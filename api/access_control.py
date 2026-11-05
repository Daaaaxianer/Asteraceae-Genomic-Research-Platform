import hashlib
import hmac
import ipaddress

from django.conf import settings

# Cloudflare published ranges, checked 2026-10-29. Override through settings
# when the proxy topology changes: https://www.cloudflare.com/ips/
CLOUDFLARE_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    '173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22',
    '103.31.4.0/22', '141.101.64.0/18', '108.162.192.0/18',
    '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22',
    '198.41.128.0/17', '162.158.0.0/15', '104.16.0.0/13',
    '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22',
    '2400:cb00::/32', '2606:4700::/32', '2803:f800::/32',
    '2405:b500::/32', '2405:8100::/32', '2a06:98c0::/29', '2c0f:f248::/32',
))


def _ip(value):
    try:
        return ipaddress.ip_address(str(value or '').strip())
    except ValueError:
        return None


def _local_proxy(address):
    return address is not None and any(address in ipaddress.ip_network(value)
        for value in getattr(settings, 'AGRP_API_TRUSTED_PROXY_CIDRS', ('127.0.0.1/32', '::1/128')))


def _cloudflare(address):
    return address is not None and any(address in network for network in CLOUDFLARE_NETWORKS)


def get_proxy_context(request):
    """Walk from the socket peer right-to-left, never trusting the leftmost IP.

    The local reverse proxy must append its real peer to X-Forwarded-For.
    CF-Connecting-IP is accepted only behind a verified Cloudflare hop.
    """
    peer = _ip(request.META.get('REMOTE_ADDR'))
    if not (_local_proxy(peer) or _cloudflare(peer)):
        return str(peer) if peer else '', 'REMOTE_ADDR', False
    forwarded = str(request.META.get('HTTP_X_FORWARDED_FOR', ''))
    if len(forwarded) > 2048:
        return str(peer), 'REMOTE_ADDR', False
    chain = [_ip(value) for value in forwarded.split(',') if value.strip()]
    if any(value is None for value in chain):
        return str(peer), 'REMOTE_ADDR', False
    cloudflare_seen = _cloudflare(peer)
    current = peer
    while chain and (_local_proxy(current) or _cloudflare(current)):
        cloudflare_seen = cloudflare_seen or _cloudflare(current)
        current = chain.pop()
    cf_client = _ip(request.META.get('HTTP_CF_CONNECTING_IP'))
    if cloudflare_seen and cf_client is not None:
        return str(cf_client), 'CF-Connecting-IP', True
    return str(current) if current else '', 'X-Forwarded-For' if current != peer else 'REMOTE_ADDR', cloudflare_seen


DEFAULT_RATE_LIMITS = {
    'public': {
        'download': (5, 60),
        'files': (60, 60),
        'query': (120, 60),
        'ping': (60, 60),
    },
    'partner': {
        'download': (60, 60),
        'files': (600, 60),
        'query': (1000, 60),
        'ping': (120, 60),
    },
    'trusted': {
        'download': (120, 60),
        'files': (1200, 60),
        'query': (2000, 60),
        'ping': (300, 60),
    },
}

DEFAULT_DOWNLOAD_CONCURRENCY_LIMITS = {
    'public': 2,
    'partner': 10,
    'trusted': 20,
}

DEFAULT_QUERY_LIMITS = {
    'public': 100,
    'partner': 1000,
    'trusted': 2000,
}


def get_client_ip(request):
    return get_proxy_context(request)[0]


def get_scope_from_path(path):
    path = path or ''

    if path.startswith('/api/download/'):
        return 'download'

    if path.startswith('/api/files/'):
        return 'files'

    if path.startswith('/api/ping/'):
        return 'ping'

    if (
        path.startswith('/api/genomics/')
        or path.startswith('/api/genosyn/')
        or path.startswith('/api/multiomics/')
    ):
        return 'query'

    if path.startswith('/api/'):
        return 'query'

    return None


