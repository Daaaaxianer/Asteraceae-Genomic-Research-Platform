from rest_framework.throttling import BaseThrottle

from api.access_control import get_rate_for_request, get_request_access, get_scope_from_path
from api.shared_limits import consume_rate


class AGRPIPRateThrottle(BaseThrottle):
    """
    IP/API-key based rate limiting for the public AGRP API.

    Normal users are identified by client IP. Authorized collaborators can be
    granted higher quota through either:
    1. AGRP_API_TRUSTED_IPS in settings.py
    2. X-AGRP-API-Key request header with a hash stored in AGRP_API_KEY_HASHES
    """

    def __init__(self):
        self.wait_seconds = None

    def allow_request(self, request, view):
        scope = get_scope_from_path(request.path)
        if scope == 'download' and getattr(request, '_agrp_download_rate_checked', False):
            return True
        if scope is None:
            return True

        access = get_request_access(request)
        if not access.get('identity'):
            return True

        max_requests, window_seconds = get_rate_for_request(request, scope)
        key = f"agrp_api_throttle:{scope}:{access['identity']}"
        allowed, self.wait_seconds = consume_rate(key, max_requests, window_seconds)
        return allowed

    def wait(self):
        return self.wait_seconds
