from tools.command_safety import (execute_argv, guarded_tool_view, ToolInputError, choice, identifier, iq_model, bootstrap, columns, PARAAT_FORMATS, KAKS_METHODS, DIAMOND_SENSITIVITY)
import subprocess
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse
from django.urls import reverse
import os
import glob
import base64
import numpy as np
import pandas as pd
import seaborn as sns
from LGBP.tools import *
from urllib.parse import quote
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
from django.db import connection
from urllib.parse import unquote
from collections import defaultdict
from django.shortcuts import render
from django.http import JsonResponse
from Bio.Blast import NCBIXML, NCBIWWW
from LGBP.tools import FabaceaeTaxaForm
from matplotlib.patches import Rectangle
from matplotlib.font_manager import FontProperties
from django.http import HttpResponse, FileResponse
from matplotlib.colors import ListedColormap
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.conf import settings
import zipfile
import io
from Bio import SeqIO
import json
import subprocess
import tempfile
import shutil
import base64
import sys
import time
import threading
from scipy.stats import norm
import seaborn as sns # 引入 seaborn
import re
from functools import reduce
from math import pi, cos, sin, radians
from Bio.Seq import Seq
import platform




path_get = os.getcwd()

def api_documentation(request):
    return render(request, 'api_documentation.html')

