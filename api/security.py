"""API-only entry checks, safe errors and structured request audit records."""
import hashlib
import json
import logging
import re
import time
from urllib.parse import urlencode, urlsplit
import uuid

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponse, JsonResponse

from api.access_control import get_proxy_context, get_request_access
from api.shared_limits import acquire_slot
from api.downloads import PUBLIC_STATIC_ROOTS

logger = logging.getLogger('agrp.api')
DATA_PREFIXES = tuple('/static/' + name + '/' for name in PUBLIC_STATIC_ROOTS) + ('/file_keep/',)


def _legacy_download(path):
    match = re.fullmatch(r'/static/Species_data/([A-Za-z0-9_.-]+)\.(cds|pep|lens|new\.gff)', path)
    if match:
        species, suffix = match.groups()
        return '/api/download/genome/?' + urlencode({'species': species, 'type': 'gff' if suffix == 'new.gff' else suffix})
    match = re.fullmatch(r'/static/ancestral_data/([A-Za-z0-9_-]+)/\1\.(cds|pep|lens|new\.gff)', path)
    if match:
        dataset, suffix = match.groups()
        return '/api/download/ancestral/?' + urlencode({'dataset': dataset, 'type': 'gff' if suffix == 'new.gff' else suffix})
    return None


class APISecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def error(code, message):
        return JsonResponse({'status': 'error', 'message': message}, status=code)

    def _serve(self, request):
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.META.get('HTTP_ORIGIN')
            if origin and urlsplit(origin).netloc != request.get_host():
                return self.error(403, 'Cross-origin submission is not allowed.')
        _, _, verified_edge = get_proxy_context(request)
        if getattr(settings, 'AGRP_API_REQUIRE_EDGE', False) and not verified_edge:
            return self.error(403, 'Use the public HTTPS API endpoint.')
        if getattr(settings, 'AGRP_API_REQUIRE_HTTPS', False):
            secure = request.is_secure() or (verified_edge and request.META.get('HTTP_X_FORWARDED_PROTO') == 'https')
            if not secure:
                return self.error(426, 'HTTPS is required.')
        try:
            host = urlsplit('//' + request.get_host()).hostname
        except (DisallowedHost, ValueError):
            return self.error(400, 'Invalid request host.')
        allowed_hosts = getattr(settings, 'AGRP_API_ALLOWED_HOSTS', None)
        if allowed_hosts and host not in allowed_hosts:
            return self.error(400, 'Invalid request host.')
        if len(request.META.get('QUERY_STRING', '')) > int(getattr(settings, 'AGRP_API_MAX_QUERY_BYTES', 8192)):
            return self.error(414, 'Query is too large.')
        for name, values in request.GET.lists():
            if len(values) > 100:
                return self.error(400, 'Too many repeated parameters.')
            for value in values:
                if any(ord(char) < 32 or ord(char) == 127 for char in value):
                    return self.error(400, 'Control characters are not allowed in parameters.')
                if name in ('q', 'keyword') and len(value) > 512:
                    return self.error(400, 'Search term is too long.')
        if request.path.startswith(DATA_PREFIXES):
            return self.error(404, 'Use the controlled file API endpoint.')
        lease = acquire_slot('all-api-queries', int(getattr(settings, 'AGRP_API_GLOBAL_QUERY_CONCURRENCY', 8)))
        if lease is None:
            return self.error(429, 'API is busy. Retry later.')
        try:
            response = self.get_response(request)
        finally:
            lease.close()
        # Includes resolver errors and middleware errors even when site DEBUG is
        # enabled. No API HTML debug response crosses this boundary.
        if response.status_code >= 400 and not response.get('Content-Type', '').startswith('application/json'):
            code = response.status_code
            response.close()
            return self.error(code, 'Request could not be completed.')
        return response

    def __call__(self, request):
        from api.download_routing import is_protected_path
        if not (is_protected_path(request) or request.path.startswith(DATA_PREFIXES)):
            return self.get_response(request)
        request.api_request_id = uuid.uuid4().hex
        started = time.monotonic()
        try:
            response = self._serve(request)
        except OSError:
            logger.exception('API resource guard unavailable request_id=%s', request.api_request_id)
            response = self.error(503, 'API temporarily unavailable.')
        except Exception:
            logger.exception('API request failed request_id=%s', request.api_request_id)
            response = self.error(500, 'Request could not be completed.')
        response['X-Request-ID'] = request.api_request_id
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'no-referrer'
        if response.status_code in (429, 503) and not response.has_header('Retry-After'):
            response['Retry-After'] = '5'
        access = get_request_access(request)
        record = {
            'event': 'api_request', 'request_id': request.api_request_id,
            'method': request.method, 'path': request.path,
            'ip': access['ip'], 'tier': access['tier'], 'kind': access['kind'],
            'caller': hashlib.sha256(access['identity'].encode()).hexdigest()[:16],
            'status': response.status_code,
            'elapsed_ms': round((time.monotonic() - started) * 1000, 2),
            'declared_bytes': response.get('Content-Length'),
        }
        logger.info(json.dumps(record, ensure_ascii=True, separators=(',', ':')))
        return response

    def process_exception(self, request, exception):
        from api.compute_limits import ComputeBusy
        if isinstance(exception, ComputeBusy):
            return self.error(429, str(exception))
        if request.path.startswith('/api/'):
            logger.error('API view failed request_id=%s', getattr(request, 'api_request_id', ''),
                         exc_info=(type(exception), exception, exception.__traceback__))
            return self.error(500, 'Request could not be completed.')
        return None
