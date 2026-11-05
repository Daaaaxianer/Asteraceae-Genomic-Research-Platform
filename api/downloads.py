"""Controlled public files, owned results, and bounded browser exports."""
import mimetypes
from pathlib import Path
import re
from http.client import HTTPConnection
from urllib.parse import quote, urlencode

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.core.files.uploadhandler import TemporaryFileUploadHandler, StopUpload


PUBLIC_STATIC_ROOTS = frozenset((
    'Species_data', 'ancestral_data', 'ancestral_combined', 'example_file',
    'collinear_kaks_mc', 'transcriptome_json', 'TE_json', 'TE_out_file',
    'syn_data', 'dotplot', 'json', 'Gene_Trees', 'Gene_Trees_block',
    'Orthogroup_Sequences', 'Orthogroup_Sequences_Block', 'Orthogroup_tree_png',
    'Orthogroup_tree_png_non', 'ortho_trees', 'blastp_blk_ks_zip',
    'bio_package', 'blast_match_database', 'L_pathway', 'Tin_genome', 'videos',
))
ALLOWED_SUFFIXES = frozenset((
    '.txt', '.tsv', '.csv', '.json', '.fasta', '.fa', '.faa', '.fna', '.cds',
    '.pep', '.lens', '.len', '.gff', '.gff3', '.gtf', '.bed', '.blast', '.newick',
    '.nwk', '.tree', '.treefile', '.hmm', '.ks', '.axt', '.homologs', '.block',
    '.collinearity', '.gz', '.zip', '.tar', '.bz2', '.xz', '.7z', '.pdf', '.svg',
    '.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff', '.xlsx', '.xls', '.docx',
    '.pptx', '.md', '.xml', '.html', '.htm', '.nex', '.nexus', '.phylip', '.phy',
    '.aln', '.paf', '.out', '.dat', '.rr', '.mc', '.fai', '.gzi', '.bz', '.a3m',
    '.tre', '.rar', '.bam', '.bai', '.cram', '.crai', '.vcf', '.tbi', '.csi',
    '.bw', '.bigwig', '.bb', '.bigbed', '.2bit', '.bgz', '.ix', '.ixx', '.mp4', '.webm', '.mov', '.ogg', '.gif',
))


def error(code, message='Download resource is unavailable.'):
    return JsonResponse({'status': 'error', 'message': message}, status=code)


def safe_path(base, relative):
    relative = str(relative)
    if (not relative or relative.startswith('/') or '\\' in relative
            or any(ord(c) < 32 or ord(c) == 127 for c in relative)
            or any(part.startswith('.') for part in relative.split('/'))):
        return None
    try:
        root = Path(base).resolve()
        path = (root / relative).resolve()
        path.relative_to(root)
        return path if path.is_file() else None
    except (ValueError, OSError, RuntimeError):
        return None


