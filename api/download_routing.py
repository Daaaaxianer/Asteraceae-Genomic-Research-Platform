"""Reuse existing tool logic behind explicit, controlled download API routes."""
from functools import wraps
import html
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.http import JsonResponse
from django.urls import URLResolver, path, resolve, Resolver404

from api.downloads import PUBLIC_STATIC_ROOTS, error

_rules = {}


def route_regex(route):
    parts = re.split(r'(<(?:(?:str|int|slug|uuid|path):)?[A-Za-z_][A-Za-z0-9_]*>)', '/' + route)
    return '^' + ''.join('(?:.+)' if p.startswith('<path:') else '(?:[^/]+)' if p.startswith('<') else re.escape(p) for p in parts) + '$'


def build_download_patterns(patterns):
    rules, aliases = [], []

    def visit(items, prefix=''):
        for item in list(items):
            if not hasattr(item.pattern, '_route'):
                continue
            route = prefix + item.pattern._route
            if route.startswith('api/'):
                continue
            if isinstance(item, URLResolver):
                visit(item.url_patterns, route)
                continue
            callback = item.callback
            function = callback.__name__
            download_only = 'download' in function.lower() or function == 'Download_file'
            export_only = function in ('orthologous', 'hierarchical_alignments_table_data')
            tool_run = route.startswith('tools/') and (
                function.endswith('_run') or '/bio_tools/' in route)
            if not (download_only or export_only or tool_run):
                continue
            rule = {'route': route, 'regex': route_regex(route), 'download': download_only,
                    'export': export_only, 'run': tool_run, 'name': item.name}
            rules.append(rule)

            def make_view(original, policy):
                @wraps(original)
                def dispatch(request, *args, **kwargs):
                    if original.__name__ in ('download_file_view', 'Download_file'):
                        from api.downloads import legacy_file_download
                        return legacy_file_download(request)
                    return original(request, *args, **kwargs)
                dispatch._agrp_download_rule = policy
                return dispatch

            # Existing reverse()/template-url calls for download/run-only names
            # now resolve to the API. Dual-purpose page/export names stay pages.
            override_name = download_only or (item.name and '_run' in item.name)
            alias_name = item.name if override_name else ('agrp_' + item.name if item.name else None)
            aliases.append(path(route, make_view(callback, rule), item.default_args, name=alias_name))
    visit(patterns)
    _rules[settings.ROOT_URLCONF] = rules
    return aliases


def rules():
    if settings.ROOT_URLCONF not in _rules:
        from django.urls import get_resolver
        get_resolver().url_patterns
    return _rules.get(settings.ROOT_URLCONF, [])


def matching_rule(pathname):
    return next((r for r in rules() if re.fullmatch(r['regex'], pathname)), None)


def canonical_url(value, method='GET', navigation=False):
    """Map published data and known download actions; never rewrite UI assets."""
    decoded = html.unescape(str(value))
    parsed = urlsplit(decoded)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return value
    if parsed.netloc and parsed.hostname not in getattr(settings, 'AGRP_API_ALLOWED_HOSTS', ('asteraceae.cgrpoee.top', 'asteraceae.cgrpoee.cn')):
        return value
    pathname = parsed.path
    target = None
    if pathname.startswith('/static/'):
        relative = pathname[len('/static/'):]
        if relative.split('/', 1)[0] in PUBLIC_STATIC_ROOTS:
            target = ('/api/download/public/static/' if navigation else '/api/files/public/static/') + relative
        elif navigation and relative.startswith('image/') and Path(relative).suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.webp'):
            target = '/api/download/public/static_assets/' + relative
    elif pathname.startswith('/file_keep/'):
        target = ('/api/download/result/' if navigation else '/api/files/result/') + pathname[len('/file_keep/'):]
    elif navigation and pathname.startswith('/api/files/public/'):
        target = pathname.replace('/api/files/public/', '/api/download/public/', 1)
    elif navigation and pathname.startswith('/api/files/result/'):
        target = pathname.replace('/api/files/result/', '/api/download/result/', 1)
    elif not pathname.startswith('/api/'):
        rule = matching_rule(pathname)
        if rule and (rule['download'] or (rule['run'] and method.upper() == 'POST')
                     or (rule['export'] and parse_qs(parsed.query).get('export') == ['tsv'])):
            target = '/api/download' + pathname
    return urlunsplit(('', '', target, parsed.query, parsed.fragment)) if target else value


def private_directory(view, kwargs, query):
    root = Path(settings.BASE_DIR) / 'file_keep'
    function = view.__name__
    job_id = kwargs.get('job_id')
    if job_id is not None:
        for family in ('kegg', 'interproscan', 'function_gene', 'dupgen'):
            if function.startswith(family + '_job_'):
                return root / (family + '_jobs') / str(job_id)
        return root / str(job_id)
    if kwargs.get('place') is not None:
        return root / str(kwargs['place'])
    if query.get('job_id') and (function in ('interproscan_result', 'interproscan_download')):
        value = query['job_id']
        return root / str(value[0] if isinstance(value, list) else value)
    return None


