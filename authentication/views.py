from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuthToken, EmailVerificationToken, User
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

    Returns a token to be sent as: Authorization: Bearer <token>
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
                'token_type': 'Bearer',
                'expires_after_minutes_of_inactivity': settings.TOKEN_INACTIVITY_TIMEOUT_MINUTES,
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /auth/logout/  (protected — requires Authorization: Bearer <token>)

    Deletes the caller's token immediately.
    """

    def post(self, request):
        AuthToken.objects.filter(user=request.user).delete()
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class AdminPromotionView(APIView):
    """Promote a registered user to an admin/manager. Super admins only."""

    def post(self, request):
        if not request.user.is_super_admin:
            return Response({'detail': 'Only super admins can create admins.'}, status=status.HTTP_403_FORBIDDEN)

        user = self._get_user(request.data.get('user_id'))
        if isinstance(user, Response):
            return user
        if user.is_super_admin:
            return Response({'detail': 'A super admin cannot be changed into an admin.'}, status=status.HTTP_400_BAD_REQUEST)

        user.sensitivity = User.SENSITIVITY_ADMIN
        user.manager = None
        user.save(update_fields=['sensitivity', 'manager'])
        return Response({'message': 'User promoted to admin.', 'user': UserSerializer(user).data})

    @staticmethod
    def _get_user(user_id):
        if not user_id:
            return Response({'detail': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class EngineerAssignmentView(APIView):
    """Put a registered user in the authenticated admin's engineer group."""

    def post(self, request):
        if not request.user.is_admin_manager:
            return Response({'detail': 'Only admins can add engineers to their group.'}, status=status.HTTP_403_FORBIDDEN)

        user = AdminPromotionView._get_user(request.data.get('user_id'))
        if isinstance(user, Response):
            return user
        if user.is_super_admin or user.is_admin_manager:
            return Response({'detail': 'Admins and super admins cannot be assigned as engineers.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.manager_id and user.manager_id != request.user.id:
            return Response({'detail': 'This engineer already belongs to another admin.'}, status=status.HTTP_400_BAD_REQUEST)

        user.sensitivity = User.SENSITIVITY_ENGINEER
        user.manager = request.user
        user.is_available = True
        user.save(update_fields=['sensitivity', 'manager', 'is_available'])
        return Response({'message': 'Engineer assigned to your group.', 'user': UserSerializer(user).data})


class TeamView(APIView):
    """Return the hierarchy visible to the current staff member."""

    def get(self, request):
        if request.user.is_super_admin:
            users = User.objects.filter(sensitivity__gte=User.SENSITIVITY_ENGINEER).select_related('manager')
        elif request.user.is_admin_manager:
            users = request.user.engineers.select_related('manager')
        else:
            return Response({'detail': 'Only staff can view teams.'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'users': UserSerializer(users, many=True).data})


class EngineerAvailabilityView(APIView):
    """Engineers declare whether they can receive another order."""

    def patch(self, request):
        if not request.user.is_engineer:
            return Response({'detail': 'Only engineers can update availability.'}, status=status.HTTP_403_FORBIDDEN)
        is_available = request.data.get('is_available')
        if not isinstance(is_available, bool):
            return Response({'detail': 'is_available must be true or false.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.is_available = is_available
        request.user.save(update_fields=['is_available'])
        return Response({'message': 'Availability updated.', 'user': UserSerializer(request.user).data})
