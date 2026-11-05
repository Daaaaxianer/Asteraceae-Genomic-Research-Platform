"""Process-shared computation limits, independent of file-download leases."""
from contextvars import ContextVar
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

from django.conf import settings
from django.http import JsonResponse

from api.access_control import get_request_access
from api.shared_limits import acquire_slot, consume_rate

_caller = ContextVar('agrp_compute_caller', default='command-line')
BROWSE_COMPUTE_PATHS = frozenset('/browse/' + name for name in (
    'kegg_index', 'interproscan_index', 'function_gene', 'dupgen_finders',
    'ancestral_ks_dotplot', 'dotplot'))


class ComputeBusy(RuntimeError):
    pass


def is_compute_request(request):
    return request.method == 'POST' and (request.path.rstrip('/') in BROWSE_COMPUTE_PATHS
                                          or request.path.startswith('/api/download/tools/'))


def computation_leases():
    acquired = []
    for key, maximum in [('all-computations', int(getattr(settings, 'AGRP_COMPUTE_CONCURRENCY', 4))),
                         ('compute-caller:' + _caller.get(), int(getattr(settings, 'AGRP_COMPUTE_PER_CALLER', 2)))]:
        lease = acquire_slot(key, maximum)
        if lease is None:
            for item in acquired:
                item.close()
            raise ComputeBusy('Calculation capacity is full. Please retry later.')
        acquired.append(lease)
    return acquired


def launch_background(command, *, cwd, log_path, status_path):
    """Pass running-job locks to a supervisor so Web reloads cannot free them."""
    leases = computation_leases()
    timeout = int(getattr(settings, 'AGRP_BACKGROUND_TIMEOUT', 7200))
    runner = Path(__file__).with_name('background_runner.py')
    wrapped = [sys.executable, str(runner), str(timeout), str(status_path), json.dumps(command)]
    try:
        with open(log_path, 'ab') as log:
            if os.name != 'nt':
                subprocess.Popen(wrapped, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True,
                                 pass_fds=tuple(item.fileno() for item in leases))
            else:
                # Windows dev has no POSIX pass_fds. Retain locks until completion.
                process = subprocess.Popen(wrapped, cwd=cwd, stdin=subprocess.DEVNULL,
                                           stdout=log, stderr=subprocess.STDOUT)
                held = leases[:]
                def release_after_exit():
                    try:
                        process.wait()
                    finally:
                        for item in held:
                            item.close()
                threading.Thread(target=release_after_exit, daemon=True).start()
                leases = []
    finally:
        for item in leases:
            item.close()


class ComputeSubmissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_compute_request(request):
            return self.get_response(request)
        identity = get_request_access(request)['identity']
        token = _caller.set(identity)
        leases = []
        try:
            for key, maximum in [('compute-submit:' + identity, int(getattr(settings, 'AGRP_COMPUTE_SUBMISSIONS_PER_MINUTE', 5))),
                                 ('all-compute-submissions', int(getattr(settings, 'AGRP_COMPUTE_GLOBAL_SUBMISSIONS_PER_MINUTE', 30)))]:
                allowed, retry = consume_rate(key, maximum, 60)
                if not allowed:
                    response = JsonResponse({'status': 'error', 'message': 'Too many calculation submissions. Retry later.'}, status=429)
                    response['Retry-After'] = str(retry)
                    return response
            # The five browse background launchers reserve their own long-lived
            # leases. Other calls retain a slot through synchronous execution.
            if request.path.rstrip('/') not in BROWSE_COMPUTE_PATHS - {'/browse/dotplot'}:
                leases = computation_leases()
            return self.get_response(request)
        except ComputeBusy as error:
            response = JsonResponse({'status': 'error', 'message': str(error)}, status=429)
            response['Retry-After'] = '10'
            return response
        finally:
            for lease in leases:
                lease.close()
            _caller.reset(token)
