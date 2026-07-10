from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuthToken, EmailVerificationToken
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from .utils import send_verification_email


class RegisterView(APIView):
    """
    POST /auth/register/
    body: { "first_name", "last_name", "email", "password" }

    Creates an inactive user and emails a verification link.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        verification_token = EmailVerificationToken.objects.create(user=user)
        send_verification_email(user, verification_token)

        return Response(
            {
                'message': 'Registration successful. Please check your email to verify your account.',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """
    GET /auth/verify-email/<uuid:token>/

    Activates the account if the token is valid, unused, and not expired.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, token):
        try:
            verification = EmailVerificationToken.objects.select_related('user').get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return Response({'detail': 'Invalid verification link.'}, status=status.HTTP_400_BAD_REQUEST)

        if verification.is_used:
            return Response({'detail': 'This verification link has already been used.'},
                             status=status.HTTP_400_BAD_REQUEST)

        if verification.is_expired():
            return Response({'detail': 'This verification link has expired. Please register again '
                                        'or request a new link.'}, status=status.HTTP_400_BAD_REQUEST)

        user = verification.user
        user.is_active = True
        user.save(update_fields=['is_active'])

        verification.is_used = True
        verification.save(update_fields=['is_used'])

        return Response({'message': 'Email verified successfully. You can now log in.'},
                         status=status.HTTP_200_OK)


class LoginView(APIView):
    """
    POST /auth/login/
    body: { "email", "password" }

    Returns a token to be sent as: Authorization: Token <key>
    The token expires if unused for settings.TOKEN_INACTIVITY_TIMEOUT_MINUTES.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # One active token per user - reuse and refresh it on repeat logins.
        token, _created = AuthToken.objects.get_or_create(user=user)
        token.last_used = timezone.now()
        token.save(update_fields=['last_used'])

        from django.conf import settings

        return Response(
            {
                'token': token.key,
                'token_type': 'Token',
                'expires_after_minutes_of_inactivity': settings.TOKEN_INACTIVITY_TIMEOUT_MINUTES,
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /auth/logout/  (protected — requires Authorization: Token <key>)

    Deletes the caller's token immediately.
    """

    def post(self, request):
        AuthToken.objects.filter(user=request.user).delete()
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
