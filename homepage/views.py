from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import BookingSerializer
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