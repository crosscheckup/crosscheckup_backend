from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import User
from .serializers import BookingSerializer
from .models import Booking
from .utils import send_booking_confirmation_email, send_booking_notification_email


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
            return Response({'detail': 'You are not authorized to view inspections.'}, status=status.HTTP_403_FORBIDDEN)
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
    """The assigned admin allocates their inspection to an available engineer."""

    def post(self, request, inspection_id):
        if not request.user.is_admin_manager:
            return Response({'detail': 'Only admins can assign engineers.'}, status=status.HTTP_403_FORBIDDEN)
        booking = AssignInspectionAdminView._get_booking(inspection_id)
        if isinstance(booking, Response):
            return booking
        if booking.assigned_admin_id != request.user.id:
            return Response({'detail': 'This inspection is not assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            engineer = User.objects.get(
                pk=request.data.get('engineer_id'),
                sensitivity=User.SENSITIVITY_ENGINEER,
                manager=request.user,
                is_available=True,
            )
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'Engineer must belong to your group and be available.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.assigned_engineer = engineer
        booking.save(update_fields=['assigned_engineer', 'updated'])
        return Response({'message': 'Inspection assigned to engineer.', 'inspection': BookingSerializer(booking).data})
