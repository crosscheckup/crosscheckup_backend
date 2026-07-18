from django.http import JsonResponse

from .models import AuthToken


class APITokenAuthMiddleware:
    """
    Enterprise-style "protect by convention" middleware.

    Any request whose path contains "/api/" is automatically treated as a
    protected endpoint: a valid, non-expired token must be supplied as

        Authorization: Bearer <token>

    If the token is missing, invalid, or expired due to inactivity, the
    request is rejected with 401 before it ever reaches the view - so
    individual views/apps don't need to remember to add permission checks.

    New apps just need their urls mounted under /api/... (see sampleapp)
    to be protected automatically.
    """

    # Add any /api/ paths here that should stay public (e.g. /api/health/).
    EXEMPT_PATHS = []

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if '/api/' in request.path and request.path not in self.EXEMPT_PATHS:
            error = self._authenticate(request)
            if error:
                return error
        return self.get_response(request)

    def _authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'detail': 'Authentication credentials were not provided. '
                           'Use header: Authorization: Bearer <token>'},
                status=401,
            )

        key = auth_header.split(' ', 1)[1].strip()
        if not key:
            return JsonResponse({'detail': 'Invalid token.'}, status=401)

        try:
            token = AuthToken.objects.select_related('user').get(key=key)
        except AuthToken.DoesNotExist:
            return JsonResponse({'detail': 'Invalid token.'}, status=401)

        if not token.user.is_active:
            return JsonResponse({'detail': 'User account is inactive or not verified.'}, status=401)

        if token.is_expired():
            token.delete()
            return JsonResponse(
                {'detail': 'Token expired due to inactivity. Please login again.'}, status=401
            )

        token.refresh()
        request.user = token.user
        request.auth_token = token
        return None
