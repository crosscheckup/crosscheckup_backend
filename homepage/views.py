from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

import secrets

from django.db.models import Q
from django.http import FileResponse

from authentication.models import User
from .serializers import BookingSerializer
from .models import Booking
from .utils import (
    send_booking_confirmation_email,
    send_booking_notification_email,
    send_inspection_account_email,
)


class BookInspectionView(APIView):
    """
    POST /api/book-inspection/
    body: { "firstName" or "first_name", "lastName" or "last_name", "email", "phone", "city" }

    Creates a booking row with status="booked" and sends:
      1. A confirmation email to the customer.
      2. A notification email to the admin inbox (crosscheckup@gmail.com).
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        data = self._normalize(request.data)

        serializer = BookingSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        send_booking_confirmation_email(booking)
        send_booking_notification_email(booking)

        return Response(
            {
                'message': 'Booking successful.',
                'booking': BookingSerializer(booking).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _normalize(payload):
        """
        Accepts either camelCase (as sent by the Next.js form: firstName,
        lastName) or snake_case keys, and maps them onto the serializer's
        snake_case fields.
        """
        return {
            'first_name': payload.get('first_name', payload.get('firstName', '')),
            'last_name': payload.get('last_name', payload.get('lastName', '')),
            'email': payload.get('email', ''),
            'phone': payload.get('phone', ''),
            'city': payload.get('city', ''),
        }


class InspectionListView(APIView):
    """Show inspection bookings according to the caller's allocation role."""

    def get(self, request):
        if request.user.is_super_admin:
            bookings = Booking.objects.select_related('assigned_admin', 'assigned_engineer').all()
        elif request.user.is_admin_manager:
            bookings = Booking.objects.filter(assigned_admin=request.user).select_related('assigned_admin', 'assigned_engineer')
        elif request.user.is_engineer:
            bookings = Booking.objects.filter(assigned_engineer=request.user).select_related('assigned_admin', 'assigned_engineer')
        else:
            bookings = Booking.objects.filter(
                Q(email__iexact=request.user.email) | Q(customer_user=request.user)
            ).select_related('assigned_admin', 'assigned_engineer')
        return Response({'inspections': BookingSerializer(bookings, many=True).data})


