from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import AuthToken


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    DRF authentication class used by protected views (e.g. /api/userdetails/).

    Behaves like DRF's TokenAuthentication, but the token expires after
    settings.TOKEN_INACTIVITY_TIMEOUT_MINUTES of no API activity. Every
    successful authentication resets the inactivity clock.

    Clients must send: Authorization: Bearer <token>
    """
    model = AuthToken
    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related('user').get(key=key)
        except self.model.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise AuthenticationFailed('User account is inactive or not verified.')

        if token.is_expired():
            token.delete()
            raise AuthenticationFailed('Token expired due to inactivity. Please login again.')

        token.refresh()
        return (token.user, token)
