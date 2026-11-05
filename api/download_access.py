"""Result ownership without a new account system or database table."""
from contextvars import ContextVar
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import time
import logging

from django.conf import settings

from api.access_control import get_request_access, get_proxy_context

COOKIE_NAME = 'agrp_download_owner'
_owner = ContextVar('agrp_download_owner', default=None)
logger = logging.getLogger('agrp.api')


def request_owner(request):
    access = get_request_access(request)
    if access['kind'] == 'api_key':
        return hashlib.sha256(('key:' + access['identity']).encode()).hexdigest()
    value = request.COOKIES.get(COOKIE_NAME, '')
    if re.fullmatch(r'[0-9a-f]{64}', value):
        return hashlib.sha256(('browser:' + value).encode()).hexdigest()
    return getattr(request, '_download_owner_id', None)


def _registry():
    root = Path(settings.BASE_DIR) / '.api_download_owners'
    root.mkdir(mode=0o700, exist_ok=True)
    if root.is_symlink() or (hasattr(os, 'getuid') and root.stat().st_uid != os.getuid()):
        raise OSError('Unexpected result registry owner')
    return root


def _record_path(relative):
    return _registry() / (hashlib.sha256(relative.encode()).hexdigest() + '.json')


def register_job_directory(directory):
    """Called only when the application creates a new task directory."""
    owner = _owner.get()
    if owner is None:
        return False  # Background/CLI jobs are not silently assigned to a user.
    base = (Path(settings.BASE_DIR) / 'file_keep').resolve()
    directory = Path(directory).resolve()
    relative = directory.relative_to(base).as_posix()
    if relative == '.' or not directory.is_dir() or any(p.startswith('.') for p in relative.split('/')):
        raise ValueError('Invalid result directory')
    record = _record_path(relative)
    now = time.time()
    payload = json.dumps({'owner': owner, 'created_at': now,
                          'access_token': secrets.token_hex(32),
                          'expires_at': now + int(getattr(settings, 'AGRP_RESULT_LINK_MAX_AGE', 7 * 86400))}).encode()
    try:
        fd = os.open(record, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        saved = json.loads(record.read_text())
        if not hmac.compare_digest(saved.get('owner', ''), owner):
            raise PermissionError('Result already belongs to another caller')
        return True
    with os.fdopen(fd, 'wb') as output:
        output.write(payload)
    return True


def register_job_id(identifier):
    directory = Path(settings.BASE_DIR) / 'file_keep' / str(identifier)
    if directory.is_dir():
        return register_job_directory(directory)
    return False


def create_job_directory(directory):
    base = (Path(settings.BASE_DIR) / 'file_keep').resolve()
    selected = Path(directory).resolve()
    relative = selected.relative_to(base)
    if not relative.parts or any(part.startswith('.') for part in relative.parts):
        raise ValueError('Invalid task directory')
    selected.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents a new request from claiming an old directory.
    selected.mkdir()
    register_job_directory(selected)
    return selected


def owns_path(path, request=None):
    owner = request_owner(request) if request is not None else _owner.get()
    if owner is None:
        return False
    base = (Path(settings.BASE_DIR) / 'file_keep').resolve()
    try:
        selected = Path(path).resolve()
        selected.relative_to(base)
    except (ValueError, OSError, RuntimeError):
        return False
    current = selected if selected.is_dir() else selected.parent
    while current != base:
        relative = current.relative_to(base).as_posix()
        record = _record_path(relative)
        try:
            with record.open(encoding='utf-8') as source:
                saved = json.loads(source.read(4096))
        except (FileNotFoundError, ValueError):
            current = current.parent
            continue
        if hmac.compare_digest(str(saved.get('owner', '')), owner):
            return True
        credential = '' if request is None else (request.META.get('HTTP_X_AGRP_RESULT_TOKEN') or request.GET.get('access_token', ''))
        return bool(re.fullmatch(r'[0-9a-f]{64}', credential)
                    and saved.get('expires_at', 0) > time.time()
                    and hmac.compare_digest(scoped_credential(saved, current, selected), credential))
    return False


def scoped_credential(record, directory, selected):
    secret = str(record.get('access_token', ''))
    if not re.fullmatch(r'[0-9a-f]{64}', secret):
        return ''
    scope = selected.relative_to(directory).as_posix().encode()
    return hmac.new(bytes.fromhex(secret), scope, hashlib.sha256).hexdigest()


def result_credential(path, request):
    base = (Path(settings.BASE_DIR) / 'file_keep').resolve()
    selected = Path(path).resolve()
    authorized = owns_path(selected, request)
    granted_directory = getattr(request, '_agrp_authorized_job', None)
    if not authorized and granted_directory is not None:
        try:
            selected.relative_to(granted_directory)
            authorized = owns_path(granted_directory, request)
        except ValueError:
            pass
    if not authorized:
        return None
    current = selected if selected.is_dir() else selected.parent
    while current != base:
        record = _record_path(current.relative_to(base).as_posix())
        try:
            saved = json.loads(record.read_text())
        except (FileNotFoundError, ValueError):
            current = current.parent
            continue
        return scoped_credential(saved, current, selected) if saved.get('expires_at', 0) > time.time() else None
    return None


class DownloadOwnerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = None
        owner = request_owner(request)
        if owner is None:
            nonce = secrets.token_hex(32)
            owner = hashlib.sha256(('browser:' + nonce).encode()).hexdigest()
        request._download_owner_id = owner
        token = _owner.set(owner)
        try:
            response = self.get_response(request)
            if ('attachment' in response.get('Content-Disposition', '').lower()
                    and not request.path.startswith(('/api/download/', '/api/files/'))):
                from api.downloads import error
                response.close()
                logger.warning('Blocked unmanaged file response path=%s', request.path)
                response = error(404, 'Use the download API endpoint.')
            from api.download_routing import rewrite_response
            response = rewrite_response(response, request)
        finally:
            _owner.reset(token)
        if nonce is not None:
            secure = request.is_secure() or get_proxy_context(request)[2]
            response.set_cookie(COOKIE_NAME, nonce, max_age=30 * 86400,
                                secure=secure, httponly=True, samesite='Lax')
        return response

    def process_view(self, request, view, args, kwargs):
        from api.download_routing import gate_view
        return gate_view(request, view, args, kwargs)