def file_response(request, path, download=True, filename=None):
    if request.method not in ('GET', 'HEAD'):
        return error(405, 'Use GET or HEAD for file retrieval.')
    path = Path(path)
    size = path.stat().st_size
    content_type = 'application/octet-stream' if download else (mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
    raw_range = request.META.get('HTTP_RANGE')
    first, last = 0, size - 1
    if raw_range:
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', raw_range)
        try:
            if match is None or not any(match.groups()) or size == 0:
                raise ValueError
            left, right = match.groups()
            if left:
                first = int(left)
                last = min(int(right), size - 1) if right else size - 1
            else:
                suffix = int(right)
                if suffix <= 0:
                    raise ValueError
                first = max(0, size - suffix)
            if first > last or first >= size:
                raise ValueError
        except ValueError:
            response = error(416, 'Requested byte range is unavailable.')
            response['Content-Range'] = 'bytes */' + str(size)
            return response
    length = max(0, last - first + 1)
    if request.method == 'HEAD':
        response = HttpResponse(content_type=content_type, status=206 if raw_range else 200)
    elif raw_range:
        source = path.open('rb')
        source.seek(first)

        def chunks():
            remaining = length
            try:
                while remaining:
                    block = source.read(min(65536, remaining))
                    if not block:
                        break
                    remaining -= len(block)
                    yield block
            finally:
                source.close()

        response = StreamingHttpResponse(chunks(), status=206, content_type=content_type)
        response._resource_closers.append(source.close)
    else:
        response = FileResponse(path.open('rb'), as_attachment=download,
                                filename=filename or path.name, content_type=content_type)
    response['Content-Length'] = str(length)
    response['Accept-Ranges'] = 'bytes'
    if raw_range:
        response['Content-Range'] = 'bytes %s-%s/%s' % (first, last, size)
    if download and 'Content-Disposition' not in response:
        response['Content-Disposition'] = "attachment; filename*=UTF-8''" + quote(filename or path.name)
    if not download and path.suffix.lower() in ('.html', '.htm', '.svg'):
        response['Content-Security-Policy'] = 'sandbox allow-scripts allow-downloads'
    return response


def public_file(request, source, path, download=True):
    if source not in ('static', 'static_assets', 'example', 'jbrowse'):
        return error(404)
    if source == 'static' and path.split('/', 1)[0] not in PUBLIC_STATIC_ROOTS:
        return error(404)
    if source == 'static_assets' and (path.split('/', 1)[0] != 'image' or Path(path).suffix.lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.webp')):
        return error(404)
    base = Path(getattr(settings, 'AGRP_JBROWSE_ROOT', '/wangjp/Asteraceae/AGRP_jbrowse')) if source == 'jbrowse' else Path(settings.BASE_DIR) / ('static' if source == 'static_assets' else source)
    selected = safe_path(base, path)
    if selected is None or selected.suffix.lower() not in ALLOWED_SUFFIXES:
        return error(404)
    return file_response(request, selected, download=download)


def result_file(request, path, download=True):
    from api.download_access import owns_path, result_credential
    selected = safe_path(Path(settings.BASE_DIR) / 'file_keep', path)
    if selected is None or not owns_path(selected, request):
        return error(404)
    response = file_response(request, selected, download=download)
    credential = result_credential(selected, request)
    if credential:
        response['X-AGRP-Result-Link'] = '/api/download/result/' + quote(path, safe='/') + '?' + urlencode({'access_token': credential})
    return response


def browser_export(request):
    if request.method != 'POST':
        return error(405, 'Use POST to export a browser-generated file.')
    maximum = int(getattr(settings, 'AGRP_API_EXPORT_MAX_BYTES', 16 * 1024 * 1024))
    try:
        if int(request.META.get('CONTENT_LENGTH', 0)) > maximum + 65536:
            return error(413, 'Export exceeds the size limit.')
    except ValueError:
        return error(400, 'Invalid upload length.')

    class BoundedExportUpload(TemporaryFileUploadHandler):
        total = 0
        def receive_data_chunk(self, raw_data, start):
            self.total += len(raw_data)
            if self.total > maximum:
                request._export_too_large = True
                raise StopUpload(connection_reset=True)
            return super().receive_data_chunk(raw_data, start)

    request.upload_handlers = [BoundedExportUpload(request)]
    upload = request.FILES.get('file')
    if getattr(request, '_export_too_large', False):
        return error(413, 'Export exceeds the size limit.')
    if upload is None:
        return error(400, 'Missing export file.')
    if upload.size > maximum:
        return error(413, 'Export exceeds the size limit.')
    if Path(upload.name).suffix.lower() not in ALLOWED_SUFFIXES:
        return error(400, 'Unsupported export format.')
    # Stream the submitted export back without saving it or opening a supplied path.
    return FileResponse(upload, as_attachment=True, filename=upload.name,
                        content_type='application/octet-stream')


def legacy_file_download(request):
    """Restrict the old absolute-file parameter to published or owned files."""
    supplied = request.GET.get('file') or request.GET.get('filename') or ''
    try:
        candidate = Path(supplied).resolve()
    except (ValueError, OSError, RuntimeError):
        return error(404)
    root = Path(settings.BASE_DIR).resolve()
    for source in ('static', 'example', 'file_keep'):
        try:
            relative = candidate.relative_to(root / source).as_posix()
        except ValueError:
            continue
        return result_file(request, relative) if source == 'file_keep' else public_file(request, source, relative)
    return error(404)


def service_download(request, service, path):
    """Proxy only the two explicit SequenceServer download operations."""
    if service != 'sequenceserver':
        return error(404)
    report = re.fullmatch(r'download/[A-Za-z0-9_-]{16,80}\.[A-Za-z0-9_-]{1,16}', path)
    if not ((report and request.method == 'GET') or (path == 'get_sequence' and request.method == 'POST')):
        return error(404)
    try:
        if int(request.META.get('CONTENT_LENGTH', 0) or 0) > 2 * 1024 * 1024:
            return error(413, 'Sequence selection is too large.')
    except ValueError:
        return error(400)
    connection = HTTPConnection('127.0.0.1', 8515, timeout=60)
    try:
        target = '/' + path
        query = request.META.get('QUERY_STRING', '')
        if query:
            target += '?' + query
        connection.request(request.method, target, body=request.body if request.method == 'POST' else None,
                           headers={'Content-Type': request.META.get('CONTENT_TYPE', 'application/x-www-form-urlencoded'),
                                    'X-Forwarded-Prefix': '/tools/sequenceserver-app'})
        upstream = connection.getresponse()
        if upstream.status not in (200, 206):
            connection.close()
            return error(404 if upstream.status == 404 else 502)
        def chunks():
            try:
                while True:
                    block = upstream.read(65536)
                    if not block:
                        break
                    yield block
            finally:
                connection.close()
        response = StreamingHttpResponse(chunks(), status=upstream.status,
                                         content_type=upstream.getheader('Content-Type', 'application/octet-stream'))
        response._resource_closers.append(connection.close)
        for header in ('Content-Disposition', 'Content-Length', 'Content-Range', 'Accept-Ranges'):
            value = upstream.getheader(header)
            if value:
                response[header] = value
        if 'Content-Disposition' not in response:
            response['Content-Disposition'] = 'attachment; filename="sequenceserver-result.txt"'
        return response
    except (OSError, ValueError):
        connection.close()
        return error(502, 'Result service is temporarily unavailable.')
