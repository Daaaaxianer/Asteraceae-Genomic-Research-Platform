"""Standalone supervisor; inherits running-job locks from the web launcher."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def supervise(command, timeout):
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               start_new_session=os.name != 'nt', close_fds=True)
    try:
        return process.wait(timeout=timeout), False
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.wait()
        return 124, True


def main():
    timeout, status_path, serialized = sys.argv[1:]
    command = json.loads(serialized)
    if not isinstance(command, list) or not command or any(not isinstance(a, str) for a in command):
        raise ValueError('Invalid background command')
    code, timed_out = supervise(command, int(timeout))
    if code:
        path = Path(status_path)
        try:
            previous = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            previous = {}
        previous.update(status='error', progress=100, updated_at=time.time(),
                        message='Calculation timed out.' if timed_out else 'Background calculation failed.')
        temporary = path.with_name(path.name + '.supervisor-tmp')
        temporary.write_text(json.dumps(previous), encoding='utf-8')
        os.replace(temporary, path)
    return code


if __name__ == '__main__':
    sys.exit(main())