class SuperAdminInspectionListView(APIView):
    """Base list view for super-admin booking queues."""

    assignment_filter = {}

    def get(self, request):
        if not request.user.is_super_admin:
            return Response(
                {'detail': 'Only super admins can view this inspection queue.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        bookings = Booking.objects.filter(**self.assignment_filter).select_related(
            'assigned_admin', 'assigned_engineer'
        )
        return Response({'inspections': BookingSerializer(bookings, many=True).data})


class ActiveInspectionListView(SuperAdminInspectionListView):
    """Bookings that still need to be assigned to an admin."""

    assignment_filter = {'assigned_admin__isnull': True}


class AssignedInspectionListView(SuperAdminInspectionListView):
    """Bookings that have already been assigned to an admin."""

    assignment_filter = {'assigned_admin__isnull': False}


class AssignInspectionAdminView(APIView):
    """Super admin assigns an inspection booking to an admin/manager."""

    def post(self, request, inspection_id):
        if not request.user.is_super_admin:
            return Response({'detail': 'Only super admins can assign inspections to admins.'}, status=status.HTTP_403_FORBIDDEN)
        booking = self._get_booking(inspection_id)
        if isinstance(booking, Response):
            return booking
        try:
            admin = User.objects.get(pk=request.data.get('admin_id'), sensitivity=User.SENSITIVITY_ADMIN)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'An admin with sensitivity 200 is required.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.assigned_admin = admin
        booking.assigned_engineer = None
        booking.save(update_fields=['assigned_admin', 'assigned_engineer', 'updated'])
        return Response({'message': 'Inspection assigned to admin.', 'inspection': BookingSerializer(booking).data})

    @staticmethod
    def _get_booking(booking_id):
        try:
            return Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response({'detail': 'Inspection booking not found.'}, status=status.HTTP_404_NOT_FOUND)


class AssignInspectionEngineerView(APIView):
    """The assigned admin or a super admin allocates an inspection to an engineer."""

    def post(self, request, inspection_id):
        booking = AssignInspectionAdminView._get_booking(inspection_id)
        if isinstance(booking, Response):
            return booking

        if request.user.is_super_admin:
            manager = booking.assigned_admin
            if not manager:
                return Response({'detail': 'Assign an admin before assigning an engineer.'}, status=status.HTTP_400_BAD_REQUEST)
        elif request.user.is_admin_manager:
            manager = request.user
            if booking.assigned_admin_id != manager.id:
                return Response({'detail': 'This inspection is not assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'detail': 'Only admins or super admins can assign engineers.'}, status=status.HTTP_403_FORBIDDEN)

        if booking.assigned_admin_id != manager.id:
            return Response({'detail': 'This inspection is not assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            engineer = User.objects.get(
                pk=request.data.get('engineer_id'),
                sensitivity=User.SENSITIVITY_ENGINEER,
                manager=manager,
                is_available=True,
            )
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'Engineer must belong to your group and be available.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.assigned_engineer = engineer
        booking.save(update_fields=['assigned_engineer', 'updated'])
        return Response({'message': 'Inspection assigned to engineer.', 'inspection': BookingSerializer(booking).data})


class EngineerInspectionActionView(APIView):
    """Shared permission checks for actions on the engineer's own bookings."""

    @staticmethod
    def get_booking(request, inspection_id):
        if not request.user.is_engineer:
            return Response({'detail': 'Only engineers can perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        booking = AssignInspectionAdminView._get_booking(inspection_id)
        if isinstance(booking, Response):
            return booking
        if booking.assigned_engineer_id != request.user.id:
            return Response({'detail': 'This inspection is not assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
        return booking


class StartInspectionView(EngineerInspectionActionView):
    def post(self, request, inspection_id):
        booking = self.get_booking(request, inspection_id)
        if isinstance(booking, Response):
            return booking
        if booking.status != Booking.STATUS_BOOKED:
            return Response({'detail': 'Only booked inspections can be started.'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = Booking.STATUS_PROCESSING
        booking.save(update_fields=['status', 'updated'])
        return Response({'message': 'Inspection started.', 'inspection': BookingSerializer(booking).data})


class RegisterInspectionCustomerView(EngineerInspectionActionView):
    def post(self, request, inspection_id):
        booking = self.get_booking(request, inspection_id)
        if isinstance(booking, Response):
            return booking
        if booking.status != Booking.STATUS_PROCESSING:
            return Response({'detail': 'Start the inspection before registering the customer.'}, status=status.HTTP_400_BAD_REQUEST)
        if booking.customer_user_id:
            return Response({'detail': 'A customer account has already been created for this inspection.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email__iexact=booking.email).exists():
            return Response({'detail': 'A user with this booking email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        password = secrets.token_urlsafe(12)
        customer = User.objects.create_user(
            email=booking.email,
            first_name=booking.first_name,
            last_name=booking.last_name,
            password=password,
            is_active=True,
        )
        booking.customer_user = customer
        booking.save(update_fields=['customer_user', 'updated'])
        send_inspection_account_email(customer, password)
        return Response({'message': 'Customer account created and credentials emailed.', 'inspection': BookingSerializer(booking).data}, status=status.HTTP_201_CREATED)


class InspectionDocumentView(EngineerInspectionActionView):
    def post(self, request, inspection_id):
        booking = self.get_booking(request, inspection_id)
        if isinstance(booking, Response):
            return booking
        if booking.status != Booking.STATUS_PROCESSING:
            return Response({'detail': 'Documents can only be uploaded during inspection processing.'}, status=status.HTTP_400_BAD_REQUEST)
        if not booking.customer_user_id:
            return Response({'detail': 'Register the customer before uploading a document.'}, status=status.HTTP_400_BAD_REQUEST)
        document = request.FILES.get('document')
        if not document:
            return Response({'detail': 'A document file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        booking.document = document
        booking.save(update_fields=['document', 'updated'])
        return Response({'message': 'Document uploaded.', 'inspection': BookingSerializer(booking).data})


class InspectionDocumentDownloadView(APIView):
    """Stream a document only to its customer or the staff responsible for it."""

    def get(self, request, inspection_id):
        booking = AssignInspectionAdminView._get_booking(inspection_id)
        if isinstance(booking, Response):
            return booking
        if not booking.document:
            return Response({'detail': 'No document has been uploaded for this inspection.'}, status=status.HTTP_404_NOT_FOUND)

        is_customer = booking.customer_user_id == request.user.id or booking.email.lower() == request.user.email.lower()
        is_staff_owner = (
            request.user.is_super_admin
            or booking.assigned_admin_id == request.user.id
            or booking.assigned_engineer_id == request.user.id
        )
        if not is_customer and not is_staff_owner:
            return Response({'detail': 'You are not authorized to download this document.'}, status=status.HTTP_403_FORBIDDEN)

        filename = booking.document.name.rsplit('/', 1)[-1]
        return FileResponse(booking.document.open('rb'), as_attachment=True, filename=filename)


class CompleteInspectionView(EngineerInspectionActionView):
    def post(self, request, inspection_id):
        booking = self.get_booking(request, inspection_id)
        if isinstance(booking, Response):
            return booking
        if booking.status != Booking.STATUS_PROCESSING:
            return Response({'detail': 'Only processing inspections can be completed.'}, status=status.HTTP_400_BAD_REQUEST)
        if not booking.customer_user_id or not booking.document:
            return Response({'detail': 'Register the customer and upload a document before completing the inspection.'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = Booking.STATUS_COMPLETED
        booking.save(update_fields=['status', 'updated'])
        return Response({'message': 'Inspection completed.', 'inspection': BookingSerializer(booking).data})