def is_protected_path(request):
    from api.compute_limits import is_compute_request
    if is_compute_request(request):
        return True
    if request.path.startswith(('/api/', '/file_keep/')):
        return True
    rule = matching_rule(request.path)
    if rule and (rule['download'] or request.method == 'POST' or (rule['export'] and request.GET.get('export') == 'tsv')):
        return True
    return bool(re.search(r'/(?:[^/]*job_(?:status|result)|ancestral_ks_dotplot_status|wgdi[^/]*_status)/', request.path)
                or request.path == '/tools/interproscan_result')


def gate_view(request, view, args, kwargs):
    from api.download_access import owns_path
    rule = matching_rule(request.path)
    if rule and (rule['download'] or (rule['run'] and request.method == 'POST')
                 or (rule['export'] and request.GET.get('export') == 'tsv')):
        return error(404, 'Use the download API endpoint.')
    if request.path.startswith('/file_keep/'):
        return error(404)
    directory = private_directory(view, kwargs, request.GET)
    if directory is not None and not owns_path(directory, request):
        return error(404)
    if directory is not None:
        request._agrp_authorized_job = directory.resolve()
    return None


def grant_url(value, request):
    from api.download_access import result_credential
    parsed = urlsplit(html.unescape(str(value)))
    if parsed.scheme not in ('', 'http', 'https'):
        return value
    if parsed.netloc and parsed.hostname != request.get_host().split(':')[0]:
        return value
    directory = None
    try:
        match = resolve(parsed.path)
        directory = private_directory(match.func, match.kwargs, parse_qs(parsed.query))
    except (Resolver404, ValueError):
        pass
    for prefix in ('/api/download/result/', '/api/files/result/'):
        if parsed.path.startswith(prefix):
            directory = Path(settings.BASE_DIR) / 'file_keep' / parsed.path[len(prefix):]
    if directory is None:
        return value
    credential = result_credential(directory, request)
    if credential is None:
        return value
    query = parse_qs(parsed.query, keep_blank_values=True)
    query['access_token'] = [credential]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query, doseq=True), parsed.fragment))


def rewrite_response(response, request):
    if response.streaming:
        return response
    if response.has_header('Location'):
        response['Location'] = grant_url(canonical_url(response['Location'], navigation=True), request)
    content_type = response.get('Content-Type', '')
    if response.status_code not in (200, 201, 202):
        return response
    if content_type.startswith('application/json'):
        try:
            payload = json.loads(response.content)
        except ValueError:
            return response
        def visit(value, field=''):
            if isinstance(value, dict):
                return {k: visit(v, k) for k, v in value.items()}
            if isinstance(value, list):
                return [visit(v, field) for v in value]
            if isinstance(value, str) and value.startswith(('/', 'https://', 'http://')):
                return grant_url(canonical_url(value, navigation=('download' in field or 'export' in field)), request)
            return value
        response.content = json.dumps(visit(payload), ensure_ascii=False).encode('utf-8')
    elif content_type.startswith('text/html'):
        text = response.content.decode(response.charset)
        # Rewrite complete URL literals, not filesystem paths inside parameters
        # or documentation examples. Page data uses inline reads by default.
        def url_literal(match):
            quote, original = match.group(1), match.group(2)
            value = grant_url(canonical_url(original), request)
            if value == original:
                return match.group(0)
            return quote + value.replace('\\', '\\\\').replace(quote, '\\' + quote).replace('</', '<\\/') + quote
        text = re.sub(r'([\"\'])(/(?:static/|file_keep/)[^\"\'<>]*)\1', url_literal, text)

        def element(match):
            tag = match.group(0)
            is_form = tag.lower().startswith('<form')
            attribute = 'action' if is_form else 'href'
            method_match = re.search(r'\bmethod\s*=\s*[\"\']([^\"\']+)', tag, re.I)
            method = method_match.group(1) if method_match else 'GET'
            def replace(attr):
                # Attribute values already contain HTML entities in rendered templates.
                original = html.unescape(attr.group(2))
                value = grant_url(canonical_url(original, method=method, navigation=not is_form), request)
                return attr.group(1) + html.escape(value, quote=True) + attr.group(3)
            return re.sub(r'(\b' + attribute + r'\s*=\s*[\"\'])([^\"\']+)([\"\'])', replace, tag, flags=re.I)
        text = re.sub(r'<(?:a|form)\b[^>]*>', element, text, flags=re.I)
        # Image/result URLs need the same automatic task link as downloads.
        def source_attr(match):
            value = grant_url(html.unescape(match.group(2)), request)
            return match.group(1) + html.escape(value, quote=True) + match.group(3)
        text = re.sub(r'(\bsrc\s*=\s*[\"\'])(/api/files/result/[^\"\']+)([\"\'])', source_attr, text, flags=re.I)
        if '<head' in text.lower() and '/static/js/download-gateway.js' not in text:
            config = json.dumps({'roots': sorted(PUBLIC_STATIC_ROOTS), 'rules': rules()}, separators=(',', ':')).replace('<', '\\u003c')
            scripts = ('<script data-cfasync="false">window.AGRPDownloadConfig=' + config + ';</script>'
                       '<script data-cfasync="false" src="/static/js/download-gateway.js?v=20261029-2"></script>')
            text = re.sub(r'(<head\b[^>]*>)', lambda m: m.group(1) + scripts, text, count=1, flags=re.I)
        response.content = text.encode(response.charset)
    else:
        return response
    if response.has_header('Content-Length'):
        response['Content-Length'] = str(len(response.content))
    return response