## 辅助命令行调用
def run_command(command, cwd=None):
    try:
        # shell=True 在 Windows 下必须，Linux 下通常也兼容
        subprocess.run(command, shell=True, check=True, cwd=cwd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode(errors='ignore') if e.stderr else str(e)
        raise RuntimeError(f"Command failed: {command}\nError: {error_msg}")


def wgdi_runtime_error_response(exc, cookie_name=None):
    response = HttpResponse(
        f"<html><body><pre>{str(exc)}</pre></body></html>",
        status=500,
        content_type='text/html; charset=utf-8',
    )
    if cookie_name:
        response.set_cookie(cookie_name, 'error', max_age=60, path='/')
    return response


def build_wgdi_gff_table(gff_path):
    try:
        gff_df = pd.read_csv(gff_path, sep=r'\s+', header=None, comment='#')
    except Exception:
        return None

    if gff_df.shape[1] >= 7:
        starts = pd.to_numeric(gff_df.iloc[:, 1], errors='coerce')
        ends = pd.to_numeric(gff_df.iloc[:, 2], errors='coerce')
        orders = pd.to_numeric(gff_df.iloc[:, 6], errors='coerce')
        if not (starts.isnull().any() or ends.isnull().any() or orders.isnull().any()):
            return pd.DataFrame({
                0: gff_df.iloc[:, 0],
                1: gff_df.iloc[:, 5],
                2: starts.astype(int),
                3: ends.astype(int),
                4: gff_df.iloc[:, 3],
                5: orders.astype(int),
            })

    if gff_df.shape[1] >= 6:
        starts = pd.to_numeric(gff_df.iloc[:, 2], errors='coerce')
        ends = pd.to_numeric(gff_df.iloc[:, 3], errors='coerce')
        orders = pd.to_numeric(gff_df.iloc[:, 5], errors='coerce')
        if not (starts.isnull().any() or ends.isnull().any() or orders.isnull().any()):
            return pd.DataFrame({
                0: gff_df.iloc[:, 0],
                1: gff_df.iloc[:, 1],
                2: starts.astype(int),
                3: ends.astype(int),
                4: gff_df.iloc[:, 4],
                5: orders.astype(int),
            })

    return None


def normalize_wgdi_gff_file(place, gff_name):
    gff_path = os.path.join(path_get, 'file_keep', place, gff_name)
    if not os.path.exists(gff_path):
        return

    wgdi_gff_table = build_wgdi_gff_table(gff_path)
    if wgdi_gff_table is None:
        return

    wgdi_gff_table.to_csv(gff_path, sep='\t', header=False, index=False)


def normalize_wgdi_lens_file(place, lens_name, gff_name):
    lens_path = os.path.join(path_get, 'file_keep', place, lens_name)
    gff_path = os.path.join(path_get, 'file_keep', place, gff_name)
    if not os.path.exists(lens_path) or not os.path.exists(gff_path):
        return

    try:
        lens_df = pd.read_csv(lens_path, sep=r'\s+', header=None, comment='#')
    except Exception:
        return

    if lens_df.shape[1] >= 3 or lens_df.shape[1] < 2:
        return

    wgdi_gff_table = build_wgdi_gff_table(gff_path)
    if wgdi_gff_table is None:
        return

    gff_stats = wgdi_gff_table.groupby(0).agg({3: 'max', 5: 'max'})
    gff_stats.index = gff_stats.index.astype(str)
    chromosome_names = lens_df.iloc[:, 0].astype(str)
    lengths = chromosome_names.map(gff_stats[3])
    order_counts = chromosome_names.map(gff_stats[5])

    if lengths.isnull().any() or order_counts.isnull().any():
        return

    normalized_lens_df = pd.DataFrame({
        0: lens_df.iloc[:, 0],
        1: lengths,
        2: order_counts,
    })
    normalized_lens_df.to_csv(lens_path, sep='\t', header=False, index=False)


def validate_wgdi_ks_file(place, ks_name):
    ks_path = os.path.join(path_get, 'file_keep', place, ks_name)
    if not os.path.exists(ks_path):
        return

    def is_float_value(value):
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    try:
        with open(ks_path, 'r', encoding='utf-8', errors='ignore') as ks_file:
            content = ks_file.read()
    except Exception:
        return

    data_lines = [line for line in content.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    first_data_line = data_lines[0] if data_lines else None
    if first_data_line is None:
        return

    first_columns = first_data_line.split()
    has_required_ids = len(first_columns) >= 2 and first_columns[0].lower() == 'id1' and first_columns[1].lower() == 'id2'
    if has_required_ids and 'ks_NG86' in first_columns:
        return

    rows_to_check = [line.split() for line in data_lines[:50]]
    has_headerless_official_shape = (
        rows_to_check
        and all(len(row) == 4 for row in rows_to_check)
        and all(row[0] and row[1] for row in rows_to_check)
        and all(is_float_value(row[2]) and is_float_value(row[3]) for row in rows_to_check)
    )
    if has_headerless_official_shape:
        with open(ks_path, 'w', encoding='utf-8') as ks_file:
            ks_file.write('id1\tid2\tka_NG86\tks_NG86\n')
            ks_file.write('\n'.join(data_lines))
            ks_file.write('\n')
        return

    if not has_required_ids or 'ks_NG86' not in first_columns:
        raise RuntimeError(
            "WGDI blockinfo requires a KS file header with id1, id2, and ks_NG86 columns, "
            "or a headerless four-column file ordered as id1, id2, ka_NG86, ks_NG86."
        )

def download_file_view(request):
    from api.downloads import legacy_file_download
    return legacy_file_download(request)


def build_wgdi_result_zip(place, files):
    base_dir = os.path.join(path_get, 'file_keep', place)
    zip_file_path = os.path.join(base_dir, 'result.zip')
    file_patterns = files.split() if isinstance(files, str) else list(files)
    matched_paths = []
    seen_paths = set()

    for pattern in file_patterns:
        current_matches = glob.glob(pattern if os.path.isabs(pattern) else os.path.join(base_dir, pattern))
        for match in current_matches:
            normalized_match = os.path.normpath(match)
            if normalized_match not in seen_paths:
                seen_paths.add(normalized_match)
                matched_paths.append(normalized_match)

    added_files = 0
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for match_path in matched_paths:
            if os.path.isdir(match_path):
                for root, _, filenames in os.walk(match_path):
                    for filename in filenames:
                        abs_file_path = os.path.join(root, filename)
                        arcname = os.path.relpath(abs_file_path, base_dir)
                        zipf.write(abs_file_path, arcname=arcname)
                        added_files += 1
            elif os.path.isfile(match_path):
                arcname = os.path.relpath(match_path, base_dir)
                zipf.write(match_path, arcname=arcname)
                added_files += 1

    if added_files == 0:
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        raise RuntimeError(f"Error: Zip file was not generated at {zip_file_path}")

    return zip_file_path


def wgdi_blockinfo_download(request, place):
    if re.fullmatch(r'\d+', place) is None:
        return HttpResponse(status=404)

    zip_file_path = os.path.join(path_get, 'file_keep', place, 'result.zip')
    if not os.path.isfile(zip_file_path):
        return HttpResponse(f"Error: Zip file was not found at {zip_file_path}", status=404)

    return FileResponse(open(zip_file_path, 'rb'), as_attachment=True, filename='result.zip')


WGDI_RESULT_DOWNLOAD_TOOLS = {
    'wgdimcs',
    'wgdikaks',
    'wgdi_dotplot',
    'wgdikaks_dot',
    'wgdi_correspondence',
}


def wgdi_result_download(request, tool_name, place):
    if tool_name not in WGDI_RESULT_DOWNLOAD_TOOLS or re.fullmatch(r'\d+', place) is None:
        return HttpResponse(status=404)

    zip_file_path = os.path.join(path_get, 'file_keep', place, 'result.zip')
    if not os.path.isfile(zip_file_path):
        return HttpResponse(f"Error: Zip file was not found at {zip_file_path}", status=404)

    return FileResponse(open(zip_file_path, 'rb'), as_attachment=True, filename='result.zip')


def wgdi_download_ready_response(tool_name, place, cookie_name):
    download_url = reverse('wgdi_result_download_url', args=[tool_name, place])
    response = HttpResponse(
        "<html><head><script>"
        f"window.top.location.href = {json.dumps(download_url)};"
        "</script></head><body></body></html>",
        content_type='text/html; charset=utf-8',
    )
    response.set_cookie(cookie_name, 'done', max_age=60, path='/')
    return response


def wgdimcs_status_file_path(place):
    return os.path.join(path_get, 'file_keep', place, 'wgdimcs_status.json')


def write_wgdimcs_status(place, status, message='', extra=None):
    status_path = wgdimcs_status_file_path(place)
    status_dir = os.path.dirname(status_path)
    os.makedirs(status_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(status_path, 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


def read_wgdimcs_status(place):
    status_path = wgdimcs_status_file_path(place)
    if not os.path.isfile(status_path):
        return {'status': 'running', 'message': ''}

    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read WGDI MCS status: {exc}'}


def run_wgdimcs_job(place, evalue, score):
    try:
        write_wgdimcs_status(place, 'running')
        normalize_wgdi_lens_file(place, '11.len', '11.gff')
        normalize_wgdi_lens_file(place, '22.len', '22.gff')
        normalize_wgdi_gff_file(place, '11.gff')
        normalize_wgdi_gff_file(place, '22.gff')
        wgdimcs_run_tools(place=place, evalue=evalue, score=score)
        result_file_path = os.path.join(path_get, 'file_keep', place, 'result.collinearity.txt')
        if not os.path.isfile(result_file_path):
            raise RuntimeError(f"Error: Result file was not generated at {result_file_path}")
        write_wgdimcs_status(place, 'done')
    except Exception as exc:
        write_wgdimcs_status(place, 'error', exc)


def start_wgdimcs_background_job(place, evalue, score):
    write_wgdimcs_status(place, 'running')

    base_dir = os.path.join(path_get, 'file_keep', place)
    log_path = os.path.join(base_dir, 'wgdimcs_background.log')
    manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
    python_executable = get_real_python_executable()
    command = [
        python_executable,
        manage_py,
        'run_wgdimcs_job',
        str(place),
        str(evalue),
        str(score),
    ]

    popen_kwargs = {
        'cwd': str(settings.BASE_DIR),
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'text': True,
    }
    if platform.system().lower() == 'windows':
        popen_kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    else:
        popen_kwargs['start_new_session'] = True

    try:
        with open(log_path, 'a', encoding='utf-8') as log_file:
            popen_kwargs['stdout'] = log_file
            subprocess.Popen(command, **popen_kwargs)
    except Exception as exc:
        write_wgdimcs_status(place, 'error', exc)
        raise


def wgdimcs_job_started_response(place):
    response = HttpResponse(
        "<html><head><script data-cfasync=\"false\">"
        "if (window.top && window.top.startWgdimcsStatusPolling) {"
        f"window.top.startWgdimcsStatusPolling({json.dumps(str(place))});"
        "}"
        "</script></head>"
        f"<body data-wgdimcs-started=\"1\" data-wgdimcs-place={json.dumps(str(place))}></body></html>",
        content_type='text/html; charset=utf-8',
    )
    return response


def wgdimcs_result_download(request, place):
    if re.fullmatch(r'\d+', place) is None:
        return HttpResponse(status=404)

    result_file_path = os.path.join(path_get, 'file_keep', place, 'result.collinearity.txt')
    if not os.path.isfile(result_file_path):
        return HttpResponse(f"Error: Result file was not found at {result_file_path}", status=404)

    return FileResponse(open(result_file_path, 'rb'), as_attachment=True, filename='result.collinearity.txt')


def wgdimcs_status(request, place):
    if re.fullmatch(r'\d+', place) is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid WGDI MCS job id.'}, status=404)

    status = read_wgdimcs_status(place)
    result_file_path = os.path.join(path_get, 'file_keep', place, 'result.collinearity.txt')
    if os.path.isfile(result_file_path):
        result_stat = os.stat(result_file_path)
        download_url = reverse('wgdimcs_result_download_url', args=[place])

        if status.get('status') == 'done':
            return JsonResponse({
                'status': 'done',
                'download_url': download_url,
            })

        previous_size = status.get('result_size')
        previous_mtime = status.get('result_mtime')
        result_size = result_stat.st_size
        result_mtime = result_stat.st_mtime
        now = time.time()
        first_seen_at = status.get('result_seen_at', now)

        if previous_size == result_size and previous_mtime == result_mtime and now - float(first_seen_at) >= 5:
            write_wgdimcs_status(place, 'done')
            return JsonResponse({
                'status': 'done',
                'download_url': download_url,
            })

        write_wgdimcs_status(place, 'running', extra={
            'result_size': result_size,
            'result_mtime': result_mtime,
            'result_seen_at': first_seen_at if previous_size == result_size and previous_mtime == result_mtime else now,
        })
        return JsonResponse({
            'status': 'running',
            'message': '',
        })

    zip_file_path = os.path.join(path_get, 'file_keep', place, 'result.zip')
    if os.path.isfile(zip_file_path):
        return JsonResponse({
            'status': 'done',
            'download_url': reverse('wgdi_result_download_url', args=['wgdimcs', place]),
        })

    return JsonResponse({
        'status': status.get('status', 'running'),
        'message': status.get('message', ''),
    })


def wgdikaks_status_file_path(place):
    return os.path.join(path_get, 'file_keep', place, 'wgdikaks_status.json')


def write_wgdikaks_status(place, status, message='', extra=None):
    status_path = wgdikaks_status_file_path(place)
    status_dir = os.path.dirname(status_path)
    os.makedirs(status_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(status_path, 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


def read_wgdikaks_status(place):
    status_path = wgdikaks_status_file_path(place)
    if not os.path.isfile(status_path):
        return {'status': 'running', 'message': ''}

    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read WGDI KaKs status: {exc}'}


def run_wgdikaks_job(place):
    try:
        write_wgdikaks_status(place, 'running')
        wgdikaks_run_tools(place=place)
        build_wgdi_result_zip(place, 'ks_result.txt')
        write_wgdikaks_status(place, 'done')
    except Exception as exc:
        write_wgdikaks_status(place, 'error', exc)


def start_wgdikaks_background_job(place):
    write_wgdikaks_status(place, 'running')

    base_dir = os.path.join(path_get, 'file_keep', place)
    log_path = os.path.join(base_dir, 'wgdikaks_background.log')
    manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
    python_executable = get_real_python_executable()
    command = [
        python_executable,
        manage_py,
        'run_wgdikaks_job',
        str(place),
    ]

    popen_kwargs = {
        'cwd': str(settings.BASE_DIR),
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'text': True,
    }
    if platform.system().lower() == 'windows':
        popen_kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    else:
        popen_kwargs['start_new_session'] = True

    try:
        with open(log_path, 'a', encoding='utf-8') as log_file:
            popen_kwargs['stdout'] = log_file
            subprocess.Popen(command, **popen_kwargs)
    except Exception as exc:
        write_wgdikaks_status(place, 'error', exc)
        raise


def wgdikaks_job_started_response(place):
    response = HttpResponse(
        "<html><head><script data-cfasync=\"false\">"
        "if (window.top && window.top.startWgdikaksStatusPolling) {"
        f"window.top.startWgdikaksStatusPolling({json.dumps(str(place))});"
        "}"
        "</script></head>"
        f"<body data-wgdikaks-started=\"1\" data-wgdikaks-place={json.dumps(str(place))}></body></html>",
        content_type='text/html; charset=utf-8',
    )
    return response


def wgdikaks_status(request, place):
    if re.fullmatch(r'\d+', place) is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid WGDI KaKs job id.'}, status=404)

    zip_file_path = os.path.join(path_get, 'file_keep', place, 'result.zip')
    if os.path.isfile(zip_file_path):
        write_wgdikaks_status(place, 'done')
        return JsonResponse({
            'status': 'done',
            'download_url': reverse('wgdi_result_download_url', args=['wgdikaks', place]),
        })

    status = read_wgdikaks_status(place)
    return JsonResponse({
        'status': status.get('status', 'running'),
        'message': status.get('message', ''),
    })


def wgdi_correspondence_status_file_path(place):
    return os.path.join(path_get, 'file_keep', place, 'wgdi_correspondence_status.json')


def write_wgdi_correspondence_status(place, status, message='', extra=None):
    status_path = wgdi_correspondence_status_file_path(place)
    status_dir = os.path.dirname(status_path)
    os.makedirs(status_dir, exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    if extra:
        payload.update(extra)
    with open(status_path, 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


def read_wgdi_correspondence_status(place):
    status_path = wgdi_correspondence_status_file_path(place)
    if not os.path.isfile(status_path):
        return {'status': 'running', 'message': ''}

    try:
        with open(status_path, 'r', encoding='utf-8') as status_file:
            return json.load(status_file)
    except Exception as exc:
        return {'status': 'error', 'message': f'Could not read WGDI correspondence status: {exc}'}


def read_file_tail(file_path, max_chars=4000):
    if not os.path.isfile(file_path):
        return ''

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as log_file:
            content = log_file.read()
    except Exception:
        return ''

    return content[-max_chars:]


def infer_wgdi_correspondence_background_error(place):
    log_path = os.path.join(path_get, 'file_keep', place, 'wgdi_correspondence_background.log')
    log_tail = read_file_tail(log_path)
    lowered_tail = log_tail.lower()
    error_markers = [
        'traceback',
        "can't open file",
        'no such file',
        'unknown command',
        'importerror',
        'modulenotfounderror',
        'commanderror',
        'syntaxerror',
    ]

    if log_tail and any(marker in lowered_tail for marker in error_markers):
        return (
            "WGDI correspondence background job failed before reporting status.\n\n"
            + log_tail
        )

    return ''


def run_wgdi_correspondence_job(place, tandem_length, pvalue, block_length):
    try:
        write_wgdi_correspondence_status(place, 'running')
        wgdi_correspondence_run_tools(
            place=place,
            tandem_length=tandem_length,
            pvalue=pvalue,
            block_length=block_length,
        )
        build_wgdi_result_zip(place, 'Correspondence.csv')
        write_wgdi_correspondence_status(place, 'done')
    except Exception as exc:
        write_wgdi_correspondence_status(place, 'error', exc)


def start_wgdi_correspondence_background_job(place, tandem_length, pvalue, block_length):
    write_wgdi_correspondence_status(place, 'running')

    base_dir = os.path.join(path_get, 'file_keep', place)
    log_path = os.path.join(base_dir, 'wgdi_correspondence_background.log')
    status_path = wgdi_correspondence_status_file_path(place)
    python_executable = get_real_python_executable()
    runner_script = r'''
import json
import os
import sys
import time
import traceback


def write_status(status, message=''):
    status_path = sys.argv[5]
    os.makedirs(os.path.dirname(status_path), exist_ok=True)
    payload = {
        'status': status,
        'message': str(message or ''),
        'updated_at': time.time(),
    }
    with open(status_path, 'w', encoding='utf-8') as status_file:
        json.dump(payload, status_file, ensure_ascii=False)


try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LGBP.settings')
    import django
    django.setup()
    from tools.views import run_wgdi_correspondence_job

    run_wgdi_correspondence_job(
        place=sys.argv[1],
        tandem_length=sys.argv[2],
        pvalue=sys.argv[3],
        block_length=sys.argv[4],
    )
except Exception:
    write_status('error', traceback.format_exc())
    raise
'''
    command = [
        python_executable,
        '-c',
        runner_script,
        str(place),
        str(tandem_length),
        str(pvalue),
        str(block_length),
        status_path,
    ]

    popen_kwargs = {
        'cwd': str(settings.BASE_DIR),
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'text': True,
    }
    if platform.system().lower() == 'windows':
        popen_kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    else:
        popen_kwargs['start_new_session'] = True

    try:
        with open(log_path, 'a', encoding='utf-8') as log_file:
            popen_kwargs['stdout'] = log_file
            subprocess.Popen(command, **popen_kwargs)
    except Exception as exc:
        write_wgdi_correspondence_status(place, 'error', exc)
        raise


def wgdi_correspondence_job_started_response(place):
    response = HttpResponse(
        "<html><head><script data-cfasync=\"false\">"
        "if (window.top && window.top.startWgdiCorrespondenceStatusPolling) {"
        f"window.top.startWgdiCorrespondenceStatusPolling({json.dumps(str(place))});"
        "}"
        "</script></head>"
        f"<body data-wgdi-correspondence-started=\"1\" data-wgdi-correspondence-place={json.dumps(str(place))}></body></html>",
        content_type='text/html; charset=utf-8',
    )
    return response


def wgdi_correspondence_status(request, place):
    if re.fullmatch(r'\d+', place) is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid WGDI correspondence job id.'}, status=404)

    zip_file_path = os.path.join(path_get, 'file_keep', place, 'result.zip')
    if os.path.isfile(zip_file_path):
        write_wgdi_correspondence_status(place, 'done')
        return JsonResponse({
            'status': 'done',
            'download_url': reverse('wgdi_result_download_url', args=['wgdi_correspondence', place]),
        })

    status = read_wgdi_correspondence_status(place)
    if status.get('status') == 'running':
        inferred_error = infer_wgdi_correspondence_background_error(place)
        if inferred_error:
            write_wgdi_correspondence_status(place, 'error', inferred_error)
            return JsonResponse({
                'status': 'error',
                'message': inferred_error,
            })

    return JsonResponse({
        'status': status.get('status', 'running'),
        'message': status.get('message', ''),
    })


TOOL_EXAMPLE_FILES = {
    'wgdimcs': {
        'Adu_Aed.blast': os.path.join('example_file', 'A', 'Aann_Aary.blast'),
        'Adu.lens': os.path.join('example_file', 'A', 'Aann.lens.txt'),
        'Adu.new.gff': os.path.join('example_file', 'A', 'Aann.new.gff'),
        'Aed.lens': os.path.join('example_file', 'A', 'Aary.lens.txt'),
        'Aed.new.gff': os.path.join('example_file', 'A', 'Aary.new.gff'),
    },
    'wgdikaks': {
        'pep.fasta': os.path.join('example_file', 'Aann', 'Aann.pep'),
        'cds.fasta': os.path.join('example_file', 'Aann', 'Aann.cds'),
        'Adu_Aed.block.rr.txt': os.path.join('example_file', 'Aann', 'Aann_Aann.block.rr.txt'),
    },
    'wgdi_dotplot': {
        'Adu_Aed.blast': os.path.join('example_file', 'A', 'Aann_Aary.blast'),
        'Adu.lens': os.path.join('example_file', 'A', 'Aann.lens.txt'),
        'Adu.new.gff': os.path.join('example_file', 'A', 'Aann.new.gff'),
        'Aed.lens': os.path.join('example_file', 'A', 'Aary.lens.txt'),
        'Aed.new.gff': os.path.join('example_file', 'A', 'Aary.new.gff'),
    },
    'wgdi_blockinfo': {
        'Adu_Aed.blast': os.path.join('example_file', 'A', 'Aann_Aary.blast'),
        'Adu_Aed.block.rr.txt': os.path.join('example_file', 'A', 'Aann_Aary.block.rr.txt'),
        'Adu_Aed.ks.txt': os.path.join('example_file', 'A', 'Aann_Aary.ks.txt'),
        'Adu.lens': os.path.join('example_file', 'A', 'Aann.lens.txt'),
        'Adu.new.gff': os.path.join('example_file', 'A', 'Aann.new.gff'),
        'Aed.lens': os.path.join('example_file', 'A', 'Aary.lens.txt'),
        'Aed.new.gff': os.path.join('example_file', 'A', 'Aary.new.gff'),
    },
    'wgdikaks_dot': {
        'Adu.lens': os.path.join('example_file', 'A', 'Aann.lens.txt'),
        'Aed.lens': os.path.join('example_file', 'A', 'Aary.lens.txt'),
    },
    'wgdi_correspondence': {
        'Aann_Aary_block_information.csv': os.path.join('example_file', 'A', 'Aann_Aary_block_information.csv'),
        'Aann.lens.txt': os.path.join('example_file', 'A', 'Aann.lens.txt'),
        'Aary.lens.txt': os.path.join('example_file', 'A', 'Aary.lens.txt'),
    },
    'subtree_extractor': {
        'ty.newick': os.path.join('example_file', 'Other_auxiliary_tools', 'tree_exw', 'ty.newick'),
        'genomesize.angio.cvalue.txt': os.path.join('example_file', 'Other_auxiliary_tools', 'tree_exw', 'genomesize.angio.cvalue.txt'),
    },
}


def tool_example_download(request, tool_name, filename):
    relative_path = TOOL_EXAMPLE_FILES.get(tool_name, {}).get(filename)
    if relative_path is None:
        return HttpResponse(status=404)

    candidate_paths = [
        os.path.join(settings.BASE_DIR, 'example', relative_path),
        os.path.join(settings.BASE_DIR, 'static', relative_path),
    ]

    static_root = getattr(settings, 'STATIC_ROOT', None)
    if static_root:
        candidate_paths.append(os.path.join(static_root, relative_path))

    file_path = next((path for path in candidate_paths if os.path.isfile(path)), None)
    if file_path is None:
        return HttpResponse(status=404)

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))


def zip_file(request, place, files):
    base_dir = os.path.join(path_get, 'file_keep', place)
    zip_file_path = os.path.join(base_dir, 'result.zip')

    if isinstance(files, str):
        file_patterns = files.split()
    else:
        file_patterns = list(files)

    matched_paths = []
    seen_paths = set()

    for pattern in file_patterns:
        if os.path.isabs(pattern):
            current_matches = glob.glob(pattern)
        else:
            current_matches = glob.glob(os.path.join(base_dir, pattern))

        for match in current_matches:
            normalized_match = os.path.normpath(match)
            if normalized_match not in seen_paths:
                seen_paths.add(normalized_match)
                matched_paths.append(normalized_match)

    added_files = 0

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for match_path in matched_paths:
                if os.path.isdir(match_path):
                    for root, _, filenames in os.walk(match_path):
                        for filename in filenames:
                            abs_file_path = os.path.join(root, filename)
                            arcname = os.path.relpath(abs_file_path, base_dir)
                            zipf.write(abs_file_path, arcname=arcname)
                            added_files += 1
                elif os.path.isfile(match_path):
                    arcname = os.path.relpath(match_path, base_dir)
                    zipf.write(match_path, arcname=arcname)
                    added_files += 1

        if added_files == 0:
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
            return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=404)

        response = FileResponse(open(zip_file_path, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename="result.zip"'
        return response
    except Exception:
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=500)
    # 1. 保持原有的压缩命令不变
    cmd = f"""
        cd {path_get}/file_keep/{place}
        zip -r result.zip {files}
    """
    os.system(cmd)
    
    # 2. 获取压缩包的绝对路径
    zip_file_path = f'{path_get}/file_keep/{place}/result.zip'
    
    # 3. 【核心修复】直接返回文件流，而不是 render 网页
    if os.path.exists(zip_file_path):
        # 打开文件
        response = FileResponse(open(zip_file_path, 'rb'))
        # 设置头部信息，告诉浏览器这是一个附件，需要下载
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename="result.zip"'
        return response
    else:
        # 如果压缩失败，返回错误提示
        return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=404)




def index(request):
    return render(request, 'index.html')


def tools(request):
    return render(request, 'tools.html')


## Caculation Tools
from django.shortcuts import render


#### BDI-finder  start ####
## 1. 定义大文件处理生成器
def large_file_replace_iterator(file_obj, old_str, new_str):
    """
    逐行读取文件对象，执行替换，并生成字节流。
    """
    # 确保查找和替换的字符串是字符串类型
    if not isinstance(old_str, str):
        old_str = str(old_str)
    if not isinstance(new_str, str):
        new_str = str(new_str)

    # 循环读取文件的每一行
    for line in file_obj:
        # 尝试解码：基因组文件通常是 UTF-8 或 ASCII
        try:
            line_str = line.decode('utf-8')
        except UnicodeDecodeError:
            # 如果包含特殊字符，尝试 Latin-1 防止报错
            line_str = line.decode('latin-1')

        # 执行替换操作
        # 注意：这里是按行替换。如果 old_str 跨行，这种简单逻辑无法处理。
        # 但对于 Scaffold 重命名 (如 scaffold_1 -> Chr1) 这种场景，按行处理是完美的。
        new_line_str = line_str.replace(old_str, new_str)

        # 重新编码为 bytes 并返回
        yield new_line_str.encode('utf-8')

# 2. 定义视图函数
@csrf_exempt #以此防止某些跨域或Token问题，生产环境建议去掉
def bdi_finder_view(request):
    """
    BDI-finder: 接收文件，查找 old_name 替换为 new_name，并下载。
    """
    if request.method == 'POST':
        try:
            # 获取上传的文件和参数
            input_file = request.FILES.get('input_file')
            old_name = request.POST.get('old_name')
            new_name = request.POST.get('new_name')

            # 参数校验
            if not input_file:
                return HttpResponse("Error: No file uploaded.", status=400)
            if not old_name:
                return HttpResponse("Error: 'Find String' is empty.", status=400)
            if new_name is None: # 允许 new_name 为空字符串(即删除操作)
                new_name = ""

            # 生成新文件名
            original_name = input_file.name
            new_filename = f"mod_{original_name}"

            # 使用流式响应返回处理后的文件
            # 这样浏览器会立即开始下载，不需要等待服务器处理完整个文件
            response = StreamingHttpResponse(
                large_file_replace_iterator(input_file, old_name, new_name),
                content_type='application/octet-stream'
            )

            # 设置响应头，强制浏览器下载
            response['Content-Disposition'] = f'attachment; filename="{new_filename}"'
            return response

        except Exception as e:
            return HttpResponse(f"Error processing file: {str(e)}", status=500)

    # 如果是 GET 请求，显示上传页面
    return render(request, 'find_replace.html')

#### BDI-finder end ####

#### BDI-extractor  start ####
# --- BDI-extractor 辅助函数 ---
def column_extract_iterator(file_obj, columns_indices):
    """
    流式读取文件，按 Tab 分割，提取指定列，并返回。
    columns_indices: List[int]，例如 [0, 3, 4] 代表第1, 4, 5列
    """
    for line in file_obj:
        # 1. 解码
        try:
            line_str = line.decode('utf-8')
        except UnicodeDecodeError:
            line_str = line.decode('latin-1')

        # 2. 去除首尾空白并按 Tab 分割
        # GFF3 文件标准是 Tab 分割，如果是 CSV 可以改用 ','
        # 这里保留行尾的换行符逻辑稍微复杂，简单起见先 strip 再加回来
        parts = line_str.strip().split('\t')

        # 3. 提取列
        extracted_parts = []
        for idx in columns_indices:
            # 检查索引是否越界（防止某些行通过空行或格式错误导致崩溃）
            if idx < len(parts):
                extracted_parts.append(parts[idx])
            else:
                extracted_parts.append("")  # 越界补空值

        # 4. 重新组合成行 (Tab 分隔)
        new_line = '\t'.join(extracted_parts) + '\n'

        yield new_line.encode('utf-8')


@csrf_exempt
def bdi_extractor_view(request):
    """
    BDI-extractor: 提取指定列
    """
    if request.method == 'POST':
        try:
            input_file = request.FILES.get('input_file')
            target_columns_str = request.POST.get('target_columns')  # e.g., "1,4,5"

            if not input_file or not target_columns_str:
                return HttpResponse("Error: Missing file or column numbers.", status=400)

            # 解析列号
            # 用户输入通常是 1,2,3 (1-based)，我们需要转为 0,1,2 (0-based)
            try:
                # 1. 分割字符串 2. 去空格 3. 转整数 4. 减1
                indices = [int(x.strip()) - 1 for x in target_columns_str.split(',') if x.strip().isdigit()]
            except ValueError:
                return HttpResponse(
                    "Error: Column format invalid. Please use numbers separated by commas (e.g., 1,4,5).", status=400)

            if not indices:
                return HttpResponse("Error: No valid columns parsed.", status=400)

            # 生成新文件名
            original_name = input_file.name
            new_filename = f"extracted_{original_name}"

            # 流式响应
            response = StreamingHttpResponse(
                column_extract_iterator(input_file, indices),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{new_filename}"'
            return response

        except Exception as e:
            return HttpResponse(f"Error processing file: {str(e)}", status=500)

    # GET 请求返回页面
    return render(request, 'column_extract.html')

#### BDI-extractor  end ####

#### BDI-combiner  start ####
# --- BDI-combiner 辅助函数 ---
def file_merge_iterator(files, suffix_filter):
    """
    生成器：遍历上传的文件列表，读取内容并 yield
    """
    for f in files:
        # 1. 后缀过滤
        if suffix_filter and not f.name.lower().endswith(suffix_filter.lower()):
            continue

        # 2. 逐块读取文件内容
        # 使用 f.chunks() 可以防止大文件一次性读入内存
        for chunk in f.chunks():
            yield chunk

        # 3. 每个文件末尾加一个换行符，防止文件首尾粘连
        # 注意：需要 yield bytes 类型
        yield b'\n'


@csrf_exempt
def bdi_combiner_view(request):
    """
    BDI-combiner: 合并多个上传的文件
    """
    if request.method == 'POST':
        try:
            # 获取上传的文件列表 (注意是 getlist)
            input_files = request.FILES.getlist('input_files')
            file_suffix = request.POST.get('file_suffix', '').strip()
            output_name = request.POST.get('output_name', '').strip()

            if not input_files:
                return HttpResponse("Error: No files selected.", status=400)

            # 确定输出文件名
            if not output_name:
                output_name = "merged_result.txt"

            # 确保后缀名格式正确（如果用户没加点，且文件名没后缀，可以考虑补全，这里简化处理）

            # 使用流式响应返回合并后的数据
            response = StreamingHttpResponse(
                file_merge_iterator(input_files, file_suffix),
                content_type='application/octet-stream'
            )

            # 设置下载头
            response['Content-Disposition'] = f'attachment; filename="{output_name}"'
            return response

        except Exception as e:
            return HttpResponse(f"Error merging files: {str(e)}", status=500)

    # GET 请求返回页面
    return render(request, 'file_combin.html')

#### BDI-combiner end ####

#### BDI-deduplicator  start ####
# --- BDI-deduplicator 辅助函数 ---
def fasta_deduplicate_iterator(file_obj):
    """
    流式读取 FASTA 文件，去除 ID 重复的序列。
    ID 定义为 '>' 后面的第一个单词（不包含空格后的描述信息）。
    """
    seen_ids = set()
    skip_current_sequence = False

    # 逐行读取
    for line in file_obj:
        # 解码
        try:
            line_str = line.decode('utf-8')
        except UnicodeDecodeError:
            line_str = line.decode('latin-1')

        stripped_line = line_str.strip()

        # 判断是否为 Header 行
        if stripped_line.startswith('>'):
            # 提取 ID：去掉 '>'，然后取第一个空格前的部分
            # 例如 ">Gene01 mRNA" -> ID 是 "Gene01"
            header_content = stripped_line[1:].strip()
            seq_id = header_content.split()[0] if header_content else ""

            if seq_id in seen_ids:
                # 如果 ID 已存在，标记跳过当前这条序列（直到下一个 '>'）
                skip_current_sequence = True
            else:
                # 如果是新 ID，记录下来，并允许输出
                seen_ids.add(seq_id)
                skip_current_sequence = False
                yield line_str.encode('utf-8')

        else:
            # 如果是序列内容行
            # 只有在不需要跳过的时候才输出
            if not skip_current_sequence:
                yield line_str.encode('utf-8')


@csrf_exempt
def bdi_deduplicator_view(request):
    """
    BDI-deduplicator: FASTA 序列去重工具
    """
    if request.method == 'POST':
        try:
            input_file = request.FILES.get('input_file')

            if not input_file:
                return HttpResponse("Error: No file uploaded.", status=400)

            # 生成新文件名
            original_name = input_file.name
            new_filename = f"deduplicated_{original_name}"

            # 流式响应
            response = StreamingHttpResponse(
                fasta_deduplicate_iterator(input_file),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{new_filename}"'
            return response

        except Exception as e:
            return HttpResponse(f"Error processing file: {str(e)}", status=500)

    # GET 请求
    return render(request, 'fasta_deduplicator.html')
#### BDI-deduplicator  end ####

#### sequence_screening start ####
@csrf_exempt
def sequence_screening_view(request):
    """
    SS-extractor: 根据 ID 列表筛选 Protein, CDS 和 GFF 文件
    """
    if request.method == 'POST':
        try:
            # 1. 获取上传的文件
            id_file = request.FILES.get('id_file')
            protein_file = request.FILES.get('protein_file')
            cds_file = request.FILES.get('cds_file')
            gff_file = request.FILES.get('gff_file')

            if not id_file:
                return HttpResponse("Error: ID List file is required.", status=400)

            # 2. 解析 ID 列表
            # 读取所有行，提取第一列作为 ID，存入 Set 以提高查找速度
            target_ids = set()
            for line in id_file:
                try:
                    line_str = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    line_str = line.decode('latin-1').strip()

                if line_str:
                    # 获取每行的第一个单词作为 ID
                    target_ids.add(line_str.split()[0])

            if not target_ids:
                return HttpResponse("Error: No valid IDs found in the ID file.", status=400)

            # 3. 准备 ZIP 内存缓冲区
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

                # --- 处理 Protein FASTA ---
                if protein_file:
                    new_prot_content = io.StringIO()
                    # SeqIO 需要文本流，这里进行包装
                    text_wrapper = io.TextIOWrapper(protein_file, encoding='utf-8', errors='ignore')

                    # 遍历序列并筛选
                    for record in SeqIO.parse(text_wrapper, "fasta"):
                        if record.id in target_ids:
                            # 写入类似 fasta 格式
                            new_prot_content.write(f">{record.id}\n{str(record.seq)}\n")

                    # 将结果写入 ZIP
                    if new_prot_content.tell() > 0:
                        zip_file.writestr("new_pro.txt", new_prot_content.getvalue())
                    text_wrapper.detach()  # 防止关闭原始文件流导致错误

                # --- 处理 CDS FASTA ---
                if cds_file:
                    new_cds_content = io.StringIO()
                    text_wrapper = io.TextIOWrapper(cds_file, encoding='utf-8', errors='ignore')

                    for record in SeqIO.parse(text_wrapper, "fasta"):
                        if record.id in target_ids:
                            new_cds_content.write(f">{record.id}\n{str(record.seq)}\n")

                    if new_cds_content.tell() > 0:
                        zip_file.writestr("new_cds.txt", new_cds_content.getvalue())
                    text_wrapper.detach()

                # --- 处理 GFF/Table 文件 ---
                if gff_file:
                    new_gff_content = io.StringIO()
                    # 逐行读取
                    for line in gff_file:
                        try:
                            line_str = line.decode('utf-8')
                        except:
                            line_str = line.decode('latin-1')

                        parts = line_str.split()
                        # 您的逻辑：gff_id = line.split()[1]
                        # 确保这一行至少有两列
                        if len(parts) > 1:
                            gff_id = parts[1]
                            if gff_id in target_ids:
                                new_gff_content.write(line_str)

                    if new_gff_content.tell() > 0:
                        zip_file.writestr("new_gff.txt", new_gff_content.getvalue())

            # 4. 返回 ZIP 文件下载
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="filtered_result.zip"'
            response.set_cookie('ss_extractor_download', 'done', max_age=60, path='/')
            return response

        except Exception as e:
            return HttpResponse(f"Error processing files: {str(e)}", status=500)

    # GET 请求返回页面
    return render(request, 'sequence_screening.html')

#### sequence_screening start ####

#### SAF_converter start ####
@csrf_exempt
def saf_converter_view(request):
    if request.method == 'POST':
        try:
            # 1. 获取并清理输入
            input_file = request.FILES.get('input_file')
            # 统一转为小写并去除空格，防止判断失效
            input_format = request.POST.get('input_format', '').strip().lower()
            output_format = request.POST.get('output_format', '').strip().lower()

            # [DEBUG] 在终端打印格式，确认接收到的参数是否正确
            print(f"--- DEBUG: Input='{input_format}', Output='{output_format}' ---")

            if not input_file:
                return HttpResponse("Error: No file uploaded.", status=400)

            # 准备数据流
            input_handle = io.TextIOWrapper(input_file.file, encoding='utf-8', errors='ignore')
            output_handle = io.StringIO()

            try:
                # 2. 解析序列
                records = list(SeqIO.parse(input_handle, input_format))
                
                if len(records) == 0:
                    return HttpResponse("Warning: No sequences found. Check input format.", status=400)

                # 3. 核心修复逻辑
                # 只要输出格式包含 'genbank', 'gb' 或 'embl'，就强制执行修复
                is_genbank_target = any(x in output_format for x in ['genbank', 'gb', 'embl'])

                new_records = []
                
                for i, record in enumerate(records):
                    # 如果是 GenBank，必须进行清洗和注入元数据
                    if is_genbank_target:
                        
                        # [A] 移除序列 Gap (GenBank 严禁 Gap)
                        clean_seq = str(record.seq).replace("-", "").replace(".", "")
                        if len(clean_seq) != len(record.seq):
                            # 这里改成了 Seq(clean_seq)，因为上面已经 from Bio.Seq import Seq 了
                            record.seq = Seq(clean_seq)

                        # [B] 确保 annotations 字典存在
                        if record.annotations is None:
                            record.annotations = {}

                        # [C] 强制注入 molecule_type (核心报错点)
                        # 不管原本有没有，我们重新检查并覆盖，确保万无一失
                        seq_upper = str(record.seq).upper()
                        # 只要包含蛋白特有的氨基酸(E,F,I,L,P,Q)，就认为是蛋白
                        is_protein = any(aa in seq_upper for aa in "EFILPQ")
                        
                        if is_protein:
                            record.annotations['molecule_type'] = 'protein'
                        else:
                            # 如果看起来像 DNA，但用户没指定，默认给 DNA
                            record.annotations['molecule_type'] = 'DNA'

                        # [D] 限制 Locus Name 长度 (GenBank 限制 16 字符)
                        # 如果 ID 太长，GenBank 也会报错，这里预先截断
                        if record.name and len(record.name) > 16:
                            record.name = record.name[:16]
                        if record.id and len(record.id) > 16:
                            record.id = record.id[:16]

                        # [E] 补充分类 (防止 BioPython 严格模式报错)
                        record.annotations['data_file_division'] = 'PLN'

                    new_records.append(record)

                # 4. 写入输出
                # 注意：这里使用清洗后的 input_format/output_format
                # BioPython 对格式名称不区分大小写，但最好传小写
                SeqIO.write(new_records, output_handle, output_format)
                
            except Exception as e:
                error_msg = str(e)
                print(f"--- ERROR: {error_msg} ---") # 打印错误到后台
                if "quality" in error_msg.lower():
                     return HttpResponse("Error: Cannot convert to FastQ without quality scores.", status=400)
                return HttpResponse(f"Conversion Error: {error_msg}", status=400)

            # 5. 生成下载
            original_name = input_file.name
            base_name = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
            
            # 简单的后缀映射
            suffix_map = {
                'fasta': 'fasta', 'genbank': 'gb', 'embl': 'embl',
                'phylip': 'phy', 'nexus': 'nex', 'clustal': 'aln', 'fastq': 'fq'
            }
            # 如果找不到映射，默认用 output_format
            new_suffix = suffix_map.get(output_format, 'txt') 
            new_filename = f"{base_name}_converted.{new_suffix}"

            output_data = output_handle.getvalue().encode('utf-8')
            response = HttpResponse(output_data, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{new_filename}"'
            response.set_cookie('saf_converter_download', 'done', max_age=60, path='/')
            
            return response

        except Exception as e:
            print(f"--- SYSTEM ERROR: {str(e)} ---")
            return HttpResponse(f"System Error: {str(e)}", status=500)

    return render(request, 'sequence_format.html')

#### SAF_converter end ####

#### BBM-extraction start ####
@csrf_exempt
def bbm_extraction_view(request):
    """
    BBM-extraction: 提取BLAST最佳匹配
    逻辑参考用户提供的 Python 脚本
    """
    if request.method == 'POST':
        try:
            blast_file = request.FILES.get('blast_file')

            if not blast_file:
                return HttpResponse("Error: No file uploaded.", status=400)

            # 1. 使用 Pandas 读取上传的文件
            # 注意：blast -outfmt 6 是无表头的，标准有12列
            try:
                df = pd.read_csv(
                    blast_file,
                    sep='\t',
                    names=list(range(1, 13)),  # 列名 1 到 12
                    index_col=False
                )
            except Exception as e:
                return HttpResponse(f"Error reading file. Is it a valid tab-separated BLAST file? details: {str(e)}",
                                    status=400)

            # 2. 核心处理逻辑 (参考提供的脚本)

            # 移除重复的基因对匹配 (Col 1: Query, Col 2: Target)
            df = df.drop_duplicates(subset=[1, 2])

            # 排除自匹配（query和target相同）
            df = df[df[1] != df[2]]

            # 按e-value(第11列)升序，score(第12列)降序排列
            # 升序=True (越小越好), 降序=False (越大越好)
            df = df.sort_values(by=[11, 12], ascending=[True, False])

            # 按查询基因(第1列)分组，每组取第一条（最佳匹配）
            best_df = df.groupby(1).first().reset_index()

            # 3. 准备输出文件 (ZIP 打包)
            zip_buffer = io.BytesIO()
            original_name = blast_file.name

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

                # --- 文件1: 基因对 (best_match.pairs.txt) ---
                # 只取第1列和第2列
                pairs_buffer = io.StringIO()
                best_df[[1, 2]].to_csv(pairs_buffer, sep='\t', header=False, index=False)
                zip_file.writestr(f"{original_name}.pairs.txt", pairs_buffer.getvalue())

                # --- 文件2: 完整BLAST结果 (best_match.blast.txt) ---
                # 格式化 e-value (第11列) 为科学计数法
                output_df = best_df.copy()
                try:
                    output_df[11] = output_df[11].apply(lambda x: f"{float(x):.2e}")
                except:
                    pass  # 如果转换失败保留原样

                blast_buffer = io.StringIO()
                output_df.to_csv(blast_buffer, sep='\t', header=False, index=False)
                zip_file.writestr(f"{original_name}.best_blast.txt", blast_buffer.getvalue())

            # 4. 返回 ZIP 下载
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="BBM_result_{original_name}.zip"'

            return response

        except Exception as e:
            return HttpResponse(f"System Error: {str(e)}", status=500)

    # GET 请求返回页面
    return render(request, 'bbm_extraction.html')

#### BBM-extraction end ####

#### Deal_stars start ####
# --- Deal_stars 辅助函数 ---
def clean_sequence_iterator(file_obj):
    """
    流式读取 FASTA 文件，去除序列中的 '*' 和 '.'
    """
    for line in file_obj:
        # 解码
        try:
            line_str = line.decode('utf-8')
        except UnicodeDecodeError:
            line_str = line.decode('latin-1')

        # 判断是否为 Header 行
        if line_str.startswith('>'):
            # 标题行不做修改，直接返回
            yield line_str.encode('utf-8')
        else:
            # 序列行：去除 * 和 .
            # 注意：replace 不会去除换行符，所以行结构保持不变
            cleaned_line = line_str.replace('*', '').replace('.', '')
            yield cleaned_line.encode('utf-8')


@csrf_exempt
def deal_stars_view(request):
    """
    Deal_stars: 去除序列中的 * 和 .
    """
    if request.method == 'POST':
        try:
            input_file = request.FILES.get('input_file')

            if not input_file:
                return HttpResponse("Error: No file uploaded.", status=400)

            # 生成新文件名
            original_name = input_file.name
            new_filename = f"cleaned_{original_name}"

            # 流式响应
            response = StreamingHttpResponse(
                clean_sequence_iterator(input_file),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{new_filename}"'
            return response

        except Exception as e:
            return HttpResponse(f"Error processing file: {str(e)}", status=500)

    # GET 请求
    return render(request, 'Deal_stars.html')

#### Deal_stars end ####

#### Gene_cds_exon_counter start ####

# --- 辅助函数：解析单个GFF3文件 ---
def parse_gff3_statistics(file_obj):
    """
    解析 GFF3 文件流，计算各类 feature 的数量和平均长度。
    返回一个字典。
    """
    # 初始化统计容器
    # 结构: {'gene': [len1, len2...], 'mRNA': [...]}
    data_store = defaultdict(list)

    # 辅助容器用于计算 Intron: parent_id -> list of (start, end) tuples
    exon_parent_map = defaultdict(list)

    for line in file_obj:
        try:
            line_str = line.decode('utf-8')
        except:
            line_str = line.decode('latin-1')

        if line_str.startswith('#') or not line_str.strip():
            continue

        parts = line_str.strip().split('\t')
        if len(parts) < 9:
            continue

        feature_type = parts[2]
        try:
            start = int(parts[3])
            end = int(parts[4])
        except ValueError:
            continue

        length = abs(end - start) + 1
        attributes = parts[8]

        # 统计常规 Feature
        # 注意：GFF3 feature type 大小写敏感，常见为 gene, mRNA, exon, CDS, five_prime_UTR, three_prime_UTR
        # 这里做简单归一化处理
        ftype_lower = feature_type.lower()

        if 'gene' == ftype_lower:
            data_store['gene'].append(length)
        elif 'mrna' == ftype_lower or 'transcript' == ftype_lower:
            data_store['mRNA'].append(length)
        elif 'cds' == ftype_lower:
            data_store['cds'].append(length)
        elif 'exon' == ftype_lower:
            data_store['exon'].append(length)
            # 解析 Parent ID 用于计算 Intron
            # 属性格式: ID=xxx;Parent=yyy;...
            parent_id = None
            for attr in attributes.split(';'):
                if attr.startswith('Parent='):
                    parent_id = attr.split('=')[1]
                    break
            if parent_id:
                exon_parent_map[parent_id].append((start, end))

        elif 'utr' in ftype_lower:  # 合并 3'UTR 和 5'UTR
            data_store['utr'].append(length)

    # --- 计算 Intron ---
    # 逻辑：对于每个 Parent (mRNA)，按 Exon 位置排序，计算 Exon 之间的空隙
    intron_lengths = []
    for parent, exons in exon_parent_map.items():
        if len(exons) < 2:
            continue
        # 按起始位置排序
        exons.sort(key=lambda x: x[0])

        # 遍历 Exon 间隙
        for i in range(len(exons) - 1):
            # Intron Start = 当前Exon End + 1
            # Intron End = 下一个Exon Start - 1
            # Length = (Next_Start - 1) - (Curr_End + 1) + 1 = Next_Start - Curr_End - 1
            curr_end = exons[i][1]
            next_start = exons[i + 1][0]

            intron_len = next_start - curr_end - 1
            if intron_len > 0:
                intron_lengths.append(intron_len)

    data_store['intron'] = intron_lengths

    # --- 汇总结果 ---
    result = {}
    keys = ['gene', 'mRNA', 'cds', 'exon', 'intron', 'utr']

    for k in keys:
        lengths = data_store.get(k, [])
        num = len(lengths)
        avg_len = round(sum(lengths) / num) if num > 0 else 0
        result[f'{k}_num'] = num
        result[f'{k}_len'] = avg_len

    return result


@csrf_exempt
def gene_stats_view(request):
    """
    Gene_cds_exon_counter: GFF3 统计视图
    """
    results = []

    if request.method == 'POST':
        input_files = request.FILES.getlist('input_files')

        if input_files:
            for f in input_files:
                # 解析单个文件
                stats = parse_gff3_statistics(f)
                stats['filename'] = f.name
                results.append(stats)

    return render(request, 'gene_structure_stats.html', {'results': results})
#### Gene_cds_exon_counter end ####

#### lollipop_chart start ####
@csrf_exempt
def lollipop_chart_view(request):
    """
    Lollipop Chart: 读取表格数据并传递给 ECharts
    (修复版：增强文件读取稳健性，使用 JSON 传递数据)
    """
    context = {}

    if request.method == 'POST':
        try:
            input_file = request.FILES.get('input_file')
            sort_order = request.POST.get('sort_order', 'none')
            dot_size = request.POST.get('dot_size', 15)
            dot_color = request.POST.get('dot_color', '#8e44ad')

            if not input_file:
                return HttpResponse("Error: No file uploaded.", status=400)

            # --- 1. 稳健的文件读取 ---
            # 将上传的二进制流包装为文本流，默认 UTF-8
            try:
                # 这里的 errors='replace' 防止因特殊字符导致解码崩溃
                text_file = io.TextIOWrapper(input_file.file, encoding='utf-8-sig', errors='replace')

                # 尝试读取，sep='\t' 优先 (生物学数据常用)，如果只有一列则尝试逗号
                df = pd.read_csv(text_file, sep='\t')
                if df.shape[1] < 2:
                    # 如果读出来只有1列，可能是逗号分隔或空格分隔，重置指针重读
                    input_file.file.seek(0)
                    text_file = io.TextIOWrapper(input_file.file, encoding='utf-8-sig', errors='replace')
                    df = pd.read_csv(text_file, sep=None, engine='python')  # 让 python 引擎去推断
            except Exception as e:
                return HttpResponse(f"Error reading file format: {str(e)}", status=400)

            # --- 2. 数据清洗 ---
            if df.shape[1] < 2:
                return HttpResponse("Error: File must have at least 2 columns (Name, Value).", status=400)

            # 标准化列名：强制重命名为 name, value, [group]
            cols = df.columns
            df.rename(columns={cols[0]: 'name', cols[1]: 'value'}, inplace=True)

            # 强制转为数字，非数字转为 NaN 并删除
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df.dropna(subset=['value'], inplace=True)

            # 处理分组列
            has_group = False
            if df.shape[1] >= 3:
                df.rename(columns={cols[2]: 'group'}, inplace=True)
                has_group = True
                # 确保分组列是字符串，防止数字分组导致 JS 报错
                df['group'] = df['group'].astype(str)

            # --- 3. 排序逻辑 ---
            if sort_order == 'asc':
                df.sort_values(by='value', ascending=True, inplace=True)
            elif sort_order == 'desc':
                df.sort_values(by='value', ascending=False, inplace=True)

            # --- 4. 准备数据 (使用 JSON) ---
            # 将 DataFrame 列转为列表
            names = df['name'].astype(str).tolist()
            values = df['value'].tolist()
            groups = df['group'].tolist() if has_group else []

            # 构造字典并转为 JSON 字符串
            chart_data = {
                'names': names,
                'values': values,
                'groups': groups
            }

            # 存入 Context
            context = {
                'chart_data_json': json.dumps(chart_data),  # 关键修改：传 JSON 字符串
                'has_result': True,
                'params': {
                    'dot_size': dot_size,
                    'dot_color': dot_color
                }
            }

        except Exception as e:
            # 捕获所有未知错误，打印到页面方便调试
            import traceback
            return HttpResponse(f"System Error: {str(e)} <br> <pre>{traceback.format_exc()}</pre>", status=500)

    return render(request, 'lollipop_chart.html', context)
#### lollipop_chart end ####

#### iq_tree start ####
@csrf_exempt
def iq_tree_view(request):
    """
    IQ-Tree: 调用后台 iqtree2 命令构建进化树 (自动检测序列类型)
    """
    if request.method == 'POST':
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. 获取参数
                input_file = request.FILES.get('input_file')
                aln_format = request.POST.get('aln_format', 'FASTA')
                model = request.POST.get('model', 'MFP')
                bootstrap = request.POST.get('bootstrap', '1000')
                threads = '2'  # 固定线程数

                if not input_file:
                    return HttpResponse("Error: No file uploaded.", status=400)

                # 2. 保存文件
                suffix_map = {'FASTA': '.fasta', 'PHYLIP': '.phy', 'NEXUS': '.nex'}
                file_suffix = suffix_map.get(aln_format, '.fasta')
                input_filename = f"input_alignment{file_suffix}"

                input_path = os.path.join(temp_dir, input_filename)

                with open(input_path, 'wb+') as destination:
                    for chunk in input_file.chunks():
                        destination.write(chunk)

                # 3. 构建 iqtree2 命令
                # 不指定 -st 参数，IQ-TREE 会自动检测 DNA/Protein
                iqtree2 = "/www/tools/soft_tools/iqtree2"
                cmd = [
                    iqtree2,
                    "-s", input_path,
                    "-m", model,
                    "-B", bootstrap,
                    "-nt", threads,
                    "--quiet"
                ]

                # 4. 执行命令
                process = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)

                if process.returncode != 0:
                    error_log = process.stderr if process.stderr else process.stdout
                    return HttpResponse(f"IQ-TREE Execution Failed:<br><pre>{error_log}</pre>", status=500)

                # 5. 打包结果
                zip_filename = f"iqtree_result_{input_file.name}.zip"
                zip_path = os.path.join(temp_dir, zip_filename)

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            # 排除输入文件和ZIP本身
                            if file != input_filename and file != zip_filename:
                                file_abs_path = os.path.join(root, file)
                                zipf.write(file_abs_path, arcname=file)

                # 6. 返回下载
                if os.path.exists(zip_path):
                    with open(zip_path, 'rb') as f:
                        file_data = f.read()

                    response = HttpResponse(file_data, content_type='application/zip')
                    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
                    return response
                else:
                    return HttpResponse("Error: Output files not found. Please check your input format.", status=500)

            except Exception as e:
                import traceback
                return HttpResponse(f"System Error: {str(e)} <br><pre>{traceback.format_exc()}</pre>", status=500)

    return render(request, 'iq_tree.html')

#### iq_tree end ####

#### ks_distriplot start ####

# 设置 matplotlib 后端
import matplotlib

matplotlib.use('Agg')


@csrf_exempt
def ks_distriplot_view(request):
    """
    Ks-Distriplot: 读取 CSV 并绘制 Seaborn 风格的 Ridge Plot
    """
    context = {}

    if request.method == 'POST':
        try:
            input_file = request.FILES.get('input_file')
            color_theme = request.POST.get('color_theme', 'viridis')
            try:
                overlap = float(request.POST.get('overlap', 0.8))
            except:
                overlap = 0.8

            if not input_file:
                return HttpResponse("Error: No file uploaded.", status=400)

            # 1. 读取 CSV (utf-8)
            try:
                text_file = io.TextIOWrapper(input_file.file, encoding='utf-8', errors='replace')
                df = pd.read_csv(text_file)
            except Exception as e:
                return HttpResponse(f"Error reading CSV: {str(e)}", status=400)

            # 2. 准备绘图环境
            # 使用 seaborn 设置类似 R ggridges 的白色主题，背景透明
            sns.set_theme(style="white", rc={"axes.facecolor": (0, 0, 0, 0)})

            # X轴范围 (Ks 通常 0-2 或 0-3)
            x_axis = np.linspace(0, 3, 300)

            # 计算图表尺寸
            num_species = len(df)
            fig_height = max(5, num_species * 0.8)

            # 创建图表
            fig, ax = plt.subplots(figsize=(9, fig_height))

            # 获取调色板
            palette = sns.color_palette(color_theme, n_colors=max(10, num_species * 2))

            y_ticks = []
            y_labels = []

            # 3. 绘制 Ridge Plot
            # 为了实现遮挡效果（下层遮挡上层），通常需要调整绘制顺序
            # 这里的逻辑是：y=0 是最底下。
            # 我们从上往下绘制 (idx 从大到小)，或者利用 zorder
            # 我们给每一个物种分配一个基准 Y 值 (base_y)

            # 为了更好的视觉效果，基准线间距设为 overlap
            spacing = overlap

            for idx, row in df.iterrows():
                species_name = str(row.iloc[0])
                # 自底向上排列
                base_y = idx * spacing

                y_ticks.append(base_y)
                y_labels.append(species_name)

                # 数据处理
                data_values = row.iloc[1:].values
                num_components = len(data_values) // 3

                # 绘制该物种的所有组件
                # 使用 zorder 控制层级：索引越小（越靠下）的物种，zorder 越高（在最前面）
                # 这样下方的波峰会遮挡上方的波谷
                row_zorder = (num_species - idx) * 10

                # 总密度曲线 (用于填充白色背景以遮挡后方线条)
                total_y = np.zeros_like(x_axis)
                components = []

                # 先计算所有组件，为了画总轮廓（可选），或者分别画
                for i in range(num_components):
                    try:
                        start = i * 3
                        a = float(data_values[start])
                        mu = float(data_values[start + 1])
                        sig = float(data_values[start + 2])

                        if pd.isna(a) or pd.isna(mu) or pd.isna(sig): continue

                        y_vals = norm.pdf(x_axis, loc=mu, scale=sig) * a
                        total_y += y_vals
                        components.append((i, y_vals))
                    except:
                        pass

                # 绘制技巧：
                # 1. 先用白色填充整个总密度曲线下方，起到“遮挡背景”的作用
                ax.fill_between(x_axis, base_y, base_y + total_y, color='white', zorder=row_zorder - 1)

                # 2. 绘制各个组件
                for i, y_vals in components:
                    # 颜色：可以使用调色板中的颜色，根据组件索引或物种索引
                    # 方案A：同一物种的不同组件不同色
                    # 方案B：不同物种不同色

                    # 这里采用混合方案：基色由调色板决定，组件微调
                    # 取色：根据组件类型取色 (模仿 R 脚本逻辑)
                    comp_color = palette[i % len(palette)]

                    ax.fill_between(x_axis, base_y, base_y + y_vals,
                                    color=comp_color, alpha=0.7,
                                    zorder=row_zorder)

                    # 画边缘线
                    ax.plot(x_axis, base_y + y_vals, color='white', linewidth=0.8, zorder=row_zorder + 1)

                # 画基准线 (Baseline)
                ax.plot(x_axis, [base_y] * len(x_axis), color='#dddddd', linewidth=1, zorder=row_zorder - 2)

            # 4. 样式调整
            ax.set_yticks(y_ticks)
            ax.set_yticklabels(y_labels, fontsize=11, fontstyle='italic')
            ax.set_xlabel("Ks (Synonymous substitution rate)", fontsize=12)
            ax.set_title("Ks Distribution (Ridge Plot)", fontsize=14, fontweight='bold', pad=20)

            # 去除边框 (Despine)
            sns.despine(top=True, right=True, left=True)

            ax.set_xlim(0, 2.5)  # 限制显示范围
            # ax.grid(True, axis='x', linestyle=':', alpha=0.3) # 纵向网格可选

            plt.tight_layout()

            # 5. 保存
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            plt.close()

            graphic = base64.b64encode(image_png).decode('utf-8')
            context['chart_image'] = graphic

        except Exception as e:
            import traceback
            return HttpResponse(f"System Error: {str(e)} <br><pre>{traceback.format_exc()}</pre>", status=500)

    return render(request, 'ks_distribution.html', context)

#### ks_distriplot end ####

#### cds2geno_dotplot start ####
# 设置 Matplotlib 后端为非交互式
matplotlib.use('Agg')


# ==========================================
# 辅助函数
# ==========================================

def run_command(command, cwd=None):
    return execute_argv(command, cwd=cwd)


def parse_standard_gff_to_custom(gff_path, output_gff, output_lens):
    """
    将标准GFF3转换为脚本需要的自定义格式和lens文件
    """
    genes = []
    with open(gff_path, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip(): continue
            parts = line.strip().split('\t')
            if len(parts) < 9: continue

            if parts[2] in ['mRNA', 'gene', 'transcript', 'CDS']:
                chrom = parts[0]
                try:
                    start = int(parts[3])
                    end = int(parts[4])
                except:
                    continue

                attr = parts[8]
                gene_id = "Unknown"
                if "ID=" in attr:
                    gene_id = attr.split("ID=")[1].split(";")[0]
                elif "Name=" in attr:
                    gene_id = attr.split("Name=")[1].split(";")[0]
                elif "Parent=" in attr:
                    gene_id = attr.split("Parent=")[1].split(";")[0]

                genes.append({'chrom': chrom, 'start': start, 'end': end, 'id': gene_id})

    if not genes:
        raise ValueError("No valid gene/mRNA features found in Reference GFF.")

    df = pd.DataFrame(genes)
    df = df.drop_duplicates(subset=['id'])
    df = df.sort_values(by=['chrom', 'start'])

    # 按照染色体出现的顺序重新排序染色体（可选，这里保持字母序或原始序）
    # df['gene_num'] = df.groupby('chrom').cumcount() + 1

    # 计算全局 Gene Number 用于 Lens
    chrom_groups = df.groupby('chrom')
    lens_data = []

    custom_rows = []
    for name, group in chrom_groups:
        count = len(group)
        lens_data.append([name, count])
        # 为每一行添加 gene_num (1 based)
        group = group.sort_values('start')
        group['gene_num'] = range(1, count + 1)
        custom_rows.append(group)

    df_final = pd.concat(custom_rows)

    custom_df = pd.DataFrame()
    custom_df[0] = df_final['chrom']
    custom_df[1] = df_final['start']
    custom_df[2] = df_final['end']
    custom_df[3] = df_final['chrom']
    custom_df[4] = df_final['chrom']
    custom_df[5] = df_final['id']
    custom_df[6] = df_final['gene_num']

    custom_df.to_csv(output_gff, sep='\t', index=False, header=False)

    lens_df = pd.DataFrame(lens_data)
    lens_df.to_csv(output_lens, sep='\t', index=False, header=False)


# ==========================================
# 绘图类 (重点修改部分)
# ==========================================

class DotPlotter:
    def __init__(self, work_dir, spec1, spec2, name_change):
        self.wd = work_dir
        self.spec1 = spec1  # Target (Y轴)
        self.spec2 = spec2  # Ref (X轴)
        self.name_change = name_change

    def get_clean_chr_name(self, raw_name):
        """提取染色体编号用于显示，例如 Soca_Chr01 -> 1"""
        # 尝试提取数字
        nums = re.findall(r'\d+', raw_name)
        if nums:
            # 取最后一个数字串 (通常是编号)，并去除前导0
            return str(int(nums[-1]))
        return raw_name

    def load_genome_info(self, spec):
        """读取 Lens 和 GFF，返回坐标映射和染色体边界信息"""
        lens_file = os.path.join(self.wd, f'{spec}.lens')
        gff_file = os.path.join(self.wd, f'{spec}.new.gff')

        if not os.path.exists(lens_file) or not os.path.exists(gff_file):
            return {}, {}, []

        # 1. 读取染色体长度 (基因数)
        chr_lens = {}  # {chr: length}
        chr_order = []  # 保持顺序
        with open(lens_file) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    c, l = parts[0], float(parts[1])
                    chr_lens[c] = l
                    chr_order.append(c)

        # 2. 计算每条染色体在全局坐标上的 起始点 和 终止点
        # 我们将所有染色体首尾相连成一个大坐标轴
        # 0 ---[Chr1]--- | ---[Chr2]--- | ...

        chr_offsets = {}  # {chr: start_pos_in_global}
        boundaries = []  # [(chr_name, start, end, center), ...]
        current_pos = 0

        for c in chr_order:
            length = chr_lens[c]
            start = current_pos
            end = current_pos + length
            center = (start + end) / 2

            chr_offsets[c] = start
            boundaries.append({
                'name': self.get_clean_chr_name(c),
                'start': start,
                'end': end,
                'center': center
            })
            current_pos += length

        total_len = current_pos

        # 3. 读取 GFF 映射具体基因 ID 到全局坐标
        gene_loc_map = {}  # {gene_id: global_pos}

        with open(gff_file) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 7: continue
                c = parts[0]
                gene_id = parts[5]
                gene_num = float(parts[6])

                if c in chr_offsets:
                    # 基因位置 = 染色体起始偏移 + 基因内部编号
                    gene_loc_map[gene_id] = chr_offsets[c] + gene_num

        return gene_loc_map, total_len, boundaries

    def plot(self):
        # 准备数据
        # X轴: Ref (Spec2)
        loc2, len2, bound2 = self.load_genome_info(self.spec2)
        # Y轴: Target (Spec1)
        loc1, len1, bound1 = self.load_genome_info(self.spec1)

        if not loc1 or not loc2:
            return None

        # 设置画布
        fig, ax = plt.subplots(figsize=(10, 10), dpi=150)

        # 读取比对点
        blast_file = os.path.join(self.wd, f'{self.spec1}_{self.spec2}.blastn')
        x_pts, y_pts = [], []

        if os.path.exists(blast_file) and os.path.getsize(blast_file) > 0:
            with open(blast_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 2: continue
                    q_id, s_id = parts[0], parts[1]  # Target_ID, Ref_ID

                    if q_id in loc1 and s_id in loc2:
                        x_pts.append(loc2[s_id])  # X 是 Ref
                        y_pts.append(loc1[q_id])  # Y 是 Target

        # 绘制散点 (红色，类似参考图)
        # s=0.5 保证点很细，适合大基因组
        ax.scatter(x_pts, y_pts, s=0.8, c='#C0392B', alpha=0.8, edgecolors='none')  # 红色点

        # 绘制网格线 (染色体边界)
        # X轴网格 (Ref)
        for b in bound2[:-1]:  # 最后一根线不画，因为是边界框
            ax.axvline(x=b['end'], color='black', linewidth=0.5, alpha=0.5)

        # Y轴网格 (Target)
        for b in bound1[:-1]:
            ax.axhline(y=b['end'], color='black', linewidth=0.5, alpha=0.5)

        # 设置坐标轴范围
        ax.set_xlim(0, len2)
        ax.set_ylim(0, len1)

        # 反转 Y 轴 (让 Chr1 在左上角，而不是左下角)
        ax.invert_yaxis()

        # 设置自定义刻度标签 (染色体编号)
        # X轴标签 (顶部显示)
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        ax.set_xticks([b['center'] for b in bound2])
        ax.set_xticklabels([b['name'] for b in bound2], fontsize=10, rotation=0)

        # Y轴标签 (左侧显示)
        ax.set_yticks([b['center'] for b in bound1])
        ax.set_yticklabels([b['name'] for b in bound1], fontsize=10)

        # 移除默认的刻度线 (Ticks)，只保留文字
        ax.tick_params(axis='both', which='both', length=0)

        # 添加外框 (Box)
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)

        # 添加大标题 (物种名)
        label_spec2 = self.name_change.get(self.spec2, self.spec2)
        label_spec1 = self.name_change.get(self.spec1, self.spec1)

        # X轴大标题 (加粗，大号)
        ax.set_xlabel(label_spec2, fontsize=20, fontweight='bold', labelpad=15)
        # Y轴大标题
        ax.set_ylabel(label_spec1, fontsize=20, fontweight='bold', labelpad=15)

        plt.tight_layout()

        # 输出图片
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()
        return base64.b64encode(image_png).decode('utf-8')


# ==========================================
# 视图函数
# ==========================================

@csrf_exempt
@guarded_tool_view
def cds2geno_dotplot_view(request):
    """
    CDS2Geno-Dotploting: 基于CDS比对的基因组共线性点图
    """
    if request.method == 'POST':
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. 获取输入
                target_genome = request.FILES.get('target_genome')
                ref_cds = request.FILES.get('ref_cds')
                ref_gff = request.FILES.get('ref_gff')

                t_abbr = identifier(request.POST.get('target_abbr', 'Target').strip())
                r_abbr = identifier(request.POST.get('ref_abbr', 'Ref').strip())
                t_name = request.POST.get('target_name', 'Target Species')
                r_name = request.POST.get('ref_name', 'Ref Species')

                if not all([target_genome, ref_cds, ref_gff]):
                    return HttpResponse("Error: All files are required.", status=400)

                # 2. 保存文件
                t_genome_path = os.path.join(temp_dir, f"{t_abbr}_genome.fasta")
                r_cds_path = os.path.join(temp_dir, f"{r_abbr}.cds")
                r_gff_raw_path = os.path.join(temp_dir, "ref_raw.gff")

                for f, p in [(target_genome, t_genome_path), (ref_cds, r_cds_path), (ref_gff, r_gff_raw_path)]:
                    with open(p, 'wb+') as dest:
                        for chunk in f.chunks(): dest.write(chunk)

                # 3. 预处理：生成参考物种的 GFF(custom) 和 Lens
                r_gff_custom = os.path.join(temp_dir, f"{r_abbr}.new.gff")
                r_lens = os.path.join(temp_dir, f"{r_abbr}.lens")
                try:
                    parse_standard_gff_to_custom(r_gff_raw_path, r_gff_custom, r_lens)
                except Exception as e:
                    return HttpResponse(f"Error parsing Reference GFF: {str(e)}", status=400)

                # 4. 步骤 I: Target Genome 建库 & Blast (Ref CDS -> Target Genome)
                db_name = os.path.join(temp_dir, f"{t_abbr}.db")
                run_command(['makeblastdb', '-in', t_genome_path, '-dbtype', 'nucl', '-out', db_name])

                # 增加 -task blastn -dust no 防止短序列无结果
                blast_out_1 = os.path.join(temp_dir, f"{r_abbr}_{t_abbr}.blastn")
                run_command(
                    ['blastn', '-task', 'blastn', '-dust', 'no', '-query', r_cds_path, '-db', db_name, '-out', blast_out_1, '-outfmt', '6', '-evalue', '1e-3', '-max_target_seqs', '5', '-num_threads', '2'])

                if not os.path.exists(blast_out_1) or os.path.getsize(blast_out_1) == 0:
                    return HttpResponse(f"Error: No hits found in Step 1 (Ref CDS vs Target Genome).", status=400)

                # 5. 步骤 II: 解析 Blast，提取 Target CDS
                try:
                    blast_df = pd.read_csv(blast_out_1, sep='\t', header=None,
                                           names=["QueryID", "Chr", "Pid", "Len", "Mis", "Gap", "QStart", "QEnd",
                                                  "SStart", "SEnd", "Eval", "Bit"])
                except pd.errors.EmptyDataError:
                    return HttpResponse("Error: Step 1 BLAST output is empty.", status=400)

                genome_dict = SeqIO.to_dict(SeqIO.parse(t_genome_path, "fasta"))

                # Ref Chain Map
                ref_chain_map = {}
                with open(r_gff_custom) as f:
                    for line in f:
                        parts = line.split('\t')
                        if len(parts) > 5:
                            ref_chain_map[parts[5]] = parts[3]

                blast_df['Chain'] = blast_df['QueryID'].map(ref_chain_map).fillna('Unk')
                blast_df = blast_df.sort_values(by=['Chr', 'SStart'])

                # 生成 Target Gene ID
                blast_df['NewID'] = [f"{t_abbr}_{row.Chr}_{i + 1}" for i, row in blast_df.iterrows()]
                blast_df['GeneNum'] = range(1, len(blast_df) + 1)

                # 生成 Target Custom GFF & Lens
                t_gff_path = os.path.join(temp_dir, f"{t_abbr}.new.gff")
                t_lens_path = os.path.join(temp_dir, f"{t_abbr}.lens")

                # Custom GFF format: Chr, SStart, SEnd, Chain, Chr, NewID, GeneNum
                t_out_df = blast_df[['Chr', 'SStart', 'SEnd', 'Chain', 'Chr', 'NewID', 'GeneNum']]
                t_out_df.to_csv(t_gff_path, sep='\t', index=False, header=False)

                # Lens: Group by Chr, Count (or Max GeneNum if reset per chr, but here simplified global)
                # Correct Logic: We need to emulate the structure where genes are ordered per chr
                # Re-calculate gene num per chr for Lens
                blast_df['LocalGeneNum'] = blast_df.groupby('Chr').cumcount() + 1
                t_lens_df = blast_df.groupby('Chr')['LocalGeneNum'].max().reset_index()
                t_lens_df.to_csv(t_lens_path, sep='\t', index=False, header=False)

                # IMPORTANT: For plotting, we need the GFF to have LocalGeneNum too?
                # The DotPlotter uses offsets + gene_num.
                # Let's update t_gff to use LocalGeneNum in col 6
                t_out_df_final = blast_df[['Chr', 'SStart', 'SEnd', 'Chain', 'Chr', 'NewID', 'LocalGeneNum']]
                t_out_df_final.to_csv(t_gff_path, sep='\t', index=False, header=False)

                # 提取 CDS
                t_cds_path = os.path.join(temp_dir, f"{t_abbr}.cds")
                with open(t_cds_path, 'w') as f:
                    for _, row in blast_df.iterrows():
                        chrom = str(row['Chr'])
                        s, e = int(row['SStart']), int(row['SEnd'])
                        if chrom in genome_dict:
                            seq = genome_dict[chrom].seq
                            if s > e:
                                sub_seq = seq[e - 1:s].reverse_complement()
                            else:
                                sub_seq = seq[s - 1:e]
                            f.write(f">{row['NewID']}\n{sub_seq}\n")

                if not os.path.exists(t_cds_path) or os.path.getsize(t_cds_path) == 0:
                    return HttpResponse("Error: Failed to extract predicted CDS.", status=400)

                # 6. 步骤 III: 双向 Blast
                t_cds_db = os.path.join(temp_dir, f"{t_abbr}_cds.db")
                run_command(['makeblastdb', '-in', t_cds_path, '-dbtype', 'nucl', '-out', t_cds_db])

                r_cds_db = os.path.join(temp_dir, f"{r_abbr}.db")
                run_command(['makeblastdb', '-in', r_cds_path, '-dbtype', 'nucl', '-out', r_cds_db])

                final_blast = os.path.join(temp_dir, f"{t_abbr}_{r_abbr}.blastn")
                run_command(
                    ['blastn', '-task', 'blastn', '-dust', 'no', '-query', t_cds_path, '-db', r_cds_db, '-out', final_blast, '-outfmt', '6', '-evalue', '1e-3', '-num_threads', '2'])

                # 7. 绘图
                plotter = DotPlotter(temp_dir, t_abbr, r_abbr, {t_abbr: t_name, r_abbr: r_name})
                img_data = plotter.plot()

                return render(request, 'cds2geno_dotplot.html', {'chart_image': img_data})

        except (ToolInputError, subprocess.TimeoutExpired):
            raise
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Calculation failed. Check the input format and parameters.'}, status=500)

    return render(request, 'cds2geno_dotplot.html')
#### cds2geno_dotplot end ####

#### mga-circos start ####

# Set backend
matplotlib.use('Agg')


# ===============================
# Drawing Helpers
# ===============================

def pol2cart(rho, phi):
    """Polar to Cartesian coordinates"""
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)
    return x, y


def draw_mga_circos_plot(lens_file_obj, synteny_file_obj):
    # --- 1. Colors ---
    # Chromosome colors (Pastel palette)
    chro2color = {
        "1": "#D8BFD8", "2": "#87CEEB", "3": "#DDA0DD", "4": "#48D1CC",
        "5": "#FFB6C1", "6": "#9370DB", "7": "#66CDAA", "8": "#DEB887",
        "9": "#F08080", "10": "#2F4F4F", "11": "#C0C0C0", "12": "#8FBC8F",
        "13": "#E9967A", "14": "#696969", "15": "#CD5C5C", "16": "#F0E68C",
        "17": "#FA8072", "18": "#B0C4DE", "19": "#4682B4"
    }
    default_colors = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4", "#46f0f0", "#f032e6", "#bcf60c",
                      "#fabebe"]

    # Ancestral colors (Standard MGA colors)
    ancestralchro2color = {
        "A1": (166 / 255, 201 / 255, 82 / 255),  # Green
        "A2": (47 / 255, 126 / 255, 194 / 255),  # Dark Blue
        "A3": (0 / 255, 156 / 255, 117 / 255),  # Teal
        "A4": (0 / 255, 181 / 255, 239 / 255),  # Light Blue
        "A5": (235 / 255, 38 / 255, 144 / 255),  # Magenta
        "A6": (255 / 255, 208 / 255, 10 / 255),  # Yellow
        "A7": (235 / 255, 45 / 255, 45 / 255)  # Red
    }

    # --- 2. Read Data ---
    # Read Lens
    chro2len = {}
    labels = []
    lens_lines = lens_file_obj.read().decode('utf-8').splitlines()
    for row in lens_lines:
        if not row.strip(): continue
        parts = row.split()
        if len(parts) >= 2:
            chro = parts[0]
            try:
                length = int(parts[1])
                chro2len[chro] = length
                labels.append(chro)
            except:
                continue

    if not labels: raise ValueError("Invalid Lens file.")

    # Read Synteny into memory for multiple passes
    synteny_lines = synteny_file_obj.read().decode('utf-8').splitlines()

    # --- 3. Layout Calculation ---
    full_len = sum(chro2len.values())
    chr_num = len(labels)
    gap_ratio = 0.02
    total_gap_rad = (2 * pi) * gap_ratio * chr_num
    if total_gap_rad > pi: total_gap_rad = pi
    effective_rad = (2 * pi) - total_gap_rad
    bp_per_rad = full_len / effective_rad

    # Calculate angles: Clockwise, starting from 12 o'clock (pi/2)
    chr_angles = {}
    current_rad = pi / 2
    gap_rad = total_gap_rad / chr_num

    for lbl in labels:
        arc_len = chro2len[lbl] / bp_per_rad
        start = current_rad
        end = current_rad - arc_len
        chr_angles[lbl] = (start, end)
        current_rad = end - gap_rad

    # --- 4. Plot Initialization ---
    fig = plt.figure(figsize=(12, 12), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1], polar=False)
    ax.set_aspect('equal')
    ax.axis('off')

    # Radii definitions
    R_inner_link = 0.60  # Bezier starts here
    R_inner_chr = 0.62  # Chromosome block start
    R_outer_chr = 0.68  # Chromosome block end
    R_label = 0.56  # V01 circle center (inside chromosome ring)

    # Outer tracks parameters
    R_tracks_start = 0.72
    track_width = 0.03
    track_gap = 0.005
    num_tracks = 7

    # --- 5. Draw Chromosomes ---
    for lbl in labels:
        start_rad, end_rad = chr_angles[lbl]

        # Color mapping
        c_code = re.sub(r'\D', '', lbl)
        color = chro2color.get(c_code, default_colors[int(c_code) % len(default_colors) if c_code.isdigit() else 0])

        # Draw Chromosome Wedge
        theta1, theta2 = np.degrees(end_rad), np.degrees(start_rad)
        wedge = patches.Wedge((0, 0), R_outer_chr, theta1, theta2, width=(R_outer_chr - R_inner_chr),
                              facecolor=color, edgecolor='white', linewidth=0.5)
        ax.add_patch(wedge)

        # Draw Label Circle (Green dot with ID) inside the ring
        mid_rad = (start_rad + end_rad) / 2
        lx, ly = pol2cart(R_label, mid_rad)
        circle = patches.Circle((lx, ly), 0.025, facecolor='#BDB76B', edgecolor='none', zorder=10)
        ax.add_patch(circle)

        display_label = f"V{c_code.zfill(2)}" if c_code.isdigit() else lbl
        ax.text(lx, ly, display_label, ha='center', va='center', fontsize=6, fontweight='bold', color='black',
                zorder=11)

        # Draw Background Grid lines for outer tracks
        for i in range(num_tracks):
            r_inner = R_tracks_start + i * (track_width + track_gap)
            r_outer = r_inner + track_width

            # Draw thin arc for track background
            theta = np.linspace(end_rad, start_rad, 50)
            ax.plot(r_inner * np.cos(theta), r_inner * np.sin(theta), color='#F0F0F0', linewidth=0.5, zorder=0)
            ax.plot(r_outer * np.cos(theta), r_outer * np.sin(theta), color='#F0F0F0', linewidth=0.5, zorder=0)

    # --- 6. Draw Data (Links & Outer Tracks) ---
    for row in synteny_lines:
        parts = row.strip().split('\t')
        if len(parts) < 5: continue

        chrA, posA = parts[0], float(parts[1])
        chrB, posB = parts[2], float(parts[3])
        anc = parts[4]

        if chrA not in chr_angles or chrB not in chr_angles: continue
        color_anc = ancestralchro2color.get(anc, '#AAAAAA')

        # === 6a. Inner Bezier Links ===
        # Calc coord A
        sA, eA = chr_angles[chrA]
        lenA = chro2len[chrA]
        angleA = sA - (posA / lenA) * (sA - eA)
        xA, yA = pol2cart(R_inner_link, angleA)

        # Calc coord B
        sB, eB = chr_angles[chrB]
        lenB = chro2len[chrB]
        angleB = sB - (posB / lenB) * (sB - eB)
        xB, yB = pol2cart(R_inner_link, angleB)

        # Bezier Control Points
        tension = 0.4
        cxA, cyA = pol2cart(R_inner_link * tension, angleA)
        cxB, cyB = pol2cart(R_inner_link * tension, angleB)

        path = Path([(xA, yA), (cxA, cyA), (cxB, cyB), (xB, yB)],
                    [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
        patch = patches.PathPatch(path, facecolor='none', edgecolor=color_anc, linewidth=0.15, alpha=0.4)
        ax.add_patch(patch)

        # === 6b. Outer Rings Data (Radial Lines/Ticks) ===
        # Map Ancestor ID (A1..A7) to Track Index (0..6)
        track_idx = -1
        if anc.startswith('A') and anc[1:].isdigit():
            track_idx = int(anc[1:]) - 1

        if 0 <= track_idx < num_tracks:
            # Calculate Radius range for this track
            r_inner = R_tracks_start + track_idx * (track_width + track_gap)
            r_outer = r_inner + track_width

            # Draw a radial line (tick) at angleA
            # Start point
            tx1, ty1 = pol2cart(r_inner, angleA)
            # End point
            tx2, ty2 = pol2cart(r_outer, angleA)

            # Use plot to draw line
            ax.plot([tx1, tx2], [ty1, ty2], color=color_anc, linewidth=0.8, alpha=0.9)

    # --- 7. Draw Ancestral Legend (Bottom) ---
    legend_y = -0.15  # Position below center
    legend_w = 0.05
    legend_h = 0.03
    start_x = - (len(ancestralchro2color) * legend_w) / 2

    # Label "Eu#"
    ax.text(start_x - 0.08, legend_y + legend_h / 2, "Eu#", ha='right', va='center', fontsize=10, fontweight='bold')

    anc_keys = sorted(ancestralchro2color.keys())
    for i, key in enumerate(anc_keys):
        col = ancestralchro2color[key]
        rect_x = start_x + i * legend_w

        # Color Box
        rect = patches.Rectangle((rect_x, legend_y), legend_w, legend_h, facecolor=col, edgecolor='none')
        ax.add_patch(rect)

        # Number Label below
        num_label = key.replace('A', '')
        ax.text(rect_x + legend_w / 2, legend_y - 0.025, num_label, ha='center', va='top', fontsize=9)

    # Limit View
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)

    # --- 8. Save ---
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', transparent=True)
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close(fig)

    return base64.b64encode(image_png).decode('utf-8')


@csrf_exempt
def mga_circos_view(request):
    context = {}
    if request.method == 'POST':
        try:
            lens_file = request.FILES.get('lens_file')
            synteny_file = request.FILES.get('synteny_file')

            if not lens_file or not synteny_file:
                return HttpResponse("Error: Both files are required.", status=400)

            chart_image = draw_mga_circos_plot(lens_file, synteny_file)
            context['chart_image'] = chart_image

        except Exception as e:
            import traceback
            return HttpResponse(f"Error processing files: {str(e)} <br><pre>{traceback.format_exc()}</pre>", status=500)

    return render(request, 'mga_circos.html', context)

#### mga-circos end ####




def sp_tree_chart(request):
    return render(request, 'sp_tree_chart.html')


def gene_replication_type(request):
    return render(request, 'gene_replication_chart_2.html')


def p_index(request):
    return render(request, 'p_index_chart.html')


def gene_annotation_chart(request):
    return render(request, 'Gene_annotation_chart.html')


def function_gene_chart(request):
    return render(request, 'function_gene_chart.html')


def transcription_factor_chart(request):
    return render(request, 'transcription_factor_chart.html')


def sp_introduce(request):
    return render(request, 'sp_introduce.html')


def sp_introduce2(request):
    return render(request, 'sp_introduce2.html')


def sp_introduce3(request):
    return render(request, 'sp_introduce3.html')


import pandas as pd
from Bio import SeqIO


def get_gene_ids(file_path, start, end, chromosome):
    df = pd.read_csv(file_path, sep="\t", header=None)
    filtered_df = df[df[0] == chromosome]
    final_filtered_df = filtered_df[(filtered_df[2] >= start) & (filtered_df[1] <= end)]
    gene_ids = final_filtered_df[5].tolist()
    return gene_ids


def extract_sequences_by_id(seq_file, gene_ids):
    sequences = {}
    for record in SeqIO.parse(seq_file, "fasta"):
        if record.id in gene_ids:
            sequences[f"{record.id}"] = str(record.seq)
    return sequences


def calculate_gc_content(sequence):
    gc_count = sequence.count('G') + sequence.count('C')
    gc_content = (gc_count / len(sequence)) * 100
    # return gc_content
    return round(gc_content, 3)


def compile_gene_info(cds_sequences, pep_sequences):
    gene_info = []
    for gene_id in cds_sequences.keys():
        cds_seq = cds_sequences[gene_id]
        pep_seq = pep_sequences.get(gene_id, "")
        cds_length = len(cds_seq)
        pep_length = len(pep_seq)
        gc_content = calculate_gc_content(cds_seq)
        gene_info.append((gene_id, cds_seq, pep_seq, cds_length, pep_length, gc_content))
    return gene_info

def species_data(request):
    sp_name = request.POST.get("sp_name")
    chromosome_number = request.POST.get('chromosome_number')
    start = request.POST.get('start')
    end = request.POST.get('end')
    print(sp_name, chromosome_number, start, end)

    if start is None or end is None:
        return render(request, 'genome_information.html')

    start = int(start)
    end = int(end)
    # 文件夹路径
    folder_path = os.path.join(settings.BASE_DIR, 'file_keep', 'species_data')
    gff_file = os.path.join(folder_path, f"{sp_name}.new.gff")
    chr_number = int(chromosome_number.split()[1])
    gene_ids = get_gene_ids(gff_file, start, end, chr_number)
    print(gene_ids)

    pep_seq_file = os.path.join(folder_path, f"{sp_name}.pep")
    pep_sequences = extract_sequences_by_id(pep_seq_file, gene_ids)
    cds_seq_file = os.path.join(folder_path, f"{sp_name}.cds")
    cds_sequences = extract_sequences_by_id(cds_seq_file, gene_ids)
    # 输出结果
    # print(pep_sequences, cds_sequences)
    # 汇总基因信息
    result = compile_gene_info(cds_sequences, pep_sequences)
    print(result)
    return render(request, 'genome_information.html', {'result': result})



def database(request):
    return render(request, 'database.html')


def submit(request):
    return render(request, 'submit.html')


def Referenced_our(request):
    return render(request, 'Referenced_our.html')


def documentation(request):
    return render(request, 'documentation.html')


def documentation_tools(request):
    return render(request, 'documentation_tools.html')


def software_tools(request):
    return render(request, 'software_tools.html')

def gfca(request):
    return render(request, 'gfca.html')


def karyotype(request):
    return render(request, 'karyotype.html')

def database(request):
    return render(request, 'database.html')


def about(request):
    return render(request, 'about.html')


def references(request):
    return render(request, 'references.html')


def new(request):
    return render(request, 'new.html')


def statistics(request):
    from browse.data_integrity import statistics_page
    return statistics_page(request)


def user_manual(request):
    return render(request, 'user_manual.html')


def article(request):
    return render(request, 'article.html')


def genome_information(request):
    return render(request, 'genome_information.html')

def metabolomics_plant(request):
    geneid = request.POST.get("geneid", None)
    print(geneid)
    if geneid:
        query = f"SELECT * FROM Metabolomics_plant WHERE CID LIKE %s"

        with connection.cursor() as cursor:
            cursor.execute(query, [f'%{geneid}%'])  # 使用 % 包裹 geneid
            results = cursor.fetchall()  # 获取所有匹配的结果
            # print(results)

        if results:  # 如果找到结果
            return render(request, 'metabolomics_plant.html', {'results': results})
        else:
            return render(request, 'metabolomics_plant.html', {'error': 'No information found'})
    return render(request, 'metabolomics_plant.html')


def metabolomics_scent(request):
    geneid = request.POST.get("geneid", None)
    if geneid:
        query = f"SELECT * FROM Metabolomics_scent WHERE CID LIKE %s"

        with connection.cursor() as cursor:
            cursor.execute(query, [f'%{geneid}%'])  # 使用 % 包裹 geneid
            results = cursor.fetchall()  # 获取所有匹配的结果
            # print(results)

        if results:  # 如果找到结果
            return render(request, 'metabolomics_scent.html', {'results': results})
        else:
            return render(request, 'metabolomics_scent.html', {'error': 'No information found'})
    return render(request, 'metabolomics_scent.html')

def JBrowse_index(request):
    return render(request, 'JBrowse_index.html')


def contact(request):
    return render(request, 'contact.html')


def pan_genome(request):
    # The page itself and the DataTables JSON data can both be served by this view.
    # This avoids production 404s caused by an extra /pan_genome/data/ route not being loaded.
    if request.GET.get('format') == 'datatables' or request.GET.get('data') == '1':
        return pan_genome_data(request)
    return render(request, 'pan_genome.html')


def successful(request):
    return render(request, 'successful.html')


# ===================== DataTables JSON data APIs =====================
def _candidate_static_json_paths(relative_parts):
    """Return possible static JSON paths in development and collected-static deployments."""
    candidate_paths = []

    def add_candidate(base_dir):
        if base_dir:
            candidate_paths.append(os.path.join(str(base_dir), *relative_parts))

    add_candidate(os.path.join(settings.BASE_DIR, 'static'))

    for static_dir in getattr(settings, 'STATICFILES_DIRS', []) or []:
        add_candidate(static_dir)

    add_candidate(getattr(settings, 'STATIC_ROOT', None))
    add_candidate(os.path.join(path_get, 'static'))

    unique_paths = []
    seen_paths = set()
    for candidate_path in candidate_paths:
        normalized_path = os.path.normpath(candidate_path)
        if normalized_path not in seen_paths:
            seen_paths.add(normalized_path)
            unique_paths.append(normalized_path)

    return unique_paths


def _is_pan_genome_header_row(row):
    if not isinstance(row, (list, tuple)) or len(row) < 4:
        return False

    normalized = [str(value).strip().lower() for value in row[:4]]
    return (
        normalized[0] == 'species'
        and normalized[1] == 'type'
        and normalized[2] == 'sample_accession'
        and 'reference' in normalized[3]
    )


def _normalize_pan_genome_row(row):
    """Normalize one pan-genome row to four DataTables columns."""
    if isinstance(row, dict):
        return [
            row.get('Species') or row.get('species') or row.get('0') or '',
            row.get('Type') or row.get('type') or row.get('1') or '',
            row.get('Sample_accession') or row.get('sample_accession') or row.get('Sample_Accession') or row.get('sample') or row.get('accession') or row.get('2') or '',
            row.get('Reference') or row.get('reference') or row.get('3') or '',
        ]

    if isinstance(row, (list, tuple)):
        values = list(row[:4])
        while len(values) < 4:
            values.append('')
        return values

    return None


def _datatables_json_payload(payload):
    """
    Convert fan.json to the exact shape DataTables needs: {"data": [[col1, col2, col3, col4], ...]}.

    Important:
    - fan.json has a first header row, while the HTML already has <thead>, so the header row must be removed.
    - Some broken/generated JSON files may be flattened as [cell1, cell2, cell3, cell4, ...];
      in that case, rebuild rows by groups of four.
    """
    if isinstance(payload, dict):
        rows = payload.get('data')
        if rows is None:
            for key in ('rows', 'results', 'items'):
                if isinstance(payload.get(key), list):
                    rows = payload.get(key)
                    break
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    if not isinstance(rows, list):
        rows = []

    # If the JSON is a flat cell list, rebuild it into rows of four cells.
    if rows and all(not isinstance(item, (list, tuple, dict)) for item in rows):
        rebuilt_rows = []
        for index in range(0, len(rows), 4):
            rebuilt_rows.append(rows[index:index + 4])
        rows = rebuilt_rows

    normalized_rows = []
    for row in rows:
        if _is_pan_genome_header_row(row):
            continue

        normalized_row = _normalize_pan_genome_row(row)
        if normalized_row is not None:
            normalized_rows.append(normalized_row)

    return {'data': normalized_rows}


def _read_static_json_response(relative_parts):
    """Return a JSON file from static/ through Django, bypassing Nginx /static/ handling."""
    candidate_paths = _candidate_static_json_paths(relative_parts)

    for json_path in candidate_paths:
        if os.path.isfile(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    payload = json.load(json_file)
                return JsonResponse(_datatables_json_payload(payload), safe=False)
            except json.JSONDecodeError as exc:
                return JsonResponse({
                    'data': [],
                    'error': f'JSON format error in {json_path}: {exc}'
                }, status=500)
            except Exception as exc:
                return JsonResponse({
                    'data': [],
                    'error': f'Could not read {json_path}: {exc}'
                }, status=500)

    return JsonResponse({
        'data': [],
        'error': 'JSON file was not found.',
        'checked_paths': candidate_paths,
    }, status=404)


def pan_genome_data(request):
    return _read_static_json_response(['syn_data', 'fan.json'])
# =================== End DataTables JSON data APIs ===================


# 分割线----------------------------------------tools模块
# 豆科_blast--

TOOL_USAGE_TOOLS = [{'original_no': 1,
  'key': 'blast_url',
  'url_name': 'blast_url',
  'name': 'Blast',
  'description': 'Call the blast software to perform sequence alignment to arbitrary files.'},
 {'original_no': 2,
  'key': 'diamond_url',
  'url_name': 'diamond_url',
  'name': 'Diamond',
  'description': 'Call the Diamond software for sequence alignment, arbitrary files.'},
 {'original_no': 3,
  'key': 'blast_match_url',
  'url_name': 'blast_match_url',
  'name': 'Blast match *',
  'description': 'Leguminosae sequence alignment and best match.'},
 {'original_no': 4,
  'key': 'sequence_fetch_url',
  'url_name': 'sequence_fetch_url',
  'name': 'Sequence fetch *',
  'description': 'Find cds and pep sequences for gene ids.'},
 {'original_no': 5,
  'key': 'sequenceserver_url',
  'url_name': 'sequenceserver_url',
  'name': 'Sequenceserver',
  'description': 'Leguminosae sequence alignment and Matching visualization.'},
 {'original_no': 6,
  'key': 'mcscanx_url',
  'url_name': 'mcscanx_url',
  'name': 'MCScanX',
  'description': 'Calls MCScanX software to perform collinearity analysis on arbitrary files.'},
 {'original_no': 7,
  'key': 'colinearscan_url',
  'url_name': 'colinearscan_url',
  'name': 'ColinearScan',
  'description': 'Calls the ColinearScan software to perform collinearity analysis on any file.'},
 {'original_no': 8,
  'key': 'synvisio_url',
  'url_name': 'synvisio_url',
  'name': 'Syntenic visualization',
  'description': 'A collinear visualization implemented by the invoked Synvisio software based on the results of '
                 'MCScanX.'},
 {'original_no': 9,
  'key': 'dupgen_finder_url',
  'url_name': 'dupgen_finder_url',
  'name': 'Dupgen finder',
  'description': 'The Dupgen finder software is invoked to analyze the type of gene replication.'},
 {'original_no': 10,
  'key': 'block_number_count_url',
  'url_name': 'block_number_count_url',
  'name': 'Block number count *',
  'description': 'Generates the block statistics result based on the ColinearScan result file.'},
 {'original_no': 11,
  'key': 'paraat_url',
  'url_name': 'paraat_url',
  'name': 'ParaAT',
  'description': 'Call ParaAT to calculate KaKs, generally used to compare pairs of gene sequences, reverse translate '
                 'and prepare input files.'},
 {'original_no': 12,
  'key': 'kaks_calculator_url',
  'url_name': 'kaks_calculator_url',
  'name': 'KaKs_Calculator',
  'description': 'Call KaKs Calculator to calculate KaKs, integrating a variety of algorithms (NG86, YN00, MYN, LWL85, '
                 'etc.).'},
 {'original_no': 13,
  'key': 'zu_ks_calculate_url',
  'url_name': 'zu_ks_calculate_url',
  'name': 'NG_KaKs_Cal *',
  'description': 'We calculate kaks using bioperl based on the NEi-Gojobori (NG86) algorithm.'},
 {'original_no': 14,
  'key': 'zu_blast_dotplot_url',
  'url_name': 'zu_blast_dotplot_url',
  'name': 'B_Dotter *',
  'description': 'Self-developed blastp dot plot function.'},
 {'original_no': 15,
  'key': 'zu_block_dotplot_url',
  'url_name': 'zu_block_dotplot_url',
  'name': 'BB_Dotter *',
  'description': 'Self-developed function of drawing block dot plots.'},
 {'original_no': 16,
  'key': 'zu_ks_dotplot_url',
  'url_name': 'zu_ks_dotplot_url',
  'name': 'BBK_Dotter *',
  'description': 'Self-developed ks dot plot function.'},
 {'original_no': 17,
  'key': 'zu_correspondence_mc_url',
  'url_name': 'zu_correspondence_mc_url',
  'name': 'Paleo-gene_identifer *',
  'description': 'Self-developed Correspondence process to generate the final mc result file.'},
 {'original_no': 18,
  'key': 'collinearity_generator_url',
  'url_name': 'collinearity_generator_url',
  'name': 'Collinearity generator *',
  'description': 'Self-developed to generate a collinear list according to multiple mc results generated.'},
 {'original_no': 19,
  'key': 'zu_retention_url',
  'url_name': 'zu_retention_url',
  'name': 'Paleo-gene_RI *',
  'description': 'Self-developed paleo-gene retention statistical tool based on mc results.'},
 {'original_no': 20,
  'key': 'zu_loss_url',
  'url_name': 'zu_loss_url',
  'name': 'Paleo-gene_RII *',
  'description': 'Self-developed ancient gene loss statistical tool based on mc results.'},
 {'original_no': 21,
  'key': 'zu_pindex_url',
  'url_name': 'zu_pindex_url',
  'name': 'P-index-calculator *',
  'description': 'Self-developed P-index calculation with customizable parameters.'},
 {'original_no': 22,
  'key': 'draw_list_tree_url',
  'url_name': 'draw_list_tree_url',
  'name': 'Draw_list_trees *',
  'description': 'Self-developed tree formation based on collinear list.'},
 {'original_no': 23,
  'key': 'GC_calculation_url',
  'url_name': 'GC_calculation_url',
  'name': 'GC-calculation *',
  'description': 'Calculation of GC content of genome or CDS sequence.'},
 {'original_no': 24,
  'key': 'chromosome_length_url',
  'url_name': 'chromosome_length_url',
  'name': 'Chromosome length extractor *',
  'description': 'Chromosome length or gene length statistics.'},
 {'original_no': 25,
  'key': 'geme_cds_exon_counter_url',
  'url_name': 'geme_cds_exon_counter_url',
  'name': 'Gene_cds_exon_counter *',
  'description': 'Calculates the length and proportion of cds, exon, intron, and gene in the original gff file.'},
 {'original_no': 26,
  'key': 'GenomeMountRateCalculator_url',
  'url_name': 'GenomeMountRateCalculator_url',
  'name': 'Genome Mount Rate Calculator *',
  'description': 'Genome mount rate calculator.'},
 {'original_no': 27,
  'key': 'GF_ks_circos_url',
  'url_name': 'GF_ks_circos_url',
  'name': 'GF_Circos *',
  'description': 'Self-developed ks circle diagram function.'},
 {'original_no': 28,
  'key': 'codonw_url',
  'url_name': 'codonw_url',
  'name': 'Codonw',
  'description': 'Call Codonw, statistical sequence codon situation.'},
 {'original_no': 29,
  'key': 'cpgfinder_url',
  'url_name': 'cpgfinder_url',
  'name': 'Cpgfinder',
  'description': 'Call Cpgfinder to find CpG islands in the sequence.'},
 {'original_no': 30,
  'key': 'meme_suit_url',
  'url_name': 'meme_suit_url',
  'name': 'MEME Suite',
  'description': 'Motif of invoked memes, predicted proteins.'},
 {'original_no': 31,
  'key': 'gsds_url',
  'url_name': 'gsds_url',
  'name': 'GSDS',
  'description': 'Called GSDS to achieve the function of drawing gene structure (CDS, UTR, Intron).'},
 {'original_no': 32,
  'key': 'hmmer_url',
  'url_name': 'hmmer_url',
  'name': 'Hmmer',
  'description': 'Invoking the Hmmer for gene family screening.'},
 {'original_no': 33,
  'key': 'pfam_url',
  'url_name': 'pfam_url',
  'name': 'Pfam',
  'description': 'Pfam is invoked to realize the function of identifying protein domains.'},
 {'original_no': 34,
  'key': 'interproscan_url',
  'url_name': 'interproscan_url',
  'name': 'Interproscan',
  'description': 'Invoke interproscan software to achieve gene function annotation.'},
 {'original_no': 35,
  'key': 'sequence_alignment_url',
  'url_name': 'sequence_alignment_url',
  'name': 'Seq alignment',
  'description': 'Multi-sequence alignment software (mafft, clustalw, and muscle).'},
 {'original_no': 36,
  'key': 'fasttree_url',
  'url_name': 'fasttree_url',
  'name': 'FastTree',
  'description': 'Call FastTree software to achieve the function of building a phylogenetic tree.'},
 {'original_no': 37,
  'key': 'iq_tree_url',
  'url_name': 'iq_tree_url',
  'name': 'IQ-Tree',
  'description': 'Call IQ-Tree software to achieve the function of building a phylogenetic tree.'},
 {'original_no': 38,
  'key': 'iTAK_url',
  'url_name': 'iTAK_url',
  'name': 'TransFam identifier',
  'description': 'Regulatory protein (RKs) prediction, invoked by iTak software.'},
 {'original_no': 39,
  'key': 'draw_heatmap_url',
  'url_name': 'draw_heatmap_url',
  'name': 'Heatmap *',
  'description': 'Calculate correlations between gene expression patterns and metabolite content patterns and draw '
                 'heat maps.'},
 {'original_no': 40,
  'key': 'lollipop_chart_url',
  'url_name': 'lollipop_chart_url',
  'name': 'Lollipop *',
  'description': 'Draw a lollipop chart function for metabolites or gene expression.'},
 {'original_no': 41,
  'key': 'draw_gene_structure_url',
  'url_name': 'draw_gene_structure_url',
  'name': 'Gene structure *',
  'description': 'Function to visualize the position of genes on chromosomes.'},
 {'original_no': 42,
  'key': 'circos_url',
  'url_name': 'circos_url',
  'name': 'ShinyCircos',
  'description': 'Call ShinyCircos to draw a circos diagram.'},
 {'original_no': 43,
  'key': 'species_classification_url',
  'url_name': 'species_classification_url',
  'name': 'Species classification *',
  'description': 'Obtain the classification of the species from NCBI in batches.'},
 {'original_no': 44,
  'key': 'sequence_screening_url',
  'url_name': 'sequence_screening_url',
  'name': 'SS-extractor *',
  'description': 'Extract gene ID information from pep/cds/gff files based on an ID file.'},
 {'original_no': 45,
  'key': 'saf_converter_url',
  'url_name': 'saf_converter_url',
  'name': 'SAF-converter *',
  'description': 'Format conversions including genbank, fasta, embl, fastq, clustal, phylip, and nexus.'},
 {'original_no': 46,
  'key': 'find_replace_url',
  'url_name': 'find_replace_url',
  'name': 'BDI-finder *',
  'description': 'Search and replace tool for file contents.'},
 {'original_no': 47,
  'key': 'quchong_url',
  'url_name': 'quchong_url',
  'name': 'BDI-deduplicator *',
  'description': 'Delete duplicate gene IDs and sequences in pep or cds files.'},
 {'original_no': 48,
  'key': 'bdi_extractor_url',
  'url_name': 'bdi_extractor_url',
  'name': 'BDI-extractor *',
  'description': 'Extract data by column from uploaded files.'},
 {'original_no': 49,
  'key': 'bdi_combiner_url',
  'url_name': 'bdi_combiner_url',
  'name': 'BDI-combiner *',
  'description': 'File merge tool for multiple files of the same format.'},
 {'original_no': 50,
  'key': 'deal_stars_url',
  'url_name': 'deal_stars_url',
  'name': 'Deal_stars *',
  'description': 'Delete stop codons ("." and "*") from pep protein files.'},
 {'original_no': 51,
  'key': 'subtree_extractor_url',
  'url_name': 'subtree_extractor_url',
  'name': 'Subtree_extractor *',
  'description': 'Extracts a specified range of small phylogenetic trees from a large tree file.'},
 {'original_no': 52,
  'key': 'wgdimcs_url',
  'url_name': 'wgdimcs_url',
  'name': 'Block_run',
  'description': 'Syntenic analysis tool based on WGDI.'},
 {'original_no': 53,
  'key': 'wgdikaks_url',
  'url_name': 'wgdikaks_url',
  'name': 'KaKs calculate',
  'description': 'Calculation KaKs tool based on WGDI (Nei-Gojobori algorithm/YN00).'},
 {'original_no': 54,
  'key': 'wgdi_dotplot_url',
  'url_name': 'wgdi_dotplot_url',
  'name': 'Blast dotplot',
  'description': 'WGDI-based blast dotplot tool.'},
 {'original_no': 55,
  'key': 'wgdikaks_dot_url',
  'url_name': 'wgdikaks_dot_url',
  'name': 'Ks dotplot',
  'description': 'Ks dotplot tool based on WGDI.'},
 {'original_no': 56,
  'key': 'wgdi_blockinfo_url',
  'url_name': 'wgdi_blockinfo_url',
  'name': 'Block_info',
  'description': 'Screening out collinear fragments based on WGDI.'},
 {'original_no': 57,
  'key': 'wgdi_correspondence_url',
  'url_name': 'wgdi_correspondence_url',
  'name': 'Correspondence',
  'description': 'Correspondence process based on WGDI.'},
 {'original_no': 58,
  'key': 'jbrowse_url',
  'url_name': 'jbrowse_url',
  'name': 'JBrowse',
  'description': 'Gene browser function to view genome and GFF files.'},
 {'original_no': 59,
  'key': 'bbm_extraction_url',
  'url_name': 'bbm_extraction_url',
  'name': 'bbm_extraction',
  'description': 'Calculation Tool: BLAST Best Match Extractor.'},
 {'original_no': 60,
  'key': 'ks_distriplot_url',
  'url_name': 'ks_distriplot_url',
  'name': 'ks_distriplot',
  'description': 'Visualizing Ks Distributions with Seaborn Ridge Plots.'},
 {'original_no': 61,
  'key': 'cds2geno_dotplot_url',
  'url_name': 'cds2geno_dotplot_url',
  'name': 'cds2geno_dotplot',
  'description': 'Synteny Visualization based on CDS Mapping.'},
 {'original_no': 62,
  'key': 'mga_circos_url',
  'url_name': 'mga_circos_url',
  'name': 'mga_circos',
  'description': 'Multi-Genome Analysis: Synteny Visualization.'}]

TOOL_USAGE_KEY_SET = {tool['key'] for tool in TOOL_USAGE_TOOLS}
TOOL_USAGE_COUNTER_FILE = os.path.join(settings.BASE_DIR, 'tool_usage_counts.json')
TOOL_USAGE_LOCK = threading.Lock()


def read_tool_usage_counts():
    """Read persistent total usage counts for tools shown on all_tools.html."""
    if not os.path.isfile(TOOL_USAGE_COUNTER_FILE):
        return {}

    try:
        with open(TOOL_USAGE_COUNTER_FILE, 'r', encoding='utf-8') as usage_file:
            raw_counts = json.load(usage_file)
    except Exception:
        return {}

    cleaned_counts = {}
    for key, value in raw_counts.items():
        if key not in TOOL_USAGE_KEY_SET:
            continue
        try:
            cleaned_counts[key] = max(0, int(value))
        except (TypeError, ValueError):
            cleaned_counts[key] = 0
    return cleaned_counts


def write_tool_usage_counts(counts):
    """Write usage counts atomically to avoid partially written JSON files."""
    counter_dir = os.path.dirname(TOOL_USAGE_COUNTER_FILE)
    if counter_dir:
        os.makedirs(counter_dir, exist_ok=True)

    temp_path = TOOL_USAGE_COUNTER_FILE + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as usage_file:
        json.dump(counts, usage_file, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(temp_path, TOOL_USAGE_COUNTER_FILE)


def build_all_tools_with_usage():
    counts = read_tool_usage_counts()
    tools_with_usage = []

    for tool in TOOL_USAGE_TOOLS:
        item = dict(tool)
        item['usage_count'] = counts.get(tool['key'], 0)
        item['is_hot'] = False
        item['hot_rank'] = None
        tools_with_usage.append(item)

    hot_tools = sorted(
        [tool for tool in tools_with_usage if tool['usage_count'] > 0],
        key=lambda tool: (-tool['usage_count'], tool['original_no'])
    )[:10]
    hot_key_rank = {tool['key']: rank for rank, tool in enumerate(hot_tools, start=1)}

    for tool in tools_with_usage:
        if tool['key'] in hot_key_rank:
            tool['is_hot'] = True
            tool['hot_rank'] = hot_key_rank[tool['key']]

    hot_key_set = set(hot_key_rank)
    ordered_tools = hot_tools + [tool for tool in tools_with_usage if tool['key'] not in hot_key_set]
    return ordered_tools


@csrf_exempt
def tool_usage_record(request):
    """Increment a tool's total usage count when users open it from the tools list."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    tool_key = ''
    try:
        if request.body:
            payload = json.loads(request.body.decode('utf-8'))
            tool_key = str(payload.get('tool_key', '')).strip()
        else:
            tool_key = str(request.POST.get('tool_key', '')).strip()
    except Exception:
        tool_key = str(request.POST.get('tool_key', '')).strip()

    if tool_key not in TOOL_USAGE_KEY_SET:
        return JsonResponse({'error': 'Invalid tool_key'}, status=400)

    # 防止一次点击因为前端重复绑定、浏览器重试或用户快速重复点击而被记两次。
    now = time.time()
    last_record = request.session.get('tool_usage_last_record') or {}
    last_tool_key = last_record.get('tool_key')
    try:
        last_record_time = float(last_record.get('record_time', 0))
    except (TypeError, ValueError):
        last_record_time = 0

    if last_tool_key == tool_key and now - last_record_time < 2:
        counts = read_tool_usage_counts()
        return JsonResponse({
            'tool_key': tool_key,
            'usage_count': counts.get(tool_key, 0),
            'duplicate_ignored': True,
        })

    with TOOL_USAGE_LOCK:
        counts = read_tool_usage_counts()
        counts[tool_key] = counts.get(tool_key, 0) + 1
        write_tool_usage_counts(counts)
        usage_count = counts[tool_key]

    request.session['tool_usage_last_record'] = {
        'tool_key': tool_key,
        'record_time': now,
    }
    request.session.modified = True

    return JsonResponse({'tool_key': tool_key, 'usage_count': usage_count})


def all_tools(request):
    return render(request, 'all_tools.html', {'tools': build_all_tools_with_usage()})


def blast(request):
    return render(request, 'f_blast.html')


def blast_match(request):
    return render(request, 'blast_match.html')


def sequence_fetch(request):
    return render(request, 'sequence_fetch.html')


def sequenceserver(request):
    return render(request, 'sequenceserver.html')

def dupgene_finder_tools(request):
    return render(request, 'dupgene_finder_tools.html')

# 两个共线性工具
def mcscanx(request):
    return render(request, 'mcscanx.html')


def colinearscan(request):
    return render(request, 'colinearscan.html')


# 4个 WGDI 功能
def wgdi_dotplot(request):
    return render(request, 'wgdi_dotplot.html')


def wgdimcs(request):
    return render(request, 'wgdimcs.html')


def wgdikaks(request):
    return render(request, 'wgdikaks.html')


def wgdi_blockinfo(request):
    return render(request, 'wgdi_blockinfo.html')


def wgdi_correspondence(request):
    return render(request, 'wgdi_correspondence.html')


def wgdikaks_dot(request):
    return render(request, 'wgdikaks_dot.html')


def GC_calculation(request):
    return render(request, 'GC_calculation.html')


def chromosome_length(request):
    return render(request, 'chromosome_length.html')


def geme_cds_exon_counter(request):
    return render(request, 'gene_structure_stats.html')

def GenomeMountRateCalculator(request):
    return render(request, 'GenomeMountRateCalculator.html')

# orther 工具
def file_merge(request):
    return render(request, 'file_merge.html')


def formatTofasta(request):
    return render(request, 'formatTofasta.html')


def find_replace(request):
    return render(request, 'find_replace.html')


def extract_row(request):
    return render(request, 'extract_row.html')


def duplicate_removal(request):
    return render(request, 'quchong.html')


# circos、jbrowse
def circos(request):
    return render(request, 'circos.html')


def jbrowse(request):
    return render(request, 'jbrowse.html')


def synvisio(request):
    return render(request, 'synvisio.html')


def gsds(request):
    return render(request, 'gsds.html')


def docker(request):
    return render(request, 'docker.html')


def karyotype_in(request):
    return render(request, 'karyotype_in.html')


def karyotype_in_html(request):
    return render(request, 'karyotype_html/karyotype_in.html')


def dupgen_finder(request):
    return render(request, 'dupgen_finder.html')


def gene_type(request):
    return render(request, 'gene_type.html')


def cpgfinder(request):
    return render(request, 'cpgfinder.html')


def phyml(request):
    return render(request, 'phyml.html')


def sequence_alignment(request):
    return render(request, 'sequence_alignment.html')


def sequence_screening(request):
    return render(request, 'sequence_screening.html')


def draw_heatmap(request):
    return render(request, 'draw_heatmap.html')

def lollipop_chart(request):
    return render(request, 'lollipop_chart.html')
def draw_gene_structure(request):
    return render(request, 'draw_gene_structure.html')

def Browse(request):
    return render(request, 'Browse.html')


def diamond(request):
    return render(request, 'diamond.html')


def paraat(request):
    return render(request, 'paraat.html')


def kaks_calculator(request):
    return render(request, 'kaks_calculator.html')


def fasttree(request):
    return render(request, 'fasttree.html')


def hmmer(request):
    return render(request, 'hmmer.html')


def meme_suit(request):
    return render(request, 'meme_suit.html')


def pfam(request):
    return render(request, 'pfam.html')


def iq_tree(request):
    return render(request, 'iq_tree.html')


def codonw(request):
    return render(request, 'codonw.html')


# 核型进化组内流程
def f_blast_html(request):
    return render(request, 'karyotype_html/f_blast.html')


def colinearscan_html(request):
    return render(request, 'karyotype_html/colinearscan.html')


def synvisio_html(request):
    return render(request, 'karyotype_html/synvisio.html')


def zu_blast_dotplot_html(request):
    return render(request, 'karyotype_html/zu_blast_dotplot.html')


def zu_block_dotplot_html(request):
    return render(request, 'karyotype_html/zu_block_dotplot.html')


def zu_correspondence_mc_html(request):
    return render(request, 'karyotype_html/zu_correspondence_mc.html')


def interproscan(request):
    return render(request, 'interproscan.html')


def deal_star(request):
    return render(request, 'deal_star.html')


def subtree_extractor(request):
    return render(request, 'subtree_extractor.html')


def iTAK(request):
    return render(request, 'iTAK.html')

def block_number_count(request):
    return render(request, 'block_number_count.html')


def collinearity_generator(request):
    return render(request, 'collinearity_generator.html')


def draw_list_tree(request):
    return render(request, 'draw_list_tree.html')


def species_classification(request):
    return render(request, 'species_classification.html')

def GF_ks_circos(request):
    from tools.offline_views.GF_Circos import views as gf_circos_views
    return gf_circos_views.GF_ks_circos(request)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# blast + diamond
# ==========================================
# 辅助函数：根据操作系统获取软件路径 服务于 f_blast.html 和 diamond.html
# ==========================================
def get_tool_path(tool_name):
    """
    根据操作系统返回调用的命令或绝对路径
    """
    system_platform = platform.system()

    if system_platform == 'Linux':
        # Linux 服务器路径配置
        BLAST_BIN_DIR = "/wangjp/yuzijian/tools/ncbi-blast-2.15.0+/bin/"
        DIAMOND_BIN_DIR = "/www/tools/soft_tools/"

        if tool_name in ['blastn', 'blastp', 'blastx', 'makeblastdb']:
            return os.path.join(BLAST_BIN_DIR, tool_name)

        elif tool_name == 'diamond':
            # 注意：这里假设 diamond 的可执行文件名就是 'diamond'
            return os.path.join(DIAMOND_BIN_DIR, 'diamond')

    # Windows 环境 (假设已配置环境变量) 或其他情况
    return tool_name


# ==========================================
# f_blast.html中 BLAST 视图函数修改
# ==========================================
def blast_run(request):
    patten = request.POST.get('patten', None)  # 获取原始模式，如 'blastp'
    myFile1 = request.FILES.get('file1', None)
    myFile2 = request.FILES.get('file2', None)
    e_value = str(request.POST.get('e_value', None))
    sco = request.POST.get('score_1', None)
    iden = request.POST.get('identity_1', None)

    # 逻辑判断依然使用原始的 'blastp' / 'blastn'
    nucl_or_prot = "prot" if patten == 'blastp' else "nucl"

    if myFile1 is None or myFile2 is None:
        return render(request, 'f_blast.html')
    c = name_set()

    myFile1_name = myFile1.name.split(".")[0]
    myFile2_name = myFile2.name.split(".")[0]
    myFile1.name = '1.fasta'
    myFile2.name = '2.fasta'
    keep_file(na=myFile1, c=c)
    keep_file(na=myFile2, c=c)

    # --- 关键修改开始 ---
    # 获取实际执行的命令路径
    # 如果是 Linux，这里 patten_cmd 会变成 /wangjp/.../bin/blastp
    # 如果是 Windows，这里 patten_cmd 还是 blastp
    patten_cmd = get_tool_path(patten)

    # 注意：这里假设 blast_run_tools 内部是用 patten 参数直接拼接命令行的
    # 如果 blast_run_tools 内部还需要调用 makeblastdb，请确保它也能找到 makeblastdb
    blast_run_tools(place=c, patten=patten_cmd, e=e_value, score=sco, identity=iden, myFile1=myFile1_name,
                    myFile2=myFile2_name, nucl_or_prot=nucl_or_prot)
    # --- 关键修改结束 ---

    files = f"{myFile1_name}_{myFile2_name}.fasta sequence.txt"
    return zip_file(request, c, files)


# ==========================================
# DIAMOND 视图函数修改
# ==========================================
@csrf_exempt
@guarded_tool_view
def diamond_run(request):
    """
    执行 DIAMOND 比对并在同一页面返回结果
    """
    if request.method == 'POST':
        try:
            # 1. 获取参数
            program = request.POST.get('patten')  # blastp 或 blastx
            program = choice(program, ('blastp', 'blastx'), 'alignment program')
            file1 = request.FILES.get('file1')  # Target Database
            file2 = request.FILES.get('file2')  # Query Sequence

            # 获取数值参数
            try:
                e_value_thresh = float(request.POST.get('e_value', 1e-3))
            except ValueError:
                e_value_thresh = 1e-3

            try:
                min_score = float(request.POST.get('score_1', 0))
            except ValueError:
                min_score = 0

            try:
                min_identity = float(request.POST.get('identity_1', 0))
            except ValueError:
                min_identity = 0

            # 获取灵敏度模式
            sensitivity = choice(request.POST.get('sensitive', '--sensitive'), DIAMOND_SENSITIVITY, 'sensitivity')

            if not file1 or not file2:
                return HttpResponse("Error: Both Target (Protein) and Query files are required.", status=400)

            # --- 关键修改开始 ---
            # 获取 diamond 可执行文件的路径
            diamond_exe = get_tool_path('diamond')
            # --- 关键修改结束 ---

            # 2. 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                target_path = os.path.join(temp_dir, "target.dmnd")
                target_fasta = os.path.join(temp_dir, "target.fasta")
                query_path = os.path.join(temp_dir, "query.fasta")

                # 保存文件
                with open(target_fasta, 'wb+') as dest:
                    for chunk in file1.chunks(): dest.write(chunk)
                with open(query_path, 'wb+') as dest:
                    for chunk in file2.chunks(): dest.write(chunk)

                # 3. 建库 (diamond makedb)
                # 使用变量 diamond_exe 替代硬编码的 "diamond"
                cmd_makedb = ['diamond', 'makedb', '--in', target_fasta, '--db', target_path, '--threads', '2']
                run_command(cmd_makedb)

                # 4. 运行比对
                out_path = os.path.join(temp_dir, "diamond_results.txt")

                # 使用变量 diamond_exe 替代硬编码的 "diamond"
                cmd_diamond = ['diamond', program, sensitivity, '--query', query_path, '--db', target_path, '--out', out_path, '--evalue', str(e_value_thresh), '--outfmt', '6', 'qseqid', 'sseqid', 'pident', 'length', 'mismatch', 'gapopen', 'qstart', 'qend', 'sstart', 'send', 'evalue', 'bitscore', '--threads', '2']

                run_command(cmd_diamond)

                # 5. 解析结果
                results = []
                raw_output = ""

                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    # A. 读取原始内容用于下载
                    with open(out_path, 'r', encoding='utf-8') as f:
                        raw_output = f.read()

                    # B. 解析表格用于展示
                    col_names = ["qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
                                 "qstart", "qend", "sstart", "send", "evalue", "bitscore"]
                    # 增加容错：如果文件为空或格式不对，pandas可能会报错，建议加 try-except
                    try:
                        df = pd.read_csv(out_path, sep='\t', names=col_names)

                        for _, row in df.iterrows():
                            if row['bitscore'] >= min_score and row['pident'] >= min_identity:
                                results.append({
                                    'query': row['qseqid'],
                                    'hit': row['sseqid'],
                                    'evalue': "{:.2e}".format(row['evalue']),
                                    'score': row['bitscore'],
                                    'identity': f"{row['pident']:.2f}%"
                                })
                    except Exception as e:
                        print(f"Error parsing diamond output: {e}")

                return render(request, 'diamond.html', {
                    'results': results,
                    'raw_output': raw_output,
                    'has_result': True
                })
        except (ToolInputError, subprocess.TimeoutExpired):
            raise
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Calculation failed. Check the input format and parameters.'}, status=500)

    # 如果不是POST请求，返回空页面（假设你有这个逻辑）
    return render(request, 'diamond.html')

# blast_match_run
def blast_match_run(request):
    patten = request.POST.get("patten", None)
    species_data = request.POST.get("species_data", None)
    myFile1 = request.FILES.get("file1", None)
    e_value = str(request.POST.get('e_value', None))
    sco = request.POST.get('score_1', None)
    iden = request.POST.get('identity_1', None)
    nucl_or_prot = "prot" if patten == 'blastp' else "nucl"
    if myFile1 is None:
        return render(request, 'blast_match.html')
    c = name_set()
    myFile1.name = '1.fasta'
    keep_file(na=myFile1, c=c)
    blast_match_run_tools(place=c, patten=patten, species_data=species_data, e=e_value, score=sco, identity=iden, nucl_or_prot=nucl_or_prot)
    files = "result_2.fasta sequence.txt"
    return zip_file(request, c, files)


# MCScanX
def mcscanx_zip_file(place, file_name):
    base_dir = os.path.join(path_get, 'file_keep', place)
    zip_file_path = os.path.join(base_dir, 'result.zip')
    target_files = [
        f'{file_name}.html',
        f'{file_name}.collinearity',
        f'{file_name}.tandem',
        'gene_classifier.txt',
    ]

    added_files = 0

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in target_files:
                file_path = os.path.join(base_dir, filename)
                if os.path.isfile(file_path):
                    zipf.write(file_path, arcname=filename)
                    added_files += 1

        if added_files == 0:
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
            return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=404)

        response = FileResponse(open(zip_file_path, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename="result.zip"'
        response.set_cookie('mcscanx_download', 'done', max_age=60, path='/')
        return response
    except Exception:
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=500)


def colinearscan_zip_file(place):
    base_dir = os.path.join(path_get, 'file_keep', place)
    zip_file_path = os.path.join(base_dir, 'result.zip')
    target_dirs = ['block', 'pair']

    added_files = 0

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for dirname in target_dirs:
                dir_path = os.path.join(base_dir, dirname)
                if not os.path.isdir(dir_path):
                    continue

                for root, _, filenames in os.walk(dir_path):
                    for filename in filenames:
                        abs_file_path = os.path.join(root, filename)
                        arcname = os.path.relpath(abs_file_path, base_dir)
                        zipf.write(abs_file_path, arcname=arcname)
                        added_files += 1

        if added_files == 0:
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
            return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=404)

        response = FileResponse(open(zip_file_path, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename="result.zip"'
        response.set_cookie('colinearscan_download', 'done', max_age=60, path='/')
        return response
    except Exception:
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=500)


def kaks_calculator_zip_file(place):
    base_dir = os.path.join(path_get, 'file_keep', place)
    zip_file_path = os.path.join(base_dir, 'result.zip')
    target_file = 'result_kaks.txt'
    file_path = os.path.join(base_dir, target_file)

    try:
        if not os.path.isfile(file_path):
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
            return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=404)

        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, arcname=target_file)

        response = FileResponse(open(zip_file_path, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename="result.zip"'
        response.set_cookie('kaks_calculator_download', 'done', max_age=60, path='/')
        return response
    except Exception:
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        return HttpResponse(f"Error: Zip file was not generated at {zip_file_path}", status=500)


def save_mcscanx_text_file(place, filename, content):
    file_path = os.path.join(path_get, 'file_keep', place, filename)
    text_content = content if content.endswith('\n') else content + '\n'
    with open(file_path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text_content)


def save_colinearscan_text_file(place, filename, content):
    file_path = os.path.join(path_get, 'file_keep', place, filename)
    normalized_lines = []

    for raw_line in content.splitlines():
        stripped_line = raw_line.strip()
        if not stripped_line:
            continue
        normalized_lines.append('\t'.join(stripped_line.split()))

    text_content = '\n'.join(normalized_lines)
    if text_content and not text_content.endswith('\n'):
        text_content += '\n'

    with open(file_path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text_content)


@guarded_tool_view
def mcscanx_run(request):
    myFile1 = request.FILES.get("file1", None)
    myFile2 = request.FILES.get("file2", None)
    blast_text = (request.POST.get("query_sequence") or "").strip()
    gff_text = (request.POST.get("query_sequence_2") or "").strip()

    if myFile1 is None and not blast_text:
        return render(request, 'mcscanx.html')
    if myFile2 is None and not gff_text:
        return render(request, 'mcscanx.html')

    c = name_set()
    file_name = 'mcscanx_input'

    blast_filename = f'{file_name}.blast'
    gff_filename = f'{file_name}.gff'

    if myFile1 is not None:
        myFile1.name = blast_filename
        keep_file(na=myFile1, c=c)
    else:
        save_mcscanx_text_file(c, blast_filename, blast_text)

    if myFile2 is not None:
        myFile2.name = gff_filename
        keep_file(na=myFile2, c=c)
    else:
        save_mcscanx_text_file(c, gff_filename, gff_text)

    mcscanx_run_tools(place=c, file_name=file_name)
    return mcscanx_zip_file(c, file_name)


# Colinearscan_run
def colinearscan_run(request):
    blast = request.FILES.get("blast", None)
    gff1 = request.FILES.get("gff1", None)
    gff2 = request.FILES.get("gff2", None)
    blast_text = (request.POST.get("query_sequence") or "").strip()
    gff1_text = (request.POST.get("query_sequence_2") or "").strip()
    gff2_text = (request.POST.get("query_sequence_3") or "").strip()
    e_value = str(request.POST.get('e_value', None))
    score = request.POST.get('score', None)
    hitnum = request.POST.get('hitnum', None)
    pos_order = str(request.POST.get('pos_order', None))
    cdsvchr = request.POST.get('cdsvchr', None)

    if blast is None and not blast_text:
        return render(request, 'colinearscan.html')
    if gff1 is None and not gff1_text:
        return render(request, 'colinearscan.html')
    if gff2 is None and not gff2_text:
        return render(request, 'colinearscan.html')

    c = name_set()

    if blast is not None:
        file_name = blast.name.split('.')[0]
    elif gff1 is not None:
        file_name = gff1.name.split('.')[0]
    elif gff2 is not None:
        file_name = gff2.name.split('.')[0]
    else:
        file_name = 'colinearscan_input'

    blast_filename = f'{file_name}.blast'
    gff1_filename = '11.gff'
    gff2_filename = '22.gff'

    if blast is not None:
        blast.name = blast_filename
        keep_file(na=blast, c=c)
    else:
        save_colinearscan_text_file(c, blast_filename, blast_text)

    if gff1 is not None:
        gff1.name = gff1_filename
        keep_file(na=gff1, c=c)
    else:
        save_colinearscan_text_file(c, gff1_filename, gff1_text)

    if gff2 is not None:
        gff2.name = gff2_filename
        keep_file(na=gff2, c=c)
    else:
        save_colinearscan_text_file(c, gff2_filename, gff2_text)

    colinearscan_run_tools(
        place=c,
        score=score,
        e_value=e_value,
        hitnum=hitnum,
        pos_order=pos_order,
        cdsvchr=cdsvchr,
        blast_name=blast_filename,
        gff1_name=gff1_filename,
        gff2_name=gff2_filename,
        file_name=file_name,
    )
    return colinearscan_zip_file(c)


# wgdi共线性分析
@xframe_options_sameorigin
def wgdimcs_run(request):
    # 五个文件
    blast = request.FILES.get('blast', None)
    heng_len = request.FILES.get('heng_len', None)
    shu_len = request.FILES.get('shu_len', None)
    heng_gff = request.FILES.get('heng_gff', None)
    shu_gff = request.FILES.get('shu_gff', None)
    # 四种参数-值
    evalue = str(request.POST.get('evalue', None))
    score = request.POST.get('score', None)
    if blast is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None:
        return render(request, 'wgdimcs.html')

    c = name_set()
    blast.name = 'diamond.fasta'
    heng_gff.name = '11.gff'
    shu_gff.name = '22.gff'
    heng_len.name = '11.len'
    shu_len.name = '22.len'

    keep_file(na=blast, c=c)
    keep_file(na=shu_gff, c=c)
    keep_file(na=heng_gff, c=c)
    keep_file(na=shu_len, c=c)
    keep_file(na=heng_len, c=c)
    try:
        start_wgdimcs_background_job(c, evalue, score)
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdimcs_download')
    except Exception as exc:
        return wgdi_runtime_error_response(exc, 'wgdimcs_download')
    return wgdimcs_job_started_response(c)


def synvisio_run(request):
    sp_data_1 = request.POST.get("sp_data_1") or request.GET.get("sp_data_1")
    sp_data_2 = request.POST.get("sp_data_2") or request.GET.get("sp_data_2")

    if not sp_data_1 or not sp_data_2:
        return render(request, 'synvisio.html')

    dashboard_url = f"https://synteny_viewer.cgrpoee.top/#/dashboard/{sp_data_1}_{sp_data_2}"
    return render(request, 'synvisio_run.html', {'dashboard_url': dashboard_url})


# paraat
@guarded_tool_view
def paraat_run(request):
    patten = request.POST.get('patten', None)
    homologs = request.FILES.get("homologs", None)
    cds = request.FILES.get('cds', None)
    pep = request.FILES.get('pep', None)

    if homologs is None or cds is None or pep is None:
        return render(request, '../templates/paraat.html')
    patten = choice(patten, PARAAT_FORMATS, 'alignment format')
    c = name_set()
    homologs.name = 'hom.homologs'
    cds.name = 'cds.cds'
    pep.name = 'pep.pep'
    keep_file(na=homologs, c=c)
    keep_file(na=cds, c=c)
    keep_file(na=pep, c=c)

    paraat_run_tools(place=c, patten=patten)
    files = f'{path_get}/file_keep/{c}/result.{patten}'
    return zip_file(request, c, files)


# kaks_calculator
@guarded_tool_view
def kaks_calculator_run(request):
    patten = request.POST.get('patten', None)
    kaks = request.FILES.get("kaks", None)
    if kaks is None:
        return render(request, '../templates/kaks_calculator.html')
    patten = choice(patten, KAKS_METHODS, 'KaKs method')
    c = name_set()
    kaks.name = 'kaks.axt'
    keep_file(na=kaks, c=c)
    kaks_calculator_run_tools(place=c, patten=patten)
    return kaks_calculator_zip_file(c)


# zu_ks_calculate_run
def zu_ks_calculate_run(request):
    cds1 = request.FILES.get('cds1', None)
    cds2 = request.FILES.get('cds2', None)
    block = request.FILES.get('block', None)
    if cds1 is None or cds2 is None or block is None:
        return render(request, '../tools/templates/zu_ks_calculate.html')
    c = name_set()
    keep_file(na=cds1, c=c)
    keep_file(na=cds2, c=c)
    keep_file(na=block, c=c)
    zu_ks_calculate_run_tools(place=c)
    files = f"ks/*"
    return zip_file(request, c, files)


# wgdi 计算 kaks
@xframe_options_sameorigin
def wgdikaks_run(request):
    pep = request.FILES.get('pep', None)
    cds = request.FILES.get('cds', None)
    colinearity = request.FILES.get('colinearity', None)
    if colinearity is None or cds is None or pep is None:
        return render(request, 'wgdikaks.html')
    c = name_set()
    pep.name = 'pep.fasta'
    cds.name = 'cds.fasta'
    colinearity.name = 'colinearity.txt'
    keep_file(na=pep, c=c)
    keep_file(na=cds, c=c)
    keep_file(na=colinearity, c=c)
    try:
        start_wgdikaks_background_job(c)
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdikaks_download')
    except Exception as exc:
        return wgdi_runtime_error_response(exc, 'wgdikaks_download')
    return wgdikaks_job_started_response(c)

# 三种点图绘制
def zu_blast_dotplot_run(request):
    blast = request.FILES.get('blast', None)
    shu_len = request.FILES.get('shu_len', None)
    shu_gff = request.FILES.get('shu_gff', None)
    heng_len = request.FILES.get('heng_len', None)
    heng_gff = request.FILES.get('heng_gff', None)

    if blast is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None:
        return render(request, '../tools/templates/zu_blast_dotplot.html')
    c = name_set()

    shu_len_name = shu_len.name.split(".")[0]
    heng_len_name = heng_len.name.split(".")[0]

    blast.name = f"{shu_len_name}_{heng_len_name}.new.blast"
    shu_len.name = f"{shu_len_name}.lens"
    heng_len.name = f"{heng_len_name}.lens"
    shu_gff.name = f"{shu_len_name}.new.gff"
    heng_gff.name = f"{heng_len_name}.new.gff"

    keep_file(na=blast, c=c)
    keep_file(na=heng_len, c=c)
    keep_file(na=shu_len, c=c)
    keep_file(na=heng_gff, c=c)
    keep_file(na=shu_gff, c=c)

    zu_blast_dotplot_run_tools(place=c, shu_len_name=shu_len_name, heng_len_name=heng_len_name)
    result_files = glob.glob(os.path.join(path_get, 'file_keep', c, '*_corr.png'))
    if not result_files:
        return HttpResponse("Error: Result png was not generated.", status=404)

    result_file = result_files[0]
    response = FileResponse(open(result_file, 'rb'))
    response['Content-Type'] = 'image/png'
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(result_file)}"'
    response.set_cookie('zu_blast_dotplot_download', 'done', max_age=60, path='/')
    return response

def zu_block_dotplot_run(request):

    blast = request.FILES.get('blast', None)

    block = request.FILES.get('block', None)

    shu_len = request.FILES.get('shu_len', None)

    shu_gff = request.FILES.get('shu_gff', None)

    heng_len = request.FILES.get('heng_len', None)

    heng_gff = request.FILES.get('heng_gff', None)

    block_num = request.POST.get('block_num')



    if blast is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None or block is None:

        return render(request, '../tools/templates/zu_block_dotplot.html')

    c = name_set()



    shu_len_name = shu_len.name.split(".")[0]

    heng_len_name = heng_len.name.split(".")[0]



    keep_file(na=blast, c=c)

    keep_file(na=block, c=c)

    keep_file(na=heng_len, c=c)

    keep_file(na=shu_len, c=c)

    keep_file(na=heng_gff, c=c)

    keep_file(na=shu_gff, c=c)



    zu_block_dotplot_run_tools(place=c, shu_len_name=shu_len_name, heng_len_name=heng_len_name, block_num=block_num)

    files = f"*.png"

    return zip_file(request, c, files)

def zu_ks_dotplot_run(request):
    blast = request.FILES.get('blast', None)
    block = request.FILES.get('block', None)
    ks = request.FILES.get('ks', None)
    shu_len = request.FILES.get('shu_len', None)
    shu_gff = request.FILES.get('shu_gff', None)
    heng_len = request.FILES.get('heng_len', None)
    heng_gff = request.FILES.get('heng_gff', None)

    if blast is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None or block is None or ks is None:
        return render(request, '../tools/templates/zu_ks_dotplot.html')
    c = name_set()

    shu_len_name = shu_len.name.split(".")[0]
    heng_len_name = heng_len.name.split(".")[0]

    keep_file(na=blast, c=c)
    keep_file(na=block, c=c)
    keep_file(na=ks, c=c)
    keep_file(na=heng_len, c=c)
    keep_file(na=shu_len, c=c)
    keep_file(na=heng_gff, c=c)
    keep_file(na=shu_gff, c=c)

    zu_ks_dotplot_run_tools(place=c, shu_len_name=shu_len_name, heng_len_name=heng_len_name)
    files = f"*.png"
    return zip_file(request, c, files)


# wgdi blast_dotplot
@xframe_options_sameorigin
def wgdi_dotplot_run(request):
    # 五个文件
    blast = request.FILES.get('blast', None)
    heng_len = request.FILES.get('heng_len', None)
    shu_len = request.FILES.get('shu_len', None)
    heng_gff = request.FILES.get('heng_gff', None)
    shu_gff = request.FILES.get('shu_gff', None)
    # 四种参数-值
    evalue = str(request.POST.get('evalue', None))
    score = request.POST.get('score', None)
    # 需要保存的物种名称
    heng_species = str(request.POST.get('heng_species', None))
    shu_species = str(request.POST.get('shu_species', None))
    patten = request.POST.get('patten', None)

    if blast is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None:
        return render(request, 'wgdi_dotplot.html')
    c = name_set()
    blast.name = 'diamond.fasta'
    heng_gff.name = '11.gff'
    shu_gff.name = '22.gff'
    heng_len.name = '11.len'
    shu_len.name = '22.len'
    keep_file(na=blast, c=c)
    keep_file(na=heng_gff, c=c)
    keep_file(na=shu_gff, c=c)
    keep_file(na=heng_len, c=c)
    keep_file(na=shu_len, c=c)
    try:
        normalize_wgdi_lens_file(c, '11.len', '11.gff')
        normalize_wgdi_lens_file(c, '22.len', '22.gff')
        normalize_wgdi_gff_file(c, '11.gff')
        normalize_wgdi_gff_file(c, '22.gff')
        wgdi_dotplot_run_tools(place=c, evalue=evalue, score=score, heng_species=heng_species, shu_species=shu_species, patten=patten)
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdi_dotplot_download')
    files = f"result.{patten}"
    try:
        build_wgdi_result_zip(c, files)
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdi_dotplot_download')
    return wgdi_download_ready_response('wgdi_dotplot', c, 'wgdi_dotplot_download')


# wgdi 绘制kaks点图
@xframe_options_sameorigin
def wgdikaks_dot_run(request):
    # 三个文件
    blockinfo = request.FILES.get('blockinfo', None)
    heng_len = request.FILES.get('heng_len', None)
    shu_len = request.FILES.get('shu_len', None)
    # 需要保存的物种名称
    heng_species = str(request.POST.get('heng_species', None))
    shu_species = str(request.POST.get('shu_species', None))
    if blockinfo is None or heng_len is None or shu_len is None:
        return render(request, 'wgdikaks_dot.html')
    c = name_set()
    blockinfo.name = 'blockinfo.csv'
    heng_len.name = '11.len'
    shu_len.name = '22.len'
    keep_file(na=blockinfo, c=c)
    keep_file(na=heng_len, c=c)
    keep_file(na=shu_len, c=c)
    try:
        wgdikaks_dot_run_tools(place=c, heng_species=heng_species, shu_species=shu_species)
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdikaks_dot_download')
    files = f"ks.dotplot.pdf"
    try:
        build_wgdi_result_zip(c, files)
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdikaks_dot_download')
    return wgdi_download_ready_response('wgdikaks_dot', c, 'wgdikaks_dot_download')


# zu_correspondence_mc_run
def zu_correspondence_mc_run(request):
    blast = request.FILES.get('blast', None)
    block = request.FILES.get('block', None)
    correspondence = request.FILES.get('correspondence', None)
    shu_len = request.FILES.get('shu_len', None)
    shu_gff = request.FILES.get('shu_gff', None)
    heng_len = request.FILES.get('heng_len', None)
    heng_gff = request.FILES.get('heng_gff', None)

    if blast is None or block is None or correspondence is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None:
        return render(request, '../templates/zu_correspondence_mc.html')
    c = name_set()

    keep_file(na=blast, c=c)
    keep_file(na=block, c=c)
    keep_file(na=correspondence, c=c)
    keep_file(na=heng_len, c=c)
    keep_file(na=heng_gff, c=c)
    keep_file(na=shu_len, c=c)
    keep_file(na=shu_gff, c=c)

    shu_name = shu_len.name.split('.')[0]
    heng_name = heng_len.name.split('.')[0]
    zu_correspondence_mc_run_tools(place=c, shu_name=shu_name, heng_name=heng_name)
    files = f"*new.blast *.mc.*.txt *_corr.png *.corr.txt"
    return zip_file(request, c, files)


def zu_retention_run(request):
    mc_files = request.FILES.getlist("mc_files", None)
    if mc_files is None:
        return render(request, '../templates/zu_retention.html')
    c = name_set()
    keep_files(na=mc_files, c=c)
    zu_retention_run_tools(place=c)
    files = f"output"
    return zip_file(request, c, files)


def zu_loss_run(request):
    mc_files = request.FILES.getlist("mc_files", None)
    if mc_files is None:
        return render(request, '../templates/zu_loss.html')
    c = name_set()
    keep_files(na=mc_files, c=c)
    zu_loss_run_tools(place=c)
    files = f"output"
    return zip_file(request, c, files)


def zu_pindex_run(request):
    mc_files = request.FILES.getlist("mc_files", None)
    sliding_window = request.POST.get('sliding_window')
    buchang = request.POST.get('buchang')
    sigema_start = request.POST.get('sigema_start')
    sigema_end = request.POST.get('sigema_end')
    if mc_files is None:
        return render(request, '../templates/zu_pindex.html')
    c = name_set()
    keep_files(na=mc_files, c=c)

    zu_pindex_run_tools(place=c, sliding_window=sliding_window, buchang=buchang, sigema_start=sigema_start, sigema_end=sigema_end)
    files = f"output pindex_result.txt"
    return zip_file(request, c, files)


# wgdi 计算 blockinfo_run
@xframe_options_sameorigin
def wgdi_blockinfo_run(request):
    # 7个文件
    blast = request.FILES.get('blast', None)
    block_file = request.FILES.get('block_file', None)
    ks_file = request.FILES.get('ks_file', None)
    heng_len = request.FILES.get('heng_len', None)
    shu_len = request.FILES.get('shu_len', None)
    heng_gff = request.FILES.get('heng_gff', None)
    shu_gff = request.FILES.get('shu_gff', None)
    # 3种参数-值
    evalue = str(request.POST.get('evalue', None))
    score = request.POST.get('score', None)
    repeat_number = request.POST.get('repeat_number', None)
    # 需要保存的物种名称
    heng_species = str(request.POST.get('heng_species', None))
    shu_species = str(request.POST.get('shu_species', None))
    if blast is None or block_file is None or ks_file is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None:
        return render(request, 'wgdi_blockinfo.html')

    c = name_set()
    blast.name = 'blast.txt'
    block_file.name = 'block.txt'
    ks_file.name = 'ks.txt'
    heng_gff.name = '11.gff'
    shu_gff.name = '22.gff'
    heng_len.name = '11.len'
    shu_len.name = '22.len'

    keep_file(na=blast, c=c)
    keep_file(na=block_file, c=c)
    keep_file(na=ks_file, c=c)
    keep_file(na=heng_gff, c=c)
    keep_file(na=shu_gff, c=c)
    keep_file(na=heng_len, c=c)
    keep_file(na=shu_len, c=c)
    try:
        normalize_wgdi_lens_file(c, '11.len', '11.gff')
        normalize_wgdi_lens_file(c, '22.len', '22.gff')
        normalize_wgdi_gff_file(c, '11.gff')
        normalize_wgdi_gff_file(c, '22.gff')
        validate_wgdi_ks_file(c, 'ks.txt')
        wgdi_blockinfo_run_tools(
            place=c,
            evalue=evalue,
            score=score,
            repeat_number=repeat_number,
            heng_species=heng_species,
            shu_species=shu_species,
        )
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdi_blockinfo_download')
    files = f'{heng_species}_{shu_species}_block_information.csv'
    try:
        build_wgdi_result_zip(c, files)
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdi_blockinfo_download')

    download_url = reverse('wgdi_blockinfo_download_url', args=[c])
    response = HttpResponse(
        "<html><head><script>"
        f"window.top.location.href = {json.dumps(download_url)};"
        "</script></head><body></body></html>",
        content_type='text/html; charset=utf-8',
    )
    response.set_cookie('wgdi_blockinfo_download', 'done', max_age=60, path='/')
    return response


# wgdi_correspondence_run
@xframe_options_sameorigin
def wgdi_correspondence_run(request):
    # 3个文件
    block_information = request.FILES.get('block_information', None)
    heng_len = request.FILES.get('heng_len', None)
    shu_len = request.FILES.get('shu_len', None)
    # 3种参数-值
    tandem_length = request.POST.get('tandem_length', None)
    pvalue = str(request.POST.get('pvalue', None))
    block_length = request.POST.get('block_length', None)

    if block_information is None or heng_len is None or shu_len is None:
        return render(request, 'wgdi_correspondence.html')
    c = name_set()
    block_information.name = 'block_information.csv'
    heng_len.name = '11.len'
    shu_len.name = '22.len'

    keep_file(na=block_information, c=c)
    keep_file(na=heng_len, c=c)
    keep_file(na=shu_len, c=c)
    try:
        start_wgdi_correspondence_background_job(
            place=c,
            tandem_length=tandem_length,
            pvalue=pvalue,
            block_length=block_length,
        )
    except RuntimeError as exc:
        return wgdi_runtime_error_response(exc, 'wgdi_correspondence_download')
    except Exception as exc:
        return wgdi_runtime_error_response(exc, 'wgdi_correspondence_download')

    return wgdi_correspondence_job_started_response(c)


# codonw
def codonw_run(request):
    file = request.FILES.get("file", None)
    if file is None:
        return render(request, '../templates/codonw.html')
    c = name_set()
    file_name = file.name.split(".")[0]
    file.name = '1.fasta'
    keep_file(na=file, c=c)

    codonw_run_tools(place=c, file_name=file_name)
    files = f'{file_name}.out {file_name}.blk'
    return zip_file(request, c, files)


# cpgfinder
def cpgfinder_run(request):
    myFile1 = request.FILES.get("file1", None)
    island = request.POST.get('island', None)
    cg_percent = request.POST.get('cg_percent', None)
    gc_ratio = request.POST.get('gc_ratio', None)
    if myFile1 is None:
        return render(request, '../templates/cpgfinder.html')

    c = name_set()
    myFile_name = myFile1.name
    keep_file(na=myFile1, c=c)
    cpgfinder_run_tools(place=c, island=island, cg_percent=cg_percent, gc_ratio=gc_ratio, myFile_name=myFile_name)

    files = 'cpgfinder_result.txt'
    return zip_file(request, c, files)


# MEME
def meme_suit_run(request):
    myFile1 = request.FILES.get("file1", None)
    patten = request.POST.get('patten', None)
    motif = request.POST.get('motif', None)
    motif_num = request.POST.get('motif_num', None)
    minw = request.POST.get('minw', None)
    maxw = request.POST.get('maxw', None)
    if myFile1 is None:
        return render(request, '../templates/meme_suit.html')
    c = name_set()
    myFile1.name = '1.fasta'
    keep_file(na=myFile1, c=c)
    meme_run_tools(place=c, patten=patten, motif=motif, motif_num=motif_num, minw=minw, maxw=maxw)
    files = 'logo*.png meme.*'
    return zip_file(request, c, files)


# hmmer
def hmmer_run(request):
    hmm_model = request.FILES.get("hmm_model", None)
    hmm_fa = request.FILES.get('hmm_fa', None)
    e_value = request.POST.get('e_value', None)

    if hmm_fa is None or hmm_model is None:
        return render(request, '../templates/hmmer.html')
    c = name_set()

    hmm_model.name = "hmm_model.fasta"
    hmm_fa.name = "hmm_fa.fasta"
    keep_file(na=hmm_model, c=c)
    keep_file(na=hmm_fa, c=c)

    hmmer_run_tools(place=c, e_value=e_value)
    files = 'result.out'
    return zip_file(request, c, files)


# pfam
def pfam_run(request):
    myFile1 = request.FILES.get("file1", None)
    structure = request.POST.get('structure', None)
    if myFile1 is None:
        return render(request, '../templates/pfam.html')
    c = name_set()
    myFile1.name = "1.fasta"
    keep_file(na=myFile1, c=c)

    pfam_run_tools(place=c, structure=structure)
    files = 'pfam.txt pfam_new.txt'
    return zip_file(request, c, files)


# sequence_alignment
def sequence_alignment_run(request):
    myFile1 = request.FILES.get("file1", None)
    patten = request.POST.get('patten', None)
    # email = request.POST.get('email', None)

    if myFile1 is None:
        return render(request, '../templates/sequence_alignment.html')
    c = name_set()
    myFile1.name = "1.fasta"
    keep_file(na=myFile1, c=c)

    sequence_aligment_run_tools(place=c, patten=patten)
    if patten == "mafft":
        files = f'{path_get}/file_keep/{c}/mafft.fasta'
    else:
        files = f'{path_get}/file_keep/{c}/1.aln'
    return zip_file(request, c, files)


# fasttree
def fasttree_run(request):
    patten = request.POST.get('patten', None)
    myFile1 = request.FILES.get("file1", None)
    if myFile1 is None:
        return render(request, '../templates/fasttree.html')
    c = name_set()
    myFile1.name = "1.phy"
    keep_file(na=myFile1, c=c)
    fasttree_run_tools(place=c, patten=patten)
    files = f'1.nwk'
    return zip_file(request, c, files)


# iqtree
@guarded_tool_view
def iq_tree_run(request):
    file = request.FILES.get("file", None)
    patten = request.POST.get('patten', None)
    bs_num = request.POST.get('bs_num', None)
    if file is None:
        return render(request, '../templates/iq_tree.html')
    patten, bs_num = iq_model(patten), bootstrap(bs_num)
    c = name_set()
    file.name = 'result.phy'
    keep_file(na=file, c=c)
    iqtree_run_tools(place=c, patten=patten, bs_num=bs_num)
    files = f'result.phy.treefile'
    return zip_file(request, c, files)


# sequence_screening
def sequence_screening_run(request):
    protein = request.FILES.get("protein", None)
    gene = request.FILES.get('gene', None)
    gff = request.FILES.get('gff', None)
    id = request.FILES.get('id', None)
    if protein is None or gene is None or gff is None or id is None:
        return render(request, 'sequence_screening.html')
    c = name_set()
    protein.name = 'protein.fasta'
    gene.name = 'gene.fasta'
    gff.name = 'gff.fasta'
    id.name = 'id.fasta'
    keep_file(na=protein, c=c)
    keep_file(na=gene, c=c)
    keep_file(na=gff, c=c)
    keep_file(na=id, c=c)
    sequence_run(place=c)
    files = 'new_pro.txt new_cds.txt new_gff.txt'
    return zip_file(request, c, files)


# formatTofasta_run
def formatTofasta_run(request):
    format = request.FILES.get("file1", None)
    patten = request.POST.get("patten", None)
    patten_end = request.POST.get("patten_end", None)

    if format is None:
        return render(request, '../templates/formatTofasta.html')
    c = name_set()
    file_name = format.name.split(".")[0]
    file_last = format.name.split(".")[1]
    keep_file(na=format, c=c)

    format_fasta_run(place=c, file_name=file_name, patten=patten, patten_end=patten_end, file_last=file_last)
    files = f'{file_name}.{patten_end}'
    return zip_file(request, c, files)


# find_replace
@guarded_tool_view
def find_replace_run(request):
    file_up = request.FILES.get("file", None)
    old_name = request.POST.get("old_name", None)
    new_name = request.POST.get("new_name", None)
    if file_up is None:
        return render(request, '../templates/find_replace.html')
    c = name_set()
    file_up.name = "upload.txt"
    keep_file(na=file_up, c=c)
    find_replace_run_tools(place=c, old_name=old_name, new_name=new_name)
    files = f'result.txt'
    return zip_file(request, c, files)


# duplicate_removal_run
def duplicate_removal_run(request):
    file = request.FILES.get("file", None)
    if file is None:
        return render(request, '../templates/quchong.html')
    c = name_set()
    file.name = '1.fasta'
    keep_file(na=file, c=c)
    quchong_run(place=c)
    files = f'new.fasta'
    return zip_file(request, c, files)

# Extract_column
@guarded_tool_view
def extract_column_run(request):
    row = request.FILES.get("row", None)
    row_num = request.POST.get("row_num", None)
    if row is None:
        return render(request, '../templates/extract_row.html')
    c = name_set()
    row_num = columns(row_num)
    row_name, row_last = 'input', 'tsv'
    row.name = 'input.tsv'
    keep_file(na=row, c=c)
    extr_row_run(place=c,  row_num=row_num, row_name=row_name, row_last=row_last)
    files = f'{row_name}.new.{row_last}'
    return zip_file(request, c, files)


# file_merge
def file_merge_run(request):
    file = request.FILES.getlist("file", None)
    if file is None:
        return render(request, '../templates/file_merge.html')
    c = name_set()
    keep_files(na=file, c=c)
    file_merge_run_tools(place=c)
    files = f'result.txt'
    return zip_file(request, c, files)


# interproscan—— run
def interproscan_run(request):
    myFile1 = request.FILES.get('file1', None)
    # e_value = str(request.POST.get('e_value', None))
    if myFile1 is None:
        return render(request, 'interproscan.html')
    # 限制大小为1Mb
    if myFile1.size > 1024 * 1024:
        return render(request, 'interproscan.html', {'error': 'File size exceeds the limit (1MB).'})
    c = name_set()
    myFile1.name = 'result.fasta'
    keep_file(na=myFile1, c=c)
    interproscan_run_tools(place=c)
    files = f"result.tsv"
    return zip_file(request, c, files)


# 删除点和星星
def deal_star_run(request):
    file = request.FILES.getlist("file", None)
    if file is None:
        return render(request, '../templates/deal_star.html')
    c = name_set()
    keep_files(na=file, c=c)
    deal_star_run_tools(place=c)
    files = f'output_pep/*'
    return zip_file(request, c, files)


# subtree_extractor_run
def subtree_extractor_run(request):
    myFile1 = request.FILES.get('file1', None)
    myFile2 = request.FILES.get('file2', None)
    if myFile1 is None or myFile2 is None:
        return render(request, 'subtree_extractor.html')
    c = name_set()
    myFile1.name = 'ty.newick'
    myFile2.name = 'species.txt'
    keep_file(na=myFile1, c=c)
    keep_file(na=myFile2, c=c)
    subtree_extractor_run_tools(place=c)
    files = f"result_subtree.newick"
    return zip_file(request, c, files)


# iTAK_run
def iTAK_run(request):
    file = request.FILES.getlist("file", None)
    if file is None:
        return render(request, '../templates/iTAK.html')
    c = name_set()
    keep_files(na=file, c=c)
    iTAK_run_tools(place=c)
    files = f'output/*'
    return zip_file(request, c, files)


# block_number_count_run
def block_number_count_run(request):
    file = request.FILES.getlist("file")
    if file is None:
        return render(request, '../templates/block_number_count.html')
    c = name_set()
    keep_files(na=file, c=c)
    block_number_count_run_tools(place=c)
    files = f'block.all.count.txt'
    return zip_file(request, c, files)


# collinearity_generator_run
def collinearity_generator_run(request):
    patten = request.POST.get('patten', None)
    reference_file = request.POST.get('reference_file', None)
    species_name = request.POST.get('species_name', None)
    file = request.FILES.getlist("file", None)
    if file is None:
        return render(request, '../templates/collinearity_generator.html')
    c = name_set()
    keep_files(na=file, c=c)
    collinearity_generator_run_tools(place=c, patten=patten, reference_file=reference_file, species_name=species_name)
    files = f'output.txt'
    return zip_file(request, c, files)


# draw_list_tree_run
def draw_list_tree_run(request):
    patten = request.POST.get('patten', None)
    file1 = request.FILES.getlist("file1", None)
    file2 = request.FILES.get("file2", None)
    if file1 is None or file2 is None:
        return render(request, '../templates/draw_list_tree.html')
    c = name_set()
    file2.name = "list.txt"
    keep_files(na=file1, c=c)
    keep_file(na=file2, c=c)
    draw_list_tree_run_tools(place=c, patten=patten)
    files = f'list_tree_BS_50_root_png.zip list_tree_BS_50_root_file.zip'
    return zip_file(request, c, files)


# species_classification_run
def species_classification_run(request):
    file1 = request.FILES.get("file1", None)
    if file1 is None:
        return render(request, '../templates/draw_list_tree.html')
    c = name_set()
    file1.name = "sp_list.txt"
    keep_file(na=file1, c=c)
    species_classification_run_tools(place=c)
    files = f'list_tree_BS_50_root_png.zip list_tree_BS_50_root_file.zip'
    return zip_file(request, c, files)


# GF_ks_circos_run
def GF_ks_circos_run(request):
    from tools.offline_views.GF_Circos import views as gf_circos_views
    return gf_circos_views.GF_ks_circos_run(request)


# 物种介绍搜索，用到了数据库
# def search_fabaceae_taxa(request):
#     species_name = request.POST.get("species_name", None)
#     print(species_name)
#
#     if request.method == 'POST':
#         form = FabaceaeTaxaForm(request.POST)
#         if form.is_valid():
#             species_name = form.cleaned_data['scientfiic_name']
#             with connection.cursor() as cursor:
#                 cursor.execute("SELECT * FROM Fabaceae_taxa WHERE scientfiic_name = %s", [species_name])
#                 species = cursor.fetchone()
#
#             return render(request, 'genome_introduction_result.html', {'species': species, 'form': form})
#     else:
#         form = FabaceaeTaxaForm()
#     return render(request, 'genome_introduction.html', {'form': form})



# from .forms import FabaceaeTaxaForm
# # 物种介绍搜索的第二个版本
# def search_fabaceae_taxa(request):
#     species_name = request.POST.get("species_name", None)
#     species_name_2 = request.POST.get("species_name_2", None)
#     # species_name_2 = request.GET.get('species_name', None)
#     # print(species_name, species_name_2)
#
#     if species_name or species_name_2:
#         species_name = species_name if species_name else species_name_2
#         form = FabaceaeTaxaForm(request.POST)
#         form.data = form.data.copy()
#         form.data['scientfiic_name'] = species_name
#         if form.is_valid():
#             species_name = form.cleaned_data['scientfiic_name']
#             # print(species_name)
#             with connection.cursor() as cursor:
#                 query = "SELECT * FROM Fabaceae_taxa WHERE scientfiic_name LIKE %s"
#                 cursor.execute(query, ['%' + species_name + '%'])
#                 species = cursor.fetchall()
#                 # print(species)
#             # return render(request, 'genome_introduction_result.html', {'species': species, 'form': form})
#             return render(request, 'genome_introduction.html', {'species': species, 'form': form})
#
#     else:
#         # form = FabaceaeTaxaForm()
#
#         form = FabaceaeTaxaForm()
#         species_dict = defaultdict(list)
#         species_count = {}  # 新增字典用于存储每个字母的物种个数
#
#         with connection.cursor() as cursor:
#             cursor.execute("SELECT scientfiic_name FROM Fabaceae_taxa")
#             all_species = cursor.fetchall()
#             for (scientific_name,) in all_species:
#                 first_letter = scientific_name[0].upper()
#                 if first_letter.isalpha():  # 检查首字母是否为字母
#                     species_dict[first_letter].append(scientific_name)
#                     # 更新物种个数字典
#                     species_count[first_letter] = species_count.get(first_letter, 0) + 1
#
#         species_dict = dict(species_dict)
#         # print(species_dict)
#         return render(request, 'genome_introduction.html', {'form': form, 'species_dict': species_dict, 'species_count': species_count})
#     # return render(request, 'genome_introduction.html', {'form': form})


# # 物种介绍搜索的第三个版本
def search_fabaceae_taxa(request):
    return encyclopedia(request)



def get_tribes(request):
    return JsonResponse({'error': 'Legacy taxonomy data are unavailable; use the Asteraceae encyclopedia.', 'url': '/tools/encyclopedia'}, status=410)



def get_genera(request):
    return JsonResponse({'error': 'Legacy taxonomy data are unavailable; use the Asteraceae encyclopedia.', 'url': '/tools/encyclopedia'}, status=410)



# def load_genera(request):
#     # 获取前端传递的属（Genus）
#     selected_genus = request.GET.get('genus')
#     if selected_genus:
#         with connection.cursor() as cursor:
#             query = "SELECT * FROM Fabaceae_taxa WHERE genus = %s"
#             cursor.execute(query, [selected_genus])
#             results = cursor.fetchall()
#             columns = [col[0] for col in cursor.description]
#             result_list = [dict(zip(columns, row)) for row in results]
#         return JsonResponse({'results': result_list})
#     return JsonResponse({'results': []})

# def load_genera(request):
#     selected_genus = request.GET.get('genus')
#     if selected_genus:
#         with connection.cursor() as cursor:
#             query = "SELECT * FROM Fabaceae_taxa WHERE genus = %s"
#             cursor.execute(query, [selected_genus])
#             results = cursor.fetchall()
#         for spec in results:
#             print(spec)
#         return render(request, 'genome_introduction_v1.html', {'result_list': results})

    # return render(request, 'genome_introduction.html', {'species': []})
from django.http import JsonResponse


def load_genera(request):
    return JsonResponse({'error': 'Legacy taxonomy data are unavailable; use the Asteraceae encyclopedia.', 'url': '/tools/encyclopedia'}, status=410)




# def load_species_by_letter(request):
#     letter = request.GET.get('letter', '')
#     print(f"Received request for letter: {letter}")  # 打印收到的字母
#     species_list = []
#
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT scientfiic_name FROM Fabaceae_taxa WHERE scientfiic_name LIKE %s", [letter + '%'])
#         species_list = [row[0] for row in cursor.fetchall()]
#
#     print(species_list)  # 打印返回的物种列表
#     return JsonResponse({'species_list': species_list})





# GC 含量统计
def GC_calculation_run(request):
    file = request.FILES.get("file", None)
    if file is None:
        return render(request, '../templates/GC_calculation.html')
    c = name_set()
    file.name = "nucl.fa"
    keep_file(na=file, c=c)
    result_content = []
    for record in SeqIO.parse(f"{path_get}/file_keep/{c}/nucl.fa", "fasta"):
        gene_id, sequence = record.id, str(record.seq)
        length, gc_count = len(sequence), sequence.count("G") + sequence.count("C")
        a_count, g_count, c_count, t_count = map(sequence.count, ["A", "G", "C", "T"])
        a_percentage, g_percentage, c_percentage, t_percentage = map(lambda x: (x / length) * 100, [a_count, g_count, c_count, t_count])
        gc_percentage = (gc_count / length) * 100
        result_content.append([gene_id, length, gc_count, f"{gc_percentage:.2f}", a_count, f"{a_percentage:.2f}", g_count, f"{g_percentage:.2f}", c_count, f"{c_percentage:.2f}", t_count, f"{t_percentage:.2f}"])
    return render(request, '../templates/GC_calculation.html', {'result_content': result_content})


# 统计基因的长度，或者是染色体的长度
def chromosome_length_run(request):
    file = request.FILES.get("file", None)
    if file is None:
        return render(request, '../templates/chromosome_length.html')
    c = name_set()
    file.name = "nucl.fa"
    keep_file(na=file, c=c)
    result_content = [[record.id, len(str(record.seq))] for record in SeqIO.parse(f"{path_get}/file_keep/{c}/nucl.fa", "fasta")]
    return render(request, '../templates/chromosome_length.html', {'result_content': result_content})


# geme_cds_exon_counter_run
def geme_cds_exon_counter_run(request):
    file = request.FILES.getlist("file", None)
    if file is None:
        return render(request, '../templates/geme_cds_exon_counter.html')
    c = name_set()
    keep_files(na=file, c=c)
    files = glob.glob(f"{path_get}/file_keep/{c}/orthomcl/*.gff*")
    result_content = [(os.path.basename(fn_gff), *get_counts(fn_gff)) for fn_gff in files]
    return render(request, '../templates/geme_cds_exon_counter.html', {'result_content': result_content})


# 计算基因组的挂载率
def GenomeMountRateCalculator_run(request):
    file = request.FILES.get("file", None)
    chromosomes_num = request.POST.get('chromosomes_num')
    excluded_num = request.POST.get('excluded_num')
    if file is None:
        return render(request, '../templates/GenomeMountRateCalculator.html')
    if file.size > 100 * 1024 * 1024:  # 100MB限制
        return HttpResponse("File size exceeds the limit (100MB).")
    c = name_set()
    file_name = file.name
    keep_file(na=file, c=c)

    # 这段代码是计算基因组的挂载率。要输出的是物种的文件名字和挂载率百分比。
    sequences = SeqIO.parse(f"{path_get}/file_keep/{c}/{file_name}", "fasta")
    gene_lengths = {}
    for record in sequences:
        gene_id = record.id
        gene_length = len(record.seq)
        if int(gene_length) > int(excluded_num):
            gene_lengths[gene_id] = gene_length
    sorted_genes = sorted(gene_lengths.items(), key=lambda x: x[1], reverse=True)
    top_genes = sorted_genes[:int(chromosomes_num)]
    total_top_length = sum([length for _, length in top_genes])
    total_genome_length = sum(gene_lengths.values())
    ratio = total_top_length / total_genome_length

    result_content = [[file_name, ratio]]
    return render(request, '../templates/GenomeMountRateCalculator.html', {'result_content': result_content})


# 绘制热图的模块
def draw_heatmap_run(request):
    file = request.FILES.get("file", None)
    log2 = True if request.POST.get('log2') == 'on' else False
    column = True if request.POST.get('column') == 'on' else False
    row = True if request.POST.get('row') == 'on' else False
    color1 = request.POST.get('color1')
    color2 = request.POST.get('color2')
    color3 = request.POST.get('color3')
    width = int(request.POST.get('width'))
    height = int(request.POST.get('height'))

    if file is None or color1 is None or color2 is None or color3 is None or width is None or height is None:
        return render(request, '../templates/draw_heatmap.html')
    c = name_set()
    file_name = file.name
    keep_file(na=file, c=c)

    data = pd.read_csv(f"{path_get}/file_keep/{c}/{file_name}", sep='\t', index_col=0)
    data = data.replace("Na", np.nan)
    data = data.astype(float)
    data = data.dropna(axis=0)
    if log2:
        data = data + 1
        data = np.log2(data)

    cmap = sns.blend_palette([color1, color2, color3], as_cmap=True)  # 渐变颜色
    clustermap = sns.clustermap(data, cmap=cmap, linewidths=0.5, linecolor='gray',
                                cbar_kws={'label': 'Expression'}, method='average', metric='euclidean',
                                col_cluster=column, row_cluster=row, figsize=(width, height))
    clustermap.fig.set_dpi(300)

    plt.title(file_name.split(".")[0])
    plt.xlabel('Samples')
    plt.ylabel('Genes')
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_file = os.path.join(f"{path_get}/file_keep/{c}/", os.path.splitext(os.path.basename(file_name))[0] + '_heatmap.png')
    plt.savefig(output_file)

    with open(output_file, 'rb') as f:
        png_content = base64.b64encode(f.read()).decode('utf-8')
    return render(request, '../templates/draw_heatmap.html', {'png_content': png_content})


# 绘制棒棒糖图
def lollipop_chart_run(request):
    file = request.FILES.get("file", None)
    color = request.POST.get('color')
    y_axis_min = int(request.POST.get('y_axis_min'))
    y_axis_max = int(request.POST.get('y_axis_max'))
    width = int(request.POST.get('width'))
    height = int(request.POST.get('height'))
    extracted_colors = []
    extracted_colors.extend(color.split(','))

    if file is None or color is None or y_axis_min is None or y_axis_max is None or width is None or height is None:
        return render(request, '../templates/lollipop_chart.html')
    c = name_set()
    file_name = file.name
    keep_file(na=file, c=c)

    with open(f"{path_get}/file_keep/{c}/{file_name}", 'r') as file:
        header = file.readline().strip().split('\t')
        car_name_label = header[0]
        mpg_label = header[1]
        group_label = header[2]

    df = pd.read_csv(f"{path_get}/file_keep/{c}/{file_name}", sep='\t')
    grouped = df.groupby(group_label)
    df = pd.read_csv(f"{path_get}/file_keep/{c}/{file_name}", sep='\t')
    grouped = df.groupby(group_label)
    # fig, ax = plt.subplots()
    fig, ax = plt.subplots(figsize=(width, height))
    for i, (name, group) in enumerate(grouped):
        for x, y in zip(group[car_name_label], group[mpg_label]):
            ax.plot([x, x], [y, 0], color='black', linestyle='-', linewidth=1.5, zorder=1)
            ax.annotate(f'{y}', (x, y), textcoords="offset points", xytext=(0, -2), ha='center', zorder=3, fontsize=8)
        ax.scatter(group[car_name_label], group[mpg_label], marker='o', s=250, label=f'Group {name}', color=extracted_colors[i], zorder=2)
    y_range = (y_axis_min, y_axis_max)
    ax.set_ylim(*y_range)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.axhline(y=y_axis_min, color='gray', linestyle='--', linewidth=1)  # 改 - 灰色线的位置
    ax.axhline(y=y_axis_max, color='gray', linestyle='--', linewidth=1)  # 改 - 灰色线的位置
    plt.xticks(rotation=45, ha="right")
    plt.subplots_adjust(right=0.8)  # 调整子图布局，将标签和标题移到图片框的右侧以外

    ax.set_xlabel(car_name_label)
    ax.set_ylabel(mpg_label)
    ax.set_title(f'{mpg_label} by {car_name_label} and {group_label}')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    plt.savefig(f"{path_get}/file_keep/{c}/plot.png", dpi=300)

    with open(f"{path_get}/file_keep/{c}/plot.png", 'rb') as f:
        png_content = base64.b64encode(f.read()).decode('utf-8')
    return render(request, '../templates/lollipop_chart.html', {'png_content': png_content})


# 绘制基因结构的基因结构图
class GeneStructurePlotter:
    def __init__(self, gff_file_path, chromosome_to_extract, start_position, end_position,
                 colors_file_path, image_size=(800, 200), gene_height=0.6):
        self.gff_file_path = gff_file_path
        self.chromosome_to_extract = chromosome_to_extract
        self.start_position = int(start_position)
        self.end_position = int(end_position)
        self.colors_file_path = colors_file_path
        self.image_size = image_size
        self.gene_height = gene_height

    def extract_gff_by_coordinates(self):
        gene_dict = {}
        with open(self.gff_file_path, 'r') as gff_file:
            for line in gff_file:
                fields = line.strip().split('\t')
                current_chromosome, current_start, current_end = fields[0], int(fields[1]), int(fields[2])
                if current_chromosome == self.chromosome_to_extract and \
                   self.start_position <= current_end and self.end_position >= current_start:
                    gene_dict[fields[5]] = line.strip()
        return gene_dict

    def read_gene_colors(self):
        gene_colors = {}
        with open(self.colors_file_path, 'r') as file:
            gene_colors = dict(line.strip().split('\t')[:2] for line in file)
        return gene_colors

    # def draw_gene_structure(self):
    def draw_gene_structure(self, output_image_path):
        gene_dict = self.extract_gff_by_coordinates()
        gene_colors_dict = self.read_gene_colors()

        sns.set(style="whitegrid")
        fig, ax = plt.subplots(figsize=(self.image_size[0] / 100, self.image_size[1] / 100), dpi=300)
        font_prop = FontProperties(fname="C:\\Windows\\Fonts\\arial.ttf", size=10)

        y = 0
        for gene_id, gff_line in gene_dict.items():
            fields = gff_line.split('\t')
            start = int(fields[1])
            end = int(fields[2])
            gene_length = end - start
            strand = fields[3]
            edgecolor = 'yellow' if strand == '+' else 'blue'
            col = gene_colors_dict.get(fields[5], "gray")

            rect = Rectangle((start, y), gene_length, self.gene_height, facecolor=col, edgecolor=edgecolor, linewidth=0.3, zorder=1)
            ax.add_patch(rect)
            ax.text(start, y + self.gene_height + 0.7, gene_id, ha='left', va='center', color='black',
                    fontproperties=font_prop, rotation=30, zorder=2)

        ax.hlines(y + self.gene_height/2, xmin=self.start_position, xmax=self.end_position, color='black', linestyle='-', linewidth=2, alpha=0.7, zorder=0)
        plt.xlim(self.start_position, self.end_position + 12000)
        plt.ylim(-0.5, 3)
        ax.set_yticks([])
        ax.axis('off')
        plt.savefig(output_image_path, format='png', dpi=300)
        # plt.savefig('gene_structure.png', format='png', dpi=300)


# 绘制基因结构图
def draw_gene_structure_run(request):
    gff_file = request.FILES.get("gff_file", None)
    highlight_file = request.FILES.get("highlight_file", None)
    chromosome_position = int(request.POST.get('chromosome_position'))
    start = int(request.POST.get('start'))
    termination = int(request.POST.get('termination'))

    if gff_file is None or highlight_file is None or chromosome_position is None or start is None or termination is None:
        return render(request, '../templates/draw_gene_structure.html')
    c = name_set()
    gff_file_name = gff_file.name
    keep_file(na=gff_file, c=c)
    highlight_file_name = highlight_file.name
    keep_file(na=highlight_file, c=c)

    plotter = GeneStructurePlotter(
        gff_file_path=f"{path_get}/file_keep/{c}/{gff_file_name}",
        chromosome_to_extract=f"{chromosome_position}",
        start_position=f"{start}",
        end_position=f"{termination}",
        colors_file_path=f"{path_get}/file_keep/{c}/{highlight_file_name}",
        image_size=(800, 200),
        gene_height=0.6
    )
    plotter.draw_gene_structure(output_image_path=f"{path_get}/file_keep/{c}/gene_structure.png")

    with open(f"{path_get}/file_keep/{c}/gene_structure.png", 'rb') as f:
        png_content = base64.b64encode(f.read()).decode('utf-8')
    return render(request, '../templates/draw_gene_structure.html', {'png_content': png_content})


# sequence_fetch_run 搜索数据库表中的序列信息，并可以输出到html中
def sequence_fetch_run(request):
    species_data = request.POST.get("species_data", None)
    geneid = request.POST.get('geneid', None)
    if species_data is None or geneid is None:
        return render(request, 'sequence_fetch.html')

    geneids = geneid.replace('\r', '').split('\n')
    geneid_placeholders = ','.join(['%s'] * len(geneids))
    sql_query = f"SELECT * FROM {species_data}_cds_pep WHERE gene_id IN ({geneid_placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(sql_query, geneids)
        result = cursor.fetchall()
    found_geneids = [row[1] for row in result]
    not_found_geneids = [geneid for geneid in geneids if geneid not in found_geneids]
    return render(request, '../templates/sequence_fetch_run.html', {'not_found_geneids': not_found_geneids, 'result': result})









































































# phyml
def phyml_run(request):
    myFile1 = request.FILES.get("file", None)
    patten = request.POST.get('patten', None)
    small = request.POST.get('small', None)
    model = request.POST.get('model', None)
    frequency = request.POST.get('frequency', None)
    nice = request.POST.get('nice', None)
    num = request.POST.get('num', None)
    if myFile1 is None:
        return render(request, '../templates/phyml.html')
    c = name_set()
    myFile1.name = "1.phy"
    keep_file(na=myFile1, c=c)

    phyml_run_tools(place=c, patten=patten, model=model, frequency=frequency, nice=nice, num=num, small=small)
    files = "1.phy_*"
    return zip_file(request, c, files)



# index_email
def index_email(request):
    name = request.POST.get("name", None)
    email = request.POST.get("email", None)
    message = request.POST.get("message", None)

    if email is None or name is None or message is None:
        return render(request, '../templates/contact.html')
    else:
        c = name_set()
        keep_email_index(place=c, name=name, email=email, message=message)
        return render(request, '../templates/successful.html')


# dotplot
def dotplot_run(request):
    # 五个文件
    blast = request.FILES.get('blast', None)
    heng_len = request.FILES.get('heng_len', None)
    shu_len = request.FILES.get('shu_len', None)
    heng_gff = request.FILES.get('heng_gff', None)
    shu_gff = request.FILES.get('shu_gff', None)

    # 四种参数-值
    evalue = str(request.POST.get('evalue', None))
    score = request.POST.get('score', None)
    hitnum = request.POST.get('hitnum', None)
    repnum = request.POST.get('repnum', None)

    # 需要保存的染色体数
    heng_chromosomes = str(request.POST.get('heng_chromosomes', None))
    shu_chromosomes = str(request.POST.get('shu_chromosomes', None))

    # 需要保存的物种名称
    heng_species = str(request.POST.get('heng_species', None))
    shu_species = str(request.POST.get('shu_species', None))

    email = request.POST.get('email', None)

    if blast is None or heng_len is None or shu_len is None or heng_gff is None or shu_gff is None:
        return render(request, '../templates/dotplot.html')
    else:
        c = name_set()
        keep_email(e=c, address=email)

        blast_name = blast.name
        shu_gff_name = shu_gff.name
        heng_gff_name = heng_gff.name
        shu_len_name = shu_len.name
        heng_len_name = heng_len.name

        keep_file(na=blast, c=c)
        keep_file(na=heng_len, c=c)
        keep_file(na=shu_len, c=c)
        keep_file(na=heng_gff, c=c)
        keep_file(na=shu_gff, c=c)

        dotplot_run_tools(place=c, email=email, evalue=evalue, score=score, hitnum=hitnum, repnum=repnum,
                          heng_chromosomes=heng_chromosomes, shu_chromosomes=shu_chromosomes,
                          heng_species=heng_species, shu_species=shu_species,
                          blast_name=blast_name,
                          shu_gff_name=shu_gff_name, heng_gff_name=heng_gff_name,
                          shu_len_name=shu_len_name, heng_len_name=heng_len_name
                          )
        return render(request, '../templates/successful.html')


# blast_match_run
# def blast_match_run(request):
#
#     patten = str(request.POST.get('patten', None))
#     myFile1 = request.FILES.get('file1', None)
#     species_name = str(request.POST.get("species_data", None))
#
#     e_value = str(request.POST.get('e_value', None))
#     sco = str(request.POST.get('score_1', None))
#     iden = str(request.POST.get('identity_1', None))
#
#     email = str(request.POST.get('email', None))
#     nucl_or_prot = "prot" if patten == 'blastp' else "nucl"
#
#     if myFile1 is None:
#         return render(request, 'blast_match.html')
#     else:
#         c = name_set()
#         keep_email(e=c, address=email)
#
#         myFile1.name = '1.fasta'
#         keep_file(na=myFile1, c=c)
#
#         blast_match_run_tools(place=c, patten=patten, species_data=species_name, e=e_value, email=email, score=sco, identity=iden, nucl_or_prot=nucl_or_prot)
#         return render(request, '../templates/successful.html')


# f_blast页面 辅助函数：执行系统命令
@csrf_exempt
@guarded_tool_view
def blast_run(request):
    """
    执行 BLAST 并在同一页面返回结果
    """
    if request.method == 'POST':
        try:
            # 1. 获取表单数据
            program = request.POST.get('patten')  # blastn 或 blastp
            program = choice(program, ('blastn', 'blastp'), 'alignment program')
            file1 = request.FILES.get('file1')  # Target Database
            file2 = request.FILES.get('file2')  # Query Sequence

            # 参数容错处理
            try:
                e_value_thresh = float(request.POST.get('e_value', 1e-5))
            except ValueError:
                e_value_thresh = 1e-5

            try:
                min_score = float(request.POST.get('score_1', 0))
            except ValueError:
                min_score = 0

            try:
                min_identity = float(request.POST.get('identity_1', 0))
            except ValueError:
                min_identity = 0

            if not file1 or not file2:
                return HttpResponse("Error: Both Target and Query files are required.", status=400)

            # 2. 使用 tempfile 创建临时目录 (自动处理路径，Windows/Linux 通用)
            with tempfile.TemporaryDirectory() as temp_dir:
                target_path = os.path.join(temp_dir, "target.fasta")
                query_path = os.path.join(temp_dir, "query.fasta")

                # 保存上传文件
                with open(target_path, 'wb+') as dest:
                    for chunk in file1.chunks(): dest.write(chunk)
                with open(query_path, 'wb+') as dest:
                    for chunk in file2.chunks(): dest.write(chunk)

                # 3. 建库 (makeblastdb)
                dbtype = 'prot' if program == 'blastp' else 'nucl'
                db_name = os.path.join(temp_dir, "target_db")

                cmd_makedb = ['makeblastdb', '-in', target_path, '-dbtype', dbtype, '-out', db_name]
                run_command(cmd_makedb)

                # 4. 运行 Blast
                # -task blastn 优化短序列，-dust no 关闭低复杂度过滤
                task_flag = "-task blastn -dust no" if program == 'blastn' else ""
                out_path = os.path.join(temp_dir, "blast_results.txt")

                # 输出格式 6 (Tabular)
                cmd_blast = [program] + (['-task', 'blastn', '-dust', 'no'] if program == 'blastn' else []) + ['-query', query_path, '-db', db_name, '-out', out_path, '-evalue', str(e_value_thresh), '-outfmt', '6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore', '-num_threads', '2']

                run_command(cmd_blast)

                # 5. 解析结果 & 读取原始内容
                results = []
                raw_output = ""  # 用于下载

                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    # A. 读取原始内容用于下载 (必须在 temp_dir 销毁前读取)
                    with open(out_path, 'r', encoding='utf-8') as f:
                        raw_output = f.read()

                    # B. 解析用于展示表格
                    col_names = ["qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
                                 "qstart", "qend", "sstart", "send", "evalue", "bitscore"]
                    df = pd.read_csv(out_path, sep='\t', names=col_names)

                    for _, row in df.iterrows():
                        if row['bitscore'] >= min_score and row['pident'] >= min_identity:
                            results.append({
                                'query': row['qseqid'],
                                'hit': row['sseqid'],
                                'evalue': "{:.2e}".format(row['evalue']),
                                'score': row['bitscore'],
                                'identity': f"{row['pident']:.2f}%"
                            })

                # 6. 返回同一页面，携带结果数据
                # raw_output 通过 json.dumps 处理可能包含的特殊字符（如果不使用 json.dumps，可以在模板中使用 escapejs）
                return render(request, 'f_blast.html', {
                    'results': results,
                    'raw_output': raw_output,
                    'has_result': True
                })

        except (ToolInputError, subprocess.TimeoutExpired):
            raise
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Calculation failed. Check the input format and parameters.'}, status=500)

    # GET 请求
    return render(request, 'f_blast.html')


def common_pests(request):
    return render(request, 'introduce/common_pests.html')


def diseases(request):
    return render(request, 'introduce/diseases.html')

def ecology(request):
    return render(request, 'introduce/ecology.html')

def agroecology(request):
    return render(request, 'agroecology.html')



def economic_value(request):
    return render(request, 'introduce/economic_value.html')


def method_planting(request):
    return render(request, 'introduce/method_planting.html')

#
# def Apr(request):
#     return render(request, 'introduce/Apr.html')
# def Aev(request):
#     return render(request, 'introduce/Aev.html')
# def Ana(request):
#     return render(request, 'introduce/Ana.html')
# def Mun(request):
#     return render(request, 'introduce/Mun.html')
# def Ame(request):
#     return render(request, 'introduce/Ame.html')
# def Aed(request):
#     return render(request, 'introduce/Aed.html')
# def Adu(request):
#     return render(request, 'introduce/Adu.html')
# def Ahy(request):
#     return render(request, 'introduce/Ahy.html')
# def Aip(request):
#     return render(request, 'introduce/Aip.html')
# def Amo(request):
#     return render(request, 'introduce/Amo.html')
# def Asi(request):
#     return render(request, 'introduce/Asi.html')
# def Cca(request):
#     return render(request, 'introduce/Cca.html')
# def Car(request):
#     return render(request, 'introduce/Car.html')
# def Cre(request):
#     return render(request, 'introduce/Cre.html')
# def Dod(request):
#     return render(request, 'introduce/Dod.html')
# def Gla(request):
#     return render(request, 'introduce/Gla.html')
# def Gma(request):
#     return render(request, 'introduce/Gma.html')
# def Gso(request):
#     return render(request, 'introduce/Gso.html')
# def Gur(request):
#     return render(request, 'introduce/Gur.html')
# def Lpu(request):
#     return render(request, 'introduce/Lpu.html')
# def Lal(request):
#     return render(request, 'introduce/Lal.html')
# def Lan(request):
#     return render(request, 'introduce/Lan.html')
# def Lja(request):
#     return render(request, 'introduce/Lja.html')
# def Mpo(request):
#     return render(request, 'introduce/Mpo.html')
# def Mru(request):
#     return render(request, 'introduce/Mru.html')
# def Msa(request):
#     return render(request, 'introduce/Msa.html')
#
#
# def Mtr(request):
#     return render(request, 'introduce/Mtr.html')
#
#
# def Mal(request):
#     return render(request, 'introduce/Mal.html')
#
#
# def Nsc(request):
#     return render(request, 'introduce/Nsc.html')
#
#
# def Pac(request):
#     return render(request, 'introduce/Pac.html')
#
#
# def Plu(request):
#     return render(request, 'introduce/Plu.html')
#
#
# def Pvu(request):
#     return render(request, 'introduce/Pvu.html')
#
#
# def Psa(request):
#     return render(request, 'introduce/Psa.html')
#
#
# def Ppi(request):
#     return render(request, 'introduce/Ppi.html')
#
#
# def Pmo(request):
#     return render(request, 'introduce/Pmo.html')
#
#
# def Sja(request):
#     return render(request, 'introduce/Sja.html')
#
#
# def Ssu(request):
#     return render(request, 'introduce/Ssu.html')
#
#
# def Toc(request):
#     return render(request, 'introduce/Toc.html')
#
#
# def Tpa(request):
#     return render(request, 'introduce/Tpa.html')
#
#
# def Tpr(request):
#     return render(request, 'introduce/Tpr.html')
#
#
# def Tre(request):
#     return render(request, 'introduce/Tre.html')
#
#
# def Tsu(request):
#     return render(request, 'introduce/Tsu.html')
#
#
# def Vsa(request):
#     return render(request, 'introduce/Vsa.html')
#
#
# def Van(request):
#     return render(request, 'introduce/Van.html')
#
#
# def Vmu(request):
#     return render(request, 'introduce/Vmu.html')
#
#
# def Vra(request):
#     return render(request, 'introduce/Vra.html')
#
#
# def Vsu(request):
#     return render(request, 'introduce/Vsu.html')
#
#
# def Vum(request):
#     return render(request, 'introduce/Vum.html')
#
#
# def Vun(request):
#     return render(request, 'introduce/Vun.html')
#
#
# def Vma(request):
#     return render(request, 'introduce/Vma.html')
#
#
# def Eph(request):
#     return render(request, 'introduce/Eph.html')
#
#
# def Fal(request):
#     return render(request, 'introduce/Fal.html')
#
#
# def Mpu(request):
#     return render(request, 'introduce/Mpu.html')
#
#
# def Cfa(request):
#     return render(request, 'introduce/Cfa.html')
#
#
# def Bva(request):
#     return render(request, 'introduce/Bva.html')
#
#
# def Sgl(request):
#     return render(request, 'introduce/Sgl.html')
#
#
# def Tin(request):
#     return render(request, 'introduce/Tin.html')
#
#
# def Ccan(request):
#     return render(request, 'introduce/Ccan.html')
#
#
# def Sto(request):
#     return render(request, 'introduce/Sto.html')
#
#
# def Vfa(request):
#     return render(request, 'introduce/Vfa.html')
#
#
# # 江荟搜集的
# def Gsa(request):
#     return render(request, 'introduce/Gsa.html')
# def Gmi(request):
#     return render(request, 'introduce/Gmi.html')
# def Ueu(request):
#     return render(request, 'introduce/Ueu.html')
# def Sju(request):
#     return render(request, 'introduce/Sju.html')
# def Eho(request):
#     return render(request, 'introduce/Eho.html')
# def Ean(request):
#     return render(request, 'introduce/Ean.html')
# def Cst(request):
#     return render(request, 'introduce/Cst.html')
# def Csco(request):
#     return render(request, 'introduce/Csco.html')
# def Ade(request):
#     return render(request, 'introduce/Ade.html')
# def Lana(request):
#     return render(request, 'introduce/Lana.html')
# def Lla(request):
#     return render(request, 'introduce/Lla.html')
# def Lar(request):
#     return render(request, 'introduce/Lar.html')
# def Lpo(request):
#     return render(request, 'introduce/Lpo.html')
# def Lba(request):
#     return render(request, 'introduce/Lba.html')
# def Llu(request):
#     return render(request, 'introduce/Llu.html')
# def Lang(request):
#     return render(request, 'introduce/Lang.html')
# def Aar(request):
#     return render(request, 'introduce/Aar.html')
# def Cge(request):
#     return render(request, 'introduce/Cge.html')
# def Lse(request):
#     return render(request, 'introduce/Lse.html')
# def Rpe(request):
#     return render(request, 'introduce/Rpe.html')
# def Cpa(request):
#     return render(request, 'introduce/Cpa.html')
# def Cal(request):
#     return render(request, 'introduce/Cal.html')
# def Pbu(request):
#     return render(request, 'introduce/Pbu.html')
# def Vdi(request):
#     return render(request, 'introduce/Vdi.html')
# def Cau(request):
#     return render(request, 'introduce/Cau.html')
# def Cpu(request):
#     return render(request, 'introduce/Cpu.html')
# def Tla(request):
#     return render(request, 'introduce/Tla.html')
# def Tsm(request):
#     return render(request, 'introduce/Tsm.html')
# def Pne(request):
#     return render(request, 'introduce/Pne.html')
# def Bbr(request):
#     return render(request, 'introduce/Bbr.html')
# def Swa(request):
#     return render(request, 'introduce/Swa.html')
# def Amo(request):
#     return render(request, 'introduce/Amo.html')
# def Sto(request):
#     return render(request, 'introduce/Sto.html')
# def Sfl(request):
#     return render(request, 'introduce/Sfl.html')
# def Abi(request):
#     return render(request, 'introduce/Abi.html')
# def Eja(request):
#     return render(request, 'introduce/Eja.html')
# def Bsp(request):
#     return render(request, 'introduce/Bsp.html')
# def Csca(request):
#     return render(request, 'introduce/Csca.html')
# def Hmo(request):
#     return render(request, 'introduce/Hmo.html')
# def Ppa(request):
#     return render(request, 'introduce/Ppa.html')
# def Ofo(request):
#     return render(request, 'introduce/Ofo.html')
# def Opi(request):
#     return render(request, 'introduce/Opi.html')
# def Sgu(request):
#     return render(request, 'introduce/Sgu.html')
# def Beb(request):
#     return render(request, 'introduce/Beb.html')
# def Pfl(request):
#     return render(request, 'introduce/Pfl.html')
# def Pmac(request):
#     return render(request, 'introduce/Pmac.html')
# def Pmar(request):
#     return render(request, 'introduce/Pmar.html')
# def Tti(request):
#     return render(request, 'introduce/Tti.html')
# def Cro(request):
#     return render(request, 'introduce/Cro.html')


# 组 --- 工具 --- blast_dotplot
def zu_blast_dotplot(request):
    return render(request, 'zu_blast_dotplot.html')


def zu_block_dotplot(request):
    return render(request, 'zu_block_dotplot.html')


def zu_ks_dotplot(request):
    return render(request, 'zu_ks_dotplot.html')


def zu_ks_calculate(request):
    return render(request, 'zu_ks_calculate.html')


def zu_ks_circos(request):
    return render(request, 'zu_ks_circos.html')


def zu_correspondence_mc(request):
    return render(request, 'zu_correspondence_mc.html')


def zu_retention(request):
    return render(request, 'zu_baoliu.html')


def zu_loss(request):
    return render(request, 'zu_loss.html')


def zu_pindex(request):
    return render(request, 'zu_pindex.html')


# AKRUP
def akrup_run_blast(request):
    return render(request, 'akrup/run_blast.html')

def akrup_run_blast_run(request):
    querypep = request.FILES.get('querypep', None)
    subjectpep = request.FILES.get('subjectpep', None)
    e_value = request.POST.get('e_value', None)
    max_target_seqs = request.POST.get('max_target_seqs', None)
    outfmt = request.POST.get('outfmt', None)
    if querypep is None or subjectpep is None:
        return render(request, '../templates/akrup/run_blast.html')
    c = name_set()
    keep_file(na=querypep, c=c)
    keep_file(na=subjectpep, c=c)
    querypep_name = querypep.name
    subjectpep_name = subjectpep.name
    akrup_run_blast_run_tools(place=c, e_value=e_value, max_target_seqs=max_target_seqs, outfmt=outfmt, querypep_name=querypep_name, subjectpep_name=subjectpep_name)

    files = f"{querypep_name}".split('.')[0] + "_" + f"{subjectpep_name}".split('.')[0] + ".blast"
    return zip_file(request, c, files)


def transcriptome2(request):
    sp_data_1 = request.POST.get("sp_data_1", None)
    sp_data_2 = request.POST.get("sp_data_2", None)
    return render(request, f'transcriptome2.html', {"sp_name": sp_data_1, "type": sp_data_2})


def chart(request):
    return render(request, 'chart.html')

def zu_baoliu(request):
    return render(request, 'zu_baoliu.html')

def zu_diushi(request):
    return render(request, 'zu_diushi.html')

def m6a_chart(request):
    return render(request, 'm6a_chart.html')

def m6A_gene_chart_view(request):
    # 渲染新创建的 m6A_gene_chart.html 模板
    return render(request, 'm6A_gene_chart.html')

def transposable_elements_view(request):
    return render(request, 'transposable_elements_chart.html')

def regulatory_proteins_view(request):
    return render(request, 'regulatory_proteins_chart.html')

def floral_morphology_view(request):
    return render(request, 'floral_morphology_chart.html')

def terpenoid_biosynthesis_view(request):
    return render(request, 'terpenoid_biosynthesis_chart.html')

def heat_stress_view(request):
    return render(request, 'heat_stress_chart.html')

def salt_resistance_view(request):
    return render(request, 'salt_resistance_chart.html')

def drought_tolerance_view(request):
    return render(request, 'drought_tolerance_chart.html')

def rubber_synthesis_view(request):
    return render(request, 'rubber_synthesis_chart.html')

def inulin_related_family_view(request):
    return render(request, 'inulin_related_family_chart.html')

def mgas_eupl_ref_view(request):
    return render(request, 'mgas_eupl_reference.html')

def mgas_vitis_ref_view(request):
    """展示 Vitis vinifera MGAs 图片的页面"""
    return render(request, 'mgas_vitis_reference.html')

def mgas_arctium_ref_view(request):
    """展示 Arctium lappa MGAs 图片的页面"""
    return render(request, 'mgas_arctium_reference.html')

def mgas_helianthus_ref_view(request):
    """展示 Helianthus annuus MGAs 图片的页面"""
    return render(request, 'mgas_helianthus_reference.html')

def f_blast(request):
    return render(request, 'f_blast.html')

def hierarchical_alignments_eupl(request):
    return render(request, 'hierarchical_alignments_eupl.html')


## Analysis Pipelines

def pipeline_wgd_identification(request):
    """
    视图函数：渲染 WGD Identification Pipeline 页面
    """
    return render(request, 'pipeline_wgd_identification.html')

def pipeline_aags_reconstruction(request):
    """
    视图函数：渲染 AAGs Reconstruction Pipeline 页面
    """
    return render(request, 'pipeline_aags_reconstruction.html')

def pipeline_trait_associated(request):
    """
    视图函数：渲染 Trait-associated Gene Origins Pipeline 页面
    """
    return render(request, 'pipeline_trait_associated.html')

def pipeline_go_annotation(request):
    """
    视图函数：渲染 GO Annotation Pipeline 页面
    """
    return render(request, 'pipeline_go_annotation.html')

def pipeline_kegg_annotation(request):
    """
    视图函数：渲染 KEGG Annotation Pipeline 页面
    """
    return render(request, 'pipeline_kegg_annotation.html')

def pipeline_identification_of_rps(request):
    """
    视图函数：渲染 Identification of RPs Pipeline 页面
    """
    return render(request, 'pipeline_identification_of_rps.html')

def pipeline_m6a_identification(request):
    """
    视图函数：渲染 m6A Identification Pipeline 页面
    """
    return render(request, 'pipeline_m6a_identification.html')

def pipeline_gene_duplication_types(request):
    """
    视图函数：渲染 Gene Duplication Types Pipeline 页面
    """
    return render(request, 'pipeline_gene_duplication_types.html')

def pipeline_transposable_elements(request):
    """
    视图函数：渲染 Transposable Elements Pipeline 页面
    """
    return render(request, 'pipeline_transposable_elements.html')

def encyclopedia(request):
    """
    渲染百科页面容器，数据由前端异步加载
    """
    # 模板直接放在 templates/ 根目录下，所以直接引用文件名
    return render(request, 'encyclopedia.html')