def _ip_is_trusted(ip_value):
    trusted_ips = getattr(settings, 'AGRP_API_TRUSTED_IPS', set()) or set()
    if not ip_value or not trusted_ips:
        return False

    try:
        ip_obj = ipaddress.ip_address(ip_value)
    except ValueError:
        return False

    for item in trusted_ips:
        item = str(item).strip()
        if not item:
            continue
        try:
            if '/' in item:
                if ip_obj in ipaddress.ip_network(item, strict=False):
                    return True
            elif ip_obj == ipaddress.ip_address(item):
                return True
        except ValueError:
            # Ignore malformed whitelist entries instead of breaking the API.
            continue

    return False


def _get_api_key_hash(request):
    # Recommended usage:
    # curl -H "X-AGRP-API-Key: agrp_xxx" "https://asteraceae.cgrpoee.top/api/..."
    raw_key = request.META.get('HTTP_X_AGRP_API_KEY', '')
    raw_key = str(raw_key or '').strip()
    if not raw_key:
        return None
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def _get_api_key_info(request):
    key_hash = _get_api_key_hash(request)
    if not key_hash:
        return None, None

    key_table = getattr(settings, 'AGRP_API_KEY_HASHES', {}) or {}
    for stored_hash, config in key_table.items():
        stored_hash = str(stored_hash or '').strip().lower()
        if not stored_hash:
            continue

        if not hmac.compare_digest(stored_hash, key_hash):
            continue

        if isinstance(config, dict):
            enabled = bool(config.get('enabled', True))
            if not enabled:
                return None, key_hash
            return config, key_hash

        if bool(config):
            return {'name': 'partner', 'tier': 'partner', 'enabled': True}, key_hash

        return None, key_hash

    return None, key_hash


def get_request_access(request):
    """
    Return access information used by rate limiting and concurrency limiting.

    Access levels:
    - public: normal users, identified by IP
    - partner: valid API key, higher quota
    - trusted: trusted IP or API key with tier='trusted', highest quota
    """
    ip_value = get_client_ip(request)

    if _ip_is_trusted(ip_value):
        return {
            'tier': 'trusted',
            'kind': 'trusted_ip',
            'identity': f'trusted-ip:{ip_value}',
            'name': 'trusted-ip',
            'ip': ip_value,
        }

    key_info, key_hash = _get_api_key_info(request)
    if key_info:
        tier = str(key_info.get('tier') or 'partner').strip().lower()
        if tier not in ('partner', 'trusted'):
            tier = 'partner'
        return {
            'tier': tier,
            'kind': 'api_key',
            'identity': f'api-key:{key_hash}',
            'name': key_info.get('name') or 'partner',
            'ip': ip_value,
        }

    return {
        'tier': 'public',
        'kind': 'ip',
        'identity': f'ip:{ip_value}',
        'name': 'public',
        'ip': ip_value,
    }


def _deep_merge(defaults, overrides):
    result = {tier: dict(values) for tier, values in defaults.items()}
    overrides = overrides or {}
    for tier, values in overrides.items():
        tier = str(tier).strip().lower()
        if not isinstance(values, dict):
            continue
        result.setdefault(tier, {})
        result[tier].update(values)
    return result


def get_rate_for_request(request, scope):
    access = get_request_access(request)
    rate_limits = _deep_merge(DEFAULT_RATE_LIMITS, getattr(settings, 'AGRP_API_RATE_LIMITS', None))
    tier_rates = rate_limits.get(access['tier']) or rate_limits['public']
    return tier_rates.get(scope) or tier_rates.get('query') or rate_limits['public']['query']


def get_download_concurrency_limit(request):
    access = get_request_access(request)
    limits = dict(DEFAULT_DOWNLOAD_CONCURRENCY_LIMITS)
    limits.update(getattr(settings, 'AGRP_API_DOWNLOAD_CONCURRENCY_LIMITS', {}) or {})
    return int(limits.get(access['tier'], limits['public']))


def get_query_max_limit(request):
    access = get_request_access(request)
    limits = dict(DEFAULT_QUERY_LIMITS)
    limits.update(getattr(settings, 'AGRP_API_QUERY_MAX_LIMITS', {}) or {})
    return int(limits.get(access['tier'], limits['public']))
