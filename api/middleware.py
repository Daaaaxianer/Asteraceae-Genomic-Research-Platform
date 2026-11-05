from django.conf import settings
from django.http import JsonResponse

from api.access_control import get_download_concurrency_limit, get_request_access, get_rate_for_request
from api.shared_limits import acquire_slot, consume_rate


class DownloadConcurrencyLimitMiddleware:
    """
    Limit concurrent /api/download/ requests.

    Public users are limited by IP. Authorized collaborators can receive higher
    concurrency through trusted IPs or valid API keys.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ''

        is_download = path.startswith('/api/download/')
        is_inline = path.startswith(('/api/files/public/', '/api/files/result/'))
        if not (is_download or is_inline):
            return self.get_response(request)

        access = get_request_access(request)
        identity = access.get('identity')
        if not identity:
            return self.get_response(request)

        scope = 'download' if is_download else 'files'
        if path.startswith('/api/files/public/jbrowse/'):
            scope = 'viewer'
            maximum, window = 600, 60
        else:
            maximum, window = get_rate_for_request(request, scope)
        allowed, retry_after = consume_rate(f'agrp_api_throttle:{scope}:{identity}', maximum, window)
        if not allowed:
            response = JsonResponse({'status': 'error', 'message': 'Too many file requests. Retry later.'}, status=429)
            response['Retry-After'] = str(retry_after)
            return response
        request._agrp_download_rate_checked = is_download
        max_concurrent = get_download_concurrency_limit(request) if is_download else int(getattr(settings, 'AGRP_API_INLINE_CONCURRENCY', 8))
        key = f'agrp_api_{scope}_concurrency:{identity}'
        lease = acquire_slot(key, max_concurrent)
        global_lease = None
        if lease is not None:
            try:
                global_key = 'all-downloads' if is_download else 'all-inline-reads'
                global_maximum = int(getattr(settings, 'AGRP_API_GLOBAL_DOWNLOAD_CONCURRENCY', 8)) if is_download else 8
                global_lease = acquire_slot(global_key, global_maximum)
            except Exception:
                lease.close()
                raise
        if lease is None or global_lease is None:
            if lease is not None:
                lease.close()
            return JsonResponse(
                {
                    'detail': (
                        'Too many concurrent download requests. '
                        'Please wait for your current downloads to finish.'
                    ),
                    'access': access.get('tier', 'public'),
                    'max_concurrent_downloads': max_concurrent,
                },
                status=429,
            )

        released = False

        def release_once():
            nonlocal released
            if released:
                return
            released = True
            lease.close()
            global_lease.close()

        try:
            response = self.get_response(request)
        except Exception:
            release_once()
            raise

        original_close = getattr(response, 'close', None)

        def close_wrapper():
            try:
                if original_close:
                    original_close()
            finally:
                release_once()

        response.close = close_wrapper

        # Non-streaming responses, such as JSON error messages, can release immediately.
        if not getattr(response, 'streaming', False):
            release_once()

        return response
