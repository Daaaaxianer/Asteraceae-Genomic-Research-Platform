import json
import ipaddress
import re
import logging
from pathlib import Path
from urllib.parse import quote, urlencode

from django.conf import settings
from django.http import FileResponse
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from api.access_control import get_query_max_limit, get_proxy_context

logger = logging.getLogger('agrp.api')


GENOME_FILE_DIR = Path(settings.BASE_DIR) / 'static' / 'Species_data'
ANCESTRAL_FILE_DIR = Path(settings.BASE_DIR) / 'static' / 'ancestral_data'
COLLINEAR_KAKS_JSON = Path(settings.BASE_DIR) / 'static' / 'collinear_kaks_mc' / 'colinearscan_kaks.json'
DOTPLOT_JSON = Path(settings.BASE_DIR) / 'static' / 'collinear_kaks_mc' / 'dotplot.json'
PANGENOME_JSON = Path(settings.BASE_DIR) / 'static' / 'syn_data' / 'fan.json'
TRANSCRIPTOME_JSON_DIR = Path(settings.BASE_DIR) / 'static' / 'transcriptome_json'

ALLOWED_GENOME_FILE_TYPES = {
    'cds': '{species}.cds',
    'pep': '{species}.pep',
    'lens': '{species}.lens',
    'gff': '{species}.new.gff',
}

ALLOWED_ANCESTRAL_FILE_TYPES = {
    'cds': '{dataset}.cds',
    'pep': '{dataset}.pep',
    'lens': '{dataset}.lens',
    'gff': '{dataset}.new.gff',
}

SPECIES_CODE_RE = re.compile(r'^[A-Za-z0-9_.-]+$')
ANCESTRAL_CODE_RE = re.compile(r'^[A-Za-z0-9_.-]+$')

ANCESTRAL_DATASETS = (
    'AAKI', 'AAKII', 'AAKIII', 'ACAK',
    'ASAKI', 'ASAKII', 'ASAKIII', 'ASAKIV', 'ASAKV', 'ASAKVI', 'ASAKVII',
    'ASAKVIII', 'ASAKIX', 'ASAKX', 'ASAKXI', 'ASAKXII', 'ASAKXIII',
    'ASAKXIV', 'ASAKXV', 'ASAKXVI', 'ASAKXVII', 'ASAKXVIII', 'ASAKXIX',
    'CAAKI', 'CAAKII', 'CAAKIII', 'CAAKIV', 'CIAKI', 'CIAKII',
)

ANCESTRAL_DISPLAY_LABELS = {
    'AAKI': 'AAK-I',
    'AAKII': 'AAK-II',
    'AAKIII': 'AAK-III',
    'ACAK': 'ACAK',
    'ASAKI': 'ASAK-I',
    'ASAKII': 'ASAK-II',
    'ASAKIII': 'ASAK-III',
    'ASAKIV': 'ASAK-IV',
    'ASAKV': 'ASAK-V',
    'ASAKVI': 'ASAK-VI',
    'ASAKVII': 'ASAK-VII',
    'ASAKVIII': 'ASAK-VIII',
    'ASAKIX': 'ASAK-IX',
    'ASAKX': 'ASAK-X',
    'ASAKXI': 'ASAK-XI',
    'ASAKXII': 'ASAK-XII',
    'ASAKXIII': 'ASAK-XIII',
    'ASAKXIV': 'ASAK-XIV',
    'ASAKXV': 'ASAK-XV',
    'ASAKXVI': 'ASAK-XVI',
    'ASAKXVII': 'ASAK-XVII',
    'ASAKXVIII': 'ASAK-XVIII',
    'ASAKXIX': 'ASAK-XIX',
    'CAAKI': 'CAAK-I',
    'CAAKII': 'CAAK-II',
    'CAAKIII': 'CAAK-III',
    'CAAKIV': 'CAAK-IV',
    'CIAKI': 'CIAK-I',
    'CIAKII': 'CIAK-II',
}


INTERPROSCAN_SPECIES = (
    'Aann', 'Aary', 'Amar', 'Amtr', 'Arla', 'Armi', 'Artr', 'Bial', 'Busi',
    'Ccar', 'Ceso', 'Chla', 'Chma', 'Chmo', 'Chna', 'Cich', 'Cien', 'Cind',
    'Cobi', 'Cpa', 'Cati', 'Dapi', 'Desu', 'Ecan', 'Enbr', 'Eupl', 'Fbi',
    'Fbr', 'Ffl', 'Fli', 'Fra', 'Fro', 'Fso', 'Ftr', 'Gehy', 'Glco', 'Hean',
    'Hetu', 'Heub', 'Laca', 'Lomi', 'Lssa', 'Mimi', 'Nenu', 'Nin', 'Pin',
    'Pdy', 'Pslu', 'Sain', 'Scae', 'Sesq', 'Smso', 'Soca', 'Stre', 'Taer',
    'Tako', 'Tamo', 'Tesi', 'Vivi',
)

INTERPROSCAN_DATABASES = (
    'ProSitePatterns', 'PANTHER', 'Coils', 'Pfam', 'Gene3D', 'PRINTS',
    'SUPERFAMILY', 'ProSiteProfiles', 'PIRSF', 'CDD', 'TIGRFAM', 'Hamap',
    'MobiDBLite', 'SMART', 'SFLD', 'AntiFam',
)


def _allowed_types(file_type_map):
    return list(file_type_map.keys())


def _api_url(request, path, query_params=None):
    query_string = ''
    if query_params:
        query_string = '?' + urlencode(query_params)
    return request.build_absolute_uri(f'/api/{path.lstrip("/")}{query_string}')


def _safe_resolve(base_dir, filename):
    base_path = Path(base_dir).resolve()
    try:
        file_path = (base_path / filename).resolve()
        file_path.relative_to(base_path)
    except (ValueError, OSError, RuntimeError):
        return base_path, base_path, False
    return base_path, file_path, True


def _file_response(file_path, filename):
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename,
        content_type='application/octet-stream',
    )


def _file_metadata(file_path):
    if not file_path.is_file():
        return False, None
    return True, file_path.stat().st_size


def _static_file_url(request, *path_parts):
    quoted_parts = [quote(str(part).strip('/')) for part in path_parts if str(part)]
    return request.build_absolute_uri('/static/' + '/'.join(quoted_parts))


def _load_json_file(file_path):
    try:
        max_bytes = int(getattr(settings, 'AGRP_API_JSON_MAX_BYTES', 16 * 1024 * 1024))
        if file_path.stat().st_size > max_bytes:
            return None, Response({'status': 'error', 'message': 'JSON resource exceeds the online query size limit.'}, status=413)
        with open(file_path, 'rb') as json_file:
            content = json_file.read(max_bytes + 1)
        if len(content) > max_bytes:
            return None, Response({'status': 'error', 'message': 'JSON resource exceeds the online query size limit.'}, status=413)
        return json.loads(content), None
    except FileNotFoundError:
        return None, Response(
            {
                'status': 'error',
                'message': 'JSON file not found.',
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    except (ValueError, UnicodeError, OSError):
        logger.exception('API JSON resource could not be read')
        return None, Response(
            {
                'status': 'error',
                'message': 'Invalid JSON file.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _extract_records(payload):
    """
    Convert common JSON table formats into a record list for filtering/pagination.

    Supported shapes:
    - [ {...}, {...} ]
    - { "data": [ ... ] }
    - { "aaData": [ ... ] }
    - { "rows": [ ... ] }
    - { "results": [ ... ] }
    """
    if isinstance(payload, list):
        return payload, None

    if isinstance(payload, dict):
        for key in ('data', 'aaData', 'rows', 'results'):
            value = payload.get(key)
            if isinstance(value, list):
                return value, key

    return None, None


def _parse_limit_offset(request, default_limit=100, max_limit=None):
    tier_limit = get_query_max_limit(request)
    max_limit = min(tier_limit, max_limit) if max_limit is not None else tier_limit
    raw_limit = str(request.query_params.get('limit', default_limit)).strip().lower()
    raw_offset = str(request.query_params.get('offset', 0)).strip()

    if raw_limit in ('all', 'none', '0'):
        limit = max_limit
    else:
        try:
            limit = int(raw_limit)
        except ValueError:
            return None, None, Response(
                {
                    'status': 'error',
                    'message': 'Invalid limit parameter. Use a positive integer or limit=all.',
                    'limit': raw_limit,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if limit < 1:
            return None, None, Response(
                {
                    'status': 'error',
                    'message': 'Invalid limit parameter. Use a positive integer or limit=all.',
                    'limit': raw_limit,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = min(limit, max_limit)

    try:
        offset = int(raw_offset)
    except ValueError:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid offset parameter. Use a non-negative integer.',
                'offset': raw_offset,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if offset < 0 or offset > int(getattr(settings, 'AGRP_API_MAX_OFFSET', 100000)):
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Offset is outside the supported online query range.',
                'offset': raw_offset,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return limit, offset, None


def _filter_records(records, query):
    if not query:
        return records

    keyword = str(query).strip().lower()
    if not keyword:
        return records

    filtered = []
    for record in records:
        text = json.dumps(record, ensure_ascii=False, default=str).lower()
        if keyword in text:
            filtered.append(record)
    return filtered


def _json_table_response(request, resource_name, file_path):
    payload, error_response = _load_json_file(file_path)
    if error_response is not None:
        return error_response

    records, container_key = _extract_records(payload)
    if records is None:
        return Response(
            {
                'status': 'ok',
                'resource': resource_name,
                'format': 'object',
                'data': payload,
            },
            status=status.HTTP_200_OK,
        )

    limit, offset, error_response = _parse_limit_offset(request)
    if error_response is not None:
        return error_response

    query = request.query_params.get('q', '').strip()
    filtered_records = _filter_records(records, query)
    total_count = len(records)
    filtered_count = len(filtered_records)

    if limit is None:
        page_records = filtered_records[offset:]
    else:
        page_records = filtered_records[offset:offset + limit]

    return Response(
        {
            'status': 'ok',
            'resource': resource_name,
            'format': 'table',
            'source_file': file_path.name,
            'container_key': container_key,
            'total_count': total_count,
            'filtered_count': filtered_count,
            'limit': limit,
            'offset': offset,
            'returned_count': len(page_records),
            'query': query,
            'data': page_records,
        },
        status=status.HTTP_200_OK,
    )


def _validate_transcriptome_json_filename(value):
    filename = str(value or '').strip()
    if not filename:
        return None, Response(
            {
                'status': 'error',
                'message': 'Missing required parameter: name or filename',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if filename.endswith('.json'):
        normalized_filename = filename
    else:
        normalized_filename = f'{filename}.json'

    if (len(normalized_filename) > 255 or any(ord(char) < 32 or ord(char) == 127 for char in normalized_filename)
            or '/' in normalized_filename or '\\' in normalized_filename or normalized_filename.startswith('.')):
        return None, Response(
            {
                'status': 'error',
                'message': 'Invalid filename parameter.',
                'filename': filename,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return normalized_filename, None


def _normalize_ancestor_code(value):
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())


def _ancestor_label(code):
    normalized = _normalize_ancestor_code(code)
    return ANCESTRAL_DISPLAY_LABELS.get(normalized, code or normalized)


def _validate_genome_params(request):
    species = request.query_params.get('species', '').strip()
    file_type = request.query_params.get('type', '').strip().lower()

    if not species:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Missing required parameter: species',
                'allowed_types': _allowed_types(ALLOWED_GENOME_FILE_TYPES),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not SPECIES_CODE_RE.match(species):
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid species parameter. Only letters, numbers, underscores, hyphens and dots are allowed.',
                'species': species,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not file_type:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Missing required parameter: type',
                'allowed_types': _allowed_types(ALLOWED_GENOME_FILE_TYPES),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if file_type not in ALLOWED_GENOME_FILE_TYPES:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid type parameter.',
                'type': file_type,
                'allowed_types': _allowed_types(ALLOWED_GENOME_FILE_TYPES),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return species, file_type, None


def _validate_ancestral_params(request):
    raw_dataset = request.query_params.get('dataset', '').strip()
    file_type = request.query_params.get('type', '').strip().lower()

    if not raw_dataset:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Missing required parameter: dataset',
                'allowed_datasets': list(ANCESTRAL_DATASETS),
                'allowed_types': _allowed_types(ALLOWED_ANCESTRAL_FILE_TYPES),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not ANCESTRAL_CODE_RE.match(raw_dataset):
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid dataset parameter. Only letters, numbers, underscores, hyphens and dots are allowed.',
                'dataset': raw_dataset,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    dataset = _normalize_ancestor_code(raw_dataset)
    if dataset not in ANCESTRAL_DATASETS:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid dataset parameter.',
                'dataset': raw_dataset,
                'normalized_dataset': dataset,
                'allowed_datasets': list(ANCESTRAL_DATASETS),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not file_type:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Missing required parameter: type',
                'allowed_types': _allowed_types(ALLOWED_ANCESTRAL_FILE_TYPES),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if file_type not in ALLOWED_ANCESTRAL_FILE_TYPES:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid type parameter.',
                'type': file_type,
                'allowed_types': _allowed_types(ALLOWED_ANCESTRAL_FILE_TYPES),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return dataset, file_type, None


@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    return Response(
        {
            'status': 'ok',
            'message': 'AGRP API is running',
            'version': '1.0',
            'base_url': request.build_absolute_uri('/api/'),
        },
        status=status.HTTP_200_OK,
    )




def _detect_client_ip(request):
    address, source, _ = get_proxy_context(request)
    return address or None, source


def _is_private_or_local_ip(ip_value):
    """Return True/False for private-local IPs, or None if the value cannot be parsed."""
    if not ip_value:
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_value)
    except ValueError:
        return None
    return bool(ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local)


@api_view(['GET'])
@permission_classes([AllowAny])
def whoami(request):
    """
    Show the client IP address detected by AGRP API.

    This endpoint helps collaborators provide the correct public IP address
    when applying for registered-IP high-throughput access.
    """
    detected_ip, ip_source = _detect_client_ip(request)
    is_private_or_local = _is_private_or_local_ip(detected_ip)

    return Response(
        {
            'status': 'ok',
            'detected_ip': detected_ip,
            'ip_source': ip_source,
            'is_private_or_local': is_private_or_local,
            'message': 'This is the client IP address detected by the AGRP API for this request.',
            'application_note': (
                'Use this IP for registered-IP access only if it belongs to a fixed server '
                'or stable institutional computing environment. Shared campus networks, '
                'public Wi-Fi, mobile hotspots, and unstable NAT IPs should normally use API key access instead.'
            ),
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def genome_file_check(request):
    """
    Check whether a genome-related static file exists.

    Example:
    /api/files/genome/?species=Aann&type=cds
    """
    species, file_type, error_response = _validate_genome_params(request)
    if error_response is not None:
        return error_response

    filename = ALLOWED_GENOME_FILE_TYPES[file_type].format(species=species)
    _, file_path, is_safe = _safe_resolve(GENOME_FILE_DIR, filename)
    if not is_safe:
        return Response(
            {
                'status': 'error',
                'message': 'Invalid file path.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    exists, size = _file_metadata(file_path)
    download_url = None
    if exists:
        download_url = _api_url(
            request,
            'download/genome/',
            {'species': species, 'type': file_type},
        )

    return Response(
        {
            'status': 'ok',
            'species': species,
            'type': file_type,
            'filename': filename,
            'exists': exists,
            'size': size,
            'download_url': download_url,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def genome_file_download(request):
    """
    Download a genome-related static file.

    Example:
    /api/download/genome/?species=Aann&type=cds
    """
    species, file_type, error_response = _validate_genome_params(request)
    if error_response is not None:
        return error_response

    filename = ALLOWED_GENOME_FILE_TYPES[file_type].format(species=species)
    _, file_path, is_safe = _safe_resolve(GENOME_FILE_DIR, filename)
    if not is_safe:
        return Response(
            {
                'status': 'error',
                'message': 'Invalid file path.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not file_path.is_file():
        return Response(
            {
                'status': 'error',
                'message': 'File not found.',
                'species': species,
                'type': file_type,
                'filename': filename,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return _file_response(file_path, filename)


def _build_genome_species_response(request):
    """Build the shared response for genome species list endpoints."""
    base_dir = GENOME_FILE_DIR.resolve()
    species_map = {}

    if base_dir.is_dir():
        for file_path in base_dir.iterdir():
            if not file_path.is_file():
                continue

            filename = file_path.name
            species = None
            file_type = None

            if filename.endswith('.new.gff'):
                species = filename[:-len('.new.gff')]
                file_type = 'gff'
            elif filename.endswith('.cds'):
                species = filename[:-len('.cds')]
                file_type = 'cds'
            elif filename.endswith('.pep'):
                species = filename[:-len('.pep')]
                file_type = 'pep'
            elif filename.endswith('.lens'):
                species = filename[:-len('.lens')]
                file_type = 'lens'

            if not species or not file_type or not SPECIES_CODE_RE.match(species):
                continue

            species_map.setdefault(species, {})[file_type] = file_path

    data = []
    for species in sorted(species_map.keys()):
        files = {}
        for file_type, pattern in ALLOWED_GENOME_FILE_TYPES.items():
            filename = pattern.format(species=species)
            file_path = species_map.get(species, {}).get(file_type)
            exists = bool(file_path and file_path.is_file())
            size = file_path.stat().st_size if exists else None
            files[file_type] = {
                'filename': filename,
                'exists': exists,
                'size': size,
                'check_url': _api_url(
                    request,
                    'files/genome/',
                    {'species': species, 'type': file_type},
                ),
                'download_url': _api_url(
                    request,
                    'download/genome/',
                    {'species': species, 'type': file_type},
                ) if exists else None,
            }

        data.append({
            'species': species,
            'available_types': [
                file_type for file_type in ALLOWED_GENOME_FILE_TYPES
                if files[file_type]['exists']
            ],
            'files': files,
        })

    return Response(
        {
            'status': 'ok',
            'count': len(data),
            'data': data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def genome_species_list(request):
    """
    List species with available genome files under static/Species_data/.

    Example:
    /api/files/genome/species/
    """
    return _build_genome_species_response(request)


@api_view(['GET'])
@permission_classes([AllowAny])
def genomics_species_list(request):
    """
    Alias endpoint for genome species resources.

    Example:
    /api/genomics/species/
    """
    return _build_genome_species_response(request)


@api_view(['GET'])
@permission_classes([AllowAny])
def ancestral_genomes_list(request):
    """
    List ancestral genome datasets and downloadable files.

    Example:
    /api/genosyn/ancestral-genomes/
    """
    data = []
    for dataset in ANCESTRAL_DATASETS:
        dataset_dir = (ANCESTRAL_FILE_DIR / dataset).resolve()
        files = {}

        for file_type, pattern in ALLOWED_ANCESTRAL_FILE_TYPES.items():
            filename = pattern.format(dataset=dataset)
            _, file_path, is_safe = _safe_resolve(dataset_dir, filename)
            exists = is_safe and file_path.is_file()
            size = file_path.stat().st_size if exists else None
            files[file_type] = {
                'filename': filename,
                'exists': exists,
                'size': size,
                'check_url': _api_url(
                    request,
                    'files/ancestral/',
                    {'dataset': dataset, 'type': file_type},
                ),
                'download_url': _api_url(
                    request,
                    'download/ancestral/',
                    {'dataset': dataset, 'type': file_type},
                ) if exists else None,
            }

        data.append({
            'dataset': dataset,
            'label': _ancestor_label(dataset),
            'available_types': [
                file_type for file_type in ALLOWED_ANCESTRAL_FILE_TYPES
                if files[file_type]['exists']
            ],
            'files': files,
        })

    return Response(
        {
            'status': 'ok',
            'count': len(data),
            'data': data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def ancestral_file_check(request):
    """
    Check whether an ancestral genome file exists.

    Example:
    /api/files/ancestral/?dataset=AAKI&type=cds
    """
    dataset, file_type, error_response = _validate_ancestral_params(request)
    if error_response is not None:
        return error_response

    filename = ALLOWED_ANCESTRAL_FILE_TYPES[file_type].format(dataset=dataset)
    base_dir = (ANCESTRAL_FILE_DIR / dataset).resolve()
    _, file_path, is_safe = _safe_resolve(base_dir, filename)
    if not is_safe:
        return Response(
            {
                'status': 'error',
                'message': 'Invalid file path.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    exists, size = _file_metadata(file_path)
    download_url = None
    if exists:
        download_url = _api_url(
            request,
            'download/ancestral/',
            {'dataset': dataset, 'type': file_type},
        )

    return Response(
        {
            'status': 'ok',
            'dataset': dataset,
            'label': _ancestor_label(dataset),
            'type': file_type,
            'filename': filename,
            'exists': exists,
            'size': size,
            'download_url': download_url,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def ancestral_file_download(request):
    """
    Download an ancestral genome file.

    Example:
    /api/download/ancestral/?dataset=AAKI&type=cds
    """
    dataset, file_type, error_response = _validate_ancestral_params(request)
    if error_response is not None:
        return error_response

    filename = ALLOWED_ANCESTRAL_FILE_TYPES[file_type].format(dataset=dataset)
    base_dir = (ANCESTRAL_FILE_DIR / dataset).resolve()
    _, file_path, is_safe = _safe_resolve(base_dir, filename)
    if not is_safe:
        return Response(
            {
                'status': 'error',
                'message': 'Invalid file path.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not file_path.is_file():
        return Response(
            {
                'status': 'error',
                'message': 'File not found.',
                'dataset': dataset,
                'type': file_type,
                'filename': filename,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return _file_response(file_path, filename)


@api_view(['GET'])
@permission_classes([AllowAny])
def collinear_kaks_api(request):
    """
    Return syntenic block / KaKs table data from static/collinear_kaks_mc/colinearscan_kaks.json.

    Example:
    /api/genosyn/collinear-kaks/?limit=100&offset=0
    /api/genosyn/collinear-kaks/?q=Aann
    """
    return _json_table_response(request, 'collinear_kaks', COLLINEAR_KAKS_JSON)


@api_view(['GET'])
@permission_classes([AllowAny])
def dotplots_api(request):
    """
    Return dotplot index data from static/collinear_kaks_mc/dotplot.json.

    Example:
    /api/genosyn/dotplots/?limit=100&offset=0
    /api/genosyn/dotplots/?q=Aann
    """
    return _json_table_response(request, 'dotplots', DOTPLOT_JSON)


@api_view(['GET'])
@permission_classes([AllowAny])
def pangenome_api(request):
    """
    Return pan-genome resources from static/syn_data/fan.json.

    Example:
    /api/multiomics/pangenome/?limit=100&offset=0
    /api/multiomics/pangenome/?q=Helianthus
    """
    return _json_table_response(request, 'pangenome', PANGENOME_JSON)


@api_view(['GET'])
@permission_classes([AllowAny])
def transcriptome_samples_api(request):
    """
    List transcriptome sample JSON files under static/transcriptome_json/.

    Example:
    /api/multiomics/transcriptome/samples/
    /api/multiomics/transcriptome/samples/?q=stem
    """
    base_dir = TRANSCRIPTOME_JSON_DIR.resolve()
    query = request.query_params.get('q', '').strip().lower()
    data = []

    if base_dir.is_dir():
        for file_path in sorted(base_dir.glob('*.json'), key=lambda item: item.name.lower()):
            filename = file_path.name
            sample_name = filename[:-len('.json')]
            if query and query not in sample_name.lower() and query not in filename.lower():
                continue

            try:
                size = file_path.stat().st_size
            except OSError:
                size = None

            data.append({
                'sample': sample_name,
                'filename': filename,
                'size': size,
                'api_url': _api_url(
                    request,
                    'multiomics/transcriptome/sample/',
                    {'filename': filename},
                ),
                'static_url': _static_file_url(
                    request,
                    'transcriptome_json',
                    filename,
                ),
            })

    return Response(
        {
            'status': 'ok',
            'count': len(data),
            'query': query,
            'data': data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def transcriptome_sample_api(request):
    """
    Return one transcriptome sample JSON file.

    Example:
    /api/multiomics/transcriptome/sample/?filename=Dapi_white%20petal.json
    /api/multiomics/transcriptome/sample/?name=Dapi_white%20petal
    """
    filename_param = request.query_params.get('filename') or request.query_params.get('name')
    filename, error_response = _validate_transcriptome_json_filename(filename_param)
    if error_response is not None:
        return error_response

    _, file_path, is_safe = _safe_resolve(TRANSCRIPTOME_JSON_DIR, filename)
    if not is_safe:
        return Response(
            {
                'status': 'error',
                'message': 'Invalid file path.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload, error_response = _load_json_file(file_path)
    if error_response is not None:
        return error_response

    sample_name = filename[:-len('.json')]
    return Response(
        {
            'status': 'ok',
            'sample': sample_name,
            'filename': filename,
            'data': payload,
        },
        status=status.HTTP_200_OK,
    )



# -----------------------------------------------------------------------------
# Database-backed Genomics APIs
# -----------------------------------------------------------------------------

def _quote_identifier(identifier):
    """Safely quote a MySQL table/column identifier after strict validation."""
    identifier = str(identifier or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_]+', identifier):
        return None
    return f'`{identifier}`'


def _split_terms(raw_value):
    """Split newline/comma separated query terms while keeping semicolons inside descriptions."""
    if raw_value is None:
        return []
    if isinstance(raw_value, (list, tuple)):
        values = []
        for item in raw_value:
            values.extend(_split_terms(item))
        return values
    return [item.strip() for item in re.split(r'[\r\n,]+', str(raw_value)) if item.strip()]


def _get_query_terms(request, *names):
    terms = []
    for name in names:
        values = request.query_params.getlist(name)
        if not values:
            value = request.query_params.get(name)
            if value is not None:
                values = [value]
        terms.extend(_split_terms(values))
    seen = set()
    unique_terms = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)
    return unique_terms


def _get_csv_values(request, *names):
    values = []
    for name in names:
        current = request.query_params.getlist(name)
        if not current:
            value = request.query_params.get(name)
            if value is not None:
                current = [value]
        for item in current:
            values.extend([part.strip() for part in str(item).split(',') if part.strip()])
    seen = set()
    unique_values = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _parse_db_limit_offset(request, default_limit=100, max_limit=None):
    limit, offset, error_response = _parse_limit_offset(request, default_limit=default_limit, max_limit=max_limit)
    if error_response is not None:
        return None, None, error_response
    if limit is None:
        limit = max_limit
    return limit, offset, None


def _fetch_table_columns(table_name):
    quoted_table = _quote_identifier(table_name)
    if quoted_table is None:
        return None, Response(
            {
                'status': 'error',
                'message': 'Invalid database table name.',
                'table': table_name,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with connection.cursor() as cursor:
            cursor.execute(f'SHOW COLUMNS FROM {quoted_table}')
            rows = cursor.fetchall()
    except Exception:
        logger.exception('API database schema lookup failed')
        return None, Response(
            {
                'status': 'error',
                'message': 'Database table not found or not readable.',
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    columns = [row[0] for row in rows]
    return columns, None


def _fetch_rows(table_name, where_clauses=None, params=None, order_by=None, limit=100, offset=0):
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return None, None, error_response

    quoted_table = _quote_identifier(table_name)
    where_clauses = where_clauses or []
    params = params or []

    sql = f'SELECT * FROM {quoted_table}'
    if where_clauses:
        sql += ' WHERE ' + ' AND '.join(where_clauses)

    if order_by and order_by in columns:
        sql += f' ORDER BY {_quote_identifier(order_by)}'

    sql += f' LIMIT {int(limit)} OFFSET {int(offset)}'

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    except Exception:
        logger.exception('API database query failed')
        return columns, None, Response(
            {
                'status': 'error',
                'message': 'Database query failed.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = [dict(zip(columns, row)) for row in rows]
    return columns, data, None


def _column_like_condition(columns, candidate_columns, keyword, params):
    searchable_columns = [column for column in candidate_columns if column in columns]
    if not searchable_columns or not keyword:
        return None

    parts = []
    for column in searchable_columns:
        parts.append(f'{_quote_identifier(column)} LIKE %s')
        params.append(f'%{keyword}%')
    return '(' + ' OR '.join(parts) + ')'


def _database_response(resource, table_name, columns, data, limit, offset, filters=None):
    return Response(
        {
            'status': 'ok',
            'resource': resource,
            'source': 'mysql',
            'table': table_name,
            'columns': columns,
            'filters': filters or {},
            'limit': limit,
            'offset': offset,
            'returned_count': len(data),
            'data': data,
        },
        status=status.HTTP_200_OK,
    )


def _validate_species_for_table(species, allowed_species=None):
    species = str(species or '').strip()
    if not species:
        return None, Response(
            {
                'status': 'error',
                'message': 'Missing required parameter: species',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not SPECIES_CODE_RE.match(species):
        return None, Response(
            {
                'status': 'error',
                'message': 'Invalid species parameter. Only letters, numbers, underscores, hyphens and dots are allowed.',
                'species': species,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if allowed_species is not None and species not in allowed_species:
        return None, Response(
            {
                'status': 'error',
                'message': 'Invalid species parameter.',
                'species': species,
                'allowed_species': list(allowed_species),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return species, None


def _is_interpro_gene_id(term, species_code):
    return bool(term) and term.startswith(species_code) and re.fullmatch(r'[A-Za-z0-9_.-]+', term) is not None


@api_view(['GET'])
@permission_classes([AllowAny])
def interproscan_api(request):
    """
    Query InterProScan annotations from {species}_interproscan_table.

    Examples:
    /api/genomics/interproscan/?species=Aann&gene_id=Aann000001&database=Pfam
    /api/genomics/interproscan/?species=Aann&q=kinase&databases=Pfam,PANTHER
    """
    species, error_response = _validate_species_for_table(
        request.query_params.get('species') or request.query_params.get('sp_name'),
        allowed_species=INTERPROSCAN_SPECIES,
    )
    if error_response is not None:
        return error_response

    selected_databases = _get_csv_values(request, 'database', 'databases', 'analysis')
    if not selected_databases:
        selected_databases = list(INTERPROSCAN_DATABASES)

    invalid_databases = [db for db in selected_databases if db not in INTERPROSCAN_DATABASES]
    if invalid_databases:
        return Response(
            {
                'status': 'error',
                'message': 'Invalid database parameter.',
                'invalid_databases': invalid_databases,
                'allowed_databases': list(INTERPROSCAN_DATABASES),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    table_name = f'{species}_interproscan_table'
    terms = _get_query_terms(request, 'gene_id', 'gene_ids', 'q', 'keyword')
    terms = terms[:50]

    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []

    if 'analysis' in columns and selected_databases:
        placeholders = ','.join(['%s'] * len(selected_databases))
        where_clauses.append(f'{_quote_identifier("analysis")} IN ({placeholders})')
        params.extend(selected_databases)

    if terms:
        term_clauses = []
        for term in terms:
            if 'gene_id' in columns and _is_interpro_gene_id(term, species):
                term_clauses.append(f'{_quote_identifier("gene_id")} = %s')
                params.append(term)
            elif 'description' in columns:
                term_clauses.append(f'{_quote_identifier("description")} LIKE %s')
                params.append(f'%{term}%')
        if term_clauses:
            where_clauses.append('(' + ' OR '.join(term_clauses) + ')')

    columns, data, error_response = _fetch_rows(
        table_name,
        where_clauses=where_clauses,
        params=params,
        order_by='gene_id',
        limit=limit,
        offset=offset,
    )
    if error_response is not None:
        return error_response

    return _database_response(
        'interproscan',
        table_name,
        columns,
        data,
        limit,
        offset,
        filters={
            'species': species,
            'databases': selected_databases,
            'terms': terms,
        },
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def kegg_api(request):
    """
    Query KEGG annotations from kegg_table.

    Examples:
    /api/genomics/kegg/?species=Aann&gene_id=Aann000001
    /api/genomics/kegg/?species=Aann&q=K00001
    /api/genomics/kegg/?species=Aann&q=photosynthesis
    """
    species, error_response = _validate_species_for_table(
        request.query_params.get('species') or request.query_params.get('sp_name') or request.query_params.get('sp_data_1'),
    )
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    table_name = 'kegg_table'
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    if 'sp_name' in columns:
        where_clauses.append(f'{_quote_identifier("sp_name")} = %s')
        params.append(species)

    terms = _get_query_terms(request, 'gene_id', 'gene_ids', 'ko', 'q', 'keyword')
    terms = terms[:50]
    if terms:
        term_clauses = []
        for term in terms:
            if 'ko' in columns and term.startswith('K') and len(term) == 6:
                term_clauses.append(f'{_quote_identifier("ko")} = %s')
                params.append(term)
            elif 'gene_id' in columns and re.fullmatch(r'[A-Za-z0-9_.:-]+', term):
                term_clauses.append(f'{_quote_identifier("gene_id")} = %s')
                params.append(term)
                if 'definition' in columns:
                    term_clauses.append(f'{_quote_identifier("definition")} LIKE %s')
                    params.append(f'%{term}%')
            elif 'definition' in columns:
                term_clauses.append(f'{_quote_identifier("definition")} LIKE %s')
                params.append(f'%{term}%')
        if term_clauses:
            where_clauses.append('(' + ' OR '.join(term_clauses) + ')')

    columns, data, error_response = _fetch_rows(
        table_name,
        where_clauses=where_clauses,
        params=params,
        order_by='gene_id',
        limit=limit,
        offset=offset,
    )
    if error_response is not None:
        return error_response

    return _database_response(
        'kegg',
        table_name,
        columns,
        data,
        limit,
        offset,
        filters={'species': species, 'terms': terms},
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def regulatory_proteins_api(request):
    """
    Query regulatory protein / transcription factor annotations from TF_pfam_table.

    Examples:
    /api/genomics/regulatory-proteins/?species=Aann&type=TF&family=MYB
    /api/genomics/regulatory-proteins/?q=MYB&limit=100
    """
    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    table_name = 'TF_pfam_table'
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {}

    equality_params = {
        'species': request.query_params.get('species') or request.query_params.get('sp_name'),
        'type': request.query_params.get('type'),
        'family': request.query_params.get('family'),
        'gene_id': request.query_params.get('gene_id'),
        'tf_name': request.query_params.get('tf_name'),
        'hmm_acc': request.query_params.get('hmm_acc'),
        'hmm_name': request.query_params.get('hmm_name'),
    }
    for column, value in equality_params.items():
        value = str(value or '').strip()
        if value and column in columns:
            where_clauses.append(f'{_quote_identifier(column)} = %s')
            params.append(value)
            filters[column] = value

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _column_like_condition(
            columns,
            ('species', 'type', 'family', 'gene_id', 'tf_name', 'hmm_acc', 'hmm_name', 'clan'),
            keyword,
            params,
        )
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    columns, data, error_response = _fetch_rows(
        table_name,
        where_clauses=where_clauses,
        params=params,
        order_by='gene_id',
        limit=limit,
        offset=offset,
    )
    if error_response is not None:
        return error_response

    return _database_response('regulatory_proteins', table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def m6a_api(request):
    """
    Query m6A-related gene annotations from m6A_table.

    Examples:
    /api/genomics/m6a/?species=Aann&first_class=readers&hmm_id=YTH
    /api/genomics/m6a/?species=Aann&q=YTH
    """
    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    table_name = 'm6A_table'
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {}

    equality_params = {
        'sp_name': request.query_params.get('species') or request.query_params.get('sp_name') or request.query_params.get('query_genome'),
        'first_class': request.query_params.get('first_class'),
        'hmm_id': request.query_params.get('hmm_id') or request.query_params.get('second_class'),
        'gene_id': request.query_params.get('gene_id'),
        'pfam_id': request.query_params.get('pfam_id'),
        'second_class': request.query_params.get('second_class'),
        'clan': request.query_params.get('clan'),
    }
    for column, value in equality_params.items():
        value = str(value or '').strip()
        if value and column in columns:
            where_clauses.append(f'{_quote_identifier(column)} = %s')
            params.append(value)
            filters[column] = value

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _column_like_condition(
            columns,
            ('gene_id', 'sp_name', 'first_class', 'hmm_id', 'pfam_id', 'second_class', 'clan'),
            keyword,
            params,
        )
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    columns, data, error_response = _fetch_rows(
        table_name,
        where_clauses=where_clauses,
        params=params,
        order_by='gene_id',
        limit=limit,
        offset=offset,
    )
    if error_response is not None:
        return error_response

    return _database_response('m6a', table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def duplication_types_api(request):
    """
    Query gene duplication type records from Genetype_table.

    Examples:
    /api/genomics/duplication-types/?gene_id=Aann000001
    /api/genomics/duplication-types/?species=Aann&type=WGD
    """
    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    table_name = 'Genetype_table'
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {}

    species = (request.query_params.get('species') or request.query_params.get('sp_name') or '').strip()
    if species and 'sp_name' in columns:
        if not SPECIES_CODE_RE.match(species):
            return Response(
                {
                    'status': 'error',
                    'message': 'Invalid species parameter. Only letters, numbers, underscores, hyphens and dots are allowed.',
                    'species': species,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        where_clauses.append(f'{_quote_identifier("sp_name")} = %s')
        params.append(species)
        filters['species'] = species

    dup_type = (request.query_params.get('type') or request.query_params.get('duplication_type') or '').strip()
    if dup_type and 'type' in columns:
        where_clauses.append(f'{_quote_identifier("type")} = %s')
        params.append(dup_type)
        filters['type'] = dup_type

    terms = _get_query_terms(request, 'gene_id', 'gene_ids', 'gene', 'q')
    terms = terms[:50]
    if terms:
        term_clauses = []
        for term in terms:
            if 'gene1' in columns:
                term_clauses.append(f'{_quote_identifier("gene1")} = %s')
                params.append(term)
            if 'gene2' in columns:
                term_clauses.append(f'{_quote_identifier("gene2")} = %s')
                params.append(term)
        if term_clauses:
            where_clauses.append('(' + ' OR '.join(term_clauses) + ')')
        filters['terms'] = terms

    columns, data, error_response = _fetch_rows(
        table_name,
        where_clauses=where_clauses,
        params=params,
        order_by='gene1',
        limit=limit,
        offset=offset,
    )
    if error_response is not None:
        return error_response

    return _database_response('duplication_types', table_name, columns, data, limit, offset, filters=filters)

# -----------------------------------------------------------------------------
# Database-backed Multi-Omics APIs
# -----------------------------------------------------------------------------

def _require_table_column(table_name, columns, required_column):
    if required_column in columns:
        return None
    return Response(
        {
            'status': 'error',
            'message': 'Required column is missing from database table.',
            'table': table_name,
            'required_column': required_column,
            'columns': columns,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _case_insensitive_column(columns, *candidate_names):
    """Return the real column name matching one of the candidates, ignoring case."""
    lower_map = {str(column).lower(): column for column in columns}
    for name in candidate_names:
        matched = lower_map.get(str(name).lower())
        if matched:
            return matched
    return None


def _append_exact_filter(where_clauses, params, filters, columns, column_name, value, filter_name=None):
    value = str(value or '').strip()
    if not value:
        return
    real_column = _case_insensitive_column(columns, column_name)
    if not real_column:
        return
    where_clauses.append(f'{_quote_identifier(real_column)} = %s')
    params.append(value)
    filters[filter_name or real_column] = value


@api_view(['GET'])
@permission_classes([AllowAny])
def transcriptome_expression_api(request):
    """
    Query transcriptome expression records from {species}_express_table.

    Examples:
    /api/multiomics/transcriptome/expression/?species=Aann&gene_id=Aann000001&expression_index=TPM
    /api/multiomics/transcriptome/expression/?species=Aann&gene_ids=Aann000001,Aann000002&index=FPKM
    /api/multiomics/transcriptome/expression/?species=Aann&limit=20
    """
    species, error_response = _validate_species_for_table(
        request.query_params.get('species') or request.query_params.get('sp_name') or request.query_params.get('sp_data_1'),
    )
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    table_name = f'{species}_express_table'
    if _quote_identifier(table_name) is None:
        return Response(
            {
                'status': 'error',
                'message': 'Invalid expression table name.',
                'species': species,
                'table': table_name,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    gene_column = _case_insensitive_column(columns, 'geneid', 'gene_id')
    if not gene_column:
        return Response(
            {
                'status': 'error',
                'message': 'Could not find gene ID column in expression table.',
                'table': table_name,
                'expected_columns': ['geneid', 'gene_id'],
                'columns': columns,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    where_clauses = []
    params = []
    filters = {'species': species}

    expression_index = (
        request.query_params.get('expression_index')
        or request.query_params.get('index')
        or request.query_params.get('type')
        or ''
    ).strip()
    expression_column = _case_insensitive_column(columns, 'Express_index', 'expression_index')
    if expression_index and expression_column:
        where_clauses.append(f'{_quote_identifier(expression_column)} = %s')
        params.append(expression_index)
        filters['expression_index'] = expression_index

    terms = _get_query_terms(request, 'gene_id', 'gene_ids', 'geneid', 'geneids', 'gene', 'q')
    terms = [term for term in terms if re.fullmatch(r'[A-Za-z0-9_.:-]+', term)][:200]
    if terms:
        placeholders = ','.join(['%s'] * len(terms))
        where_clauses.append(f'{_quote_identifier(gene_column)} IN ({placeholders})')
        params.extend(terms)
        filters['gene_ids'] = terms

    columns, data, error_response = _fetch_rows(
        table_name,
        where_clauses=where_clauses,
        params=params,
        order_by=gene_column,
        limit=limit,
        offset=offset,
    )
    if error_response is not None:
        return error_response

    returned_gene_ids = {str(row.get(gene_column, '')) for row in data}
    not_found_gene_ids = [term for term in terms if term not in returned_gene_ids]

    response = _database_response(
        'transcriptome_expression',
        table_name,
        columns,
        data,
        limit,
        offset,
        filters=filters,
    )
    response.data['gene_column'] = gene_column
    response.data['expression_index_column'] = expression_column
    response.data['not_found_gene_ids'] = not_found_gene_ids
    return response


def _metabolomics_table_api(request, table_name, resource_name):
    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {}

    # The old pages search CID with LIKE; keep that behavior for API users.
    cid = (request.query_params.get('cid') or request.query_params.get('CID') or request.query_params.get('geneid') or '').strip()
    cid_column = _case_insensitive_column(columns, 'CID')
    if cid and cid_column:
        where_clauses.append(f'{_quote_identifier(cid_column)} LIKE %s')
        params.append(f'%{cid}%')
        filters['cid'] = cid

    equality_candidates = {
        'species': ('Species', 'species', 'sp_name'),
        'type': ('Type', 'type'),
        'cas': ('CAS', 'cas'),
        'formula': ('Formula', 'formula'),
        'ko': ('KO_Number', 'ko_number', 'KO', 'ko'),
        'gene_id': ('Gene_IDs', 'gene_ids', 'Gene_ID', 'gene_id'),
    }
    for filter_name, candidate_columns in equality_candidates.items():
        value = request.query_params.get(filter_name)
        if not value:
            continue
        real_column = _case_insensitive_column(columns, *candidate_columns)
        if real_column:
            where_clauses.append(f'{_quote_identifier(real_column)} LIKE %s')
            params.append(f'%{str(value).strip()}%')
            filters[filter_name] = str(value).strip()

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        # Use all text-like columns as searchable candidates; MySQL will cast non-text columns when needed.
        condition = _column_like_condition(columns, columns, keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_column = cid_column or (columns[0] if columns else None)
    columns, data, error_response = _fetch_rows(
        table_name,
        where_clauses=where_clauses,
        params=params,
        order_by=order_column,
        limit=limit,
        offset=offset,
    )
    if error_response is not None:
        return error_response

    return _database_response(resource_name, table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def metabolomics_plant_api(request):
    """
    Query plant metabolomics records from Metabolomics_plant.

    Examples:
    /api/multiomics/metabolomics/plant/?cid=5280443
    /api/multiomics/metabolomics/plant/?q=terpene&limit=20
    """
    return _metabolomics_table_api(request, 'Metabolomics_plant', 'metabolomics_plant')


@api_view(['GET'])
@permission_classes([AllowAny])
def metabolomics_scent_api(request):
    """
    Query floral scent metabolomics records from Metabolomics_scent.

    Examples:
    /api/multiomics/metabolomics/scent/?cid=5280443
    /api/multiomics/metabolomics/scent/?q=Helianthus&limit=20
    """
    return _metabolomics_table_api(request, 'Metabolomics_scent', 'metabolomics_scent')



# =================== Remaining Genomics / Geno-Syn API endpoints ===================

TE_JSON_DIR = Path(settings.BASE_DIR) / 'static' / 'TE_json'

HIERARCHICAL_ALIGNMENT_API_TABLES = {
    'Hean': 'Hierarchical_alignment_Hean_table',
    'Lssa_all': 'Hierarchical_alignment_Lssa_all_table',
    'Vivi': 'Hierarchical_alignment_Vivi_table',
    'Eupl': 'Hierarchical_alignment_Eupl_table',
}

# The current database uses a unified hierarchical gene table.
# The per-reference gene tables used by older model names may not exist on the server,
# so all reference values use the unified table and then apply filters where columns exist.
HIERARCHICAL_GENE_API_TABLES = {
    'Hean': 'Hierarchicalgene',
    'Lssa_all': 'Hierarchicalgene',
    'Vivi': 'Hierarchicalgene',
    'Eupl': 'Hierarchicalgene',
    'all': 'Hierarchicalgene',
}

HIERARCHICAL_REFERENCE_ALIASES = {
    'hean': 'Hean',
    'helianthus': 'Hean',
    'lssa': 'Lssa_all',
    'lssa_all': 'Lssa_all',
    'aria': 'Lssa_all',
    'arla': 'Lssa_all',
    'arctium': 'Lssa_all',
    'vivi': 'Vivi',
    'vitis': 'Vivi',
    'eupl': 'Eupl',
    'euplotidium': 'Eupl',
    'all': 'all',
}


def _normalize_hierarchical_reference(value, allow_all=False):
    raw_value = str(value or '').strip()
    if not raw_value:
        return 'all' if allow_all else 'Hean', None

    key = re.sub(r'[^A-Za-z0-9_]', '', raw_value).lower()
    reference = HIERARCHICAL_REFERENCE_ALIASES.get(key)
    if reference is None or (reference == 'all' and not allow_all):
        allowed = sorted(set(HIERARCHICAL_REFERENCE_ALIASES.keys()))
        return None, Response(
            {
                'status': 'error',
                'message': 'Invalid reference parameter.',
                'reference': raw_value,
                'allowed_references': allowed,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return reference, None


def _safe_table_species(value, parameter_name='species'):
    species = str(value or '').strip()
    if not species:
        return None, Response(
            {
                'status': 'error',
                'message': f'Missing required parameter: {parameter_name}',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not SPECIES_CODE_RE.match(species):
        return None, Response(
            {
                'status': 'error',
                'message': f'Invalid {parameter_name} parameter. Only letters, numbers, underscores, hyphens and dots are allowed.',
                parameter_name: species,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return species, None


def _truthy(value):
    return str(value or '').strip().lower() in ('1', 'true', 'yes', 'y', 'on')


def _add_equal_filter(where_clauses, params, columns, column, value, filters=None, filter_name=None):
    value = str(value or '').strip()
    if value and column in columns:
        where_clauses.append(f'{_quote_identifier(column)} = %s')
        params.append(value)
        if filters is not None:
            filters[filter_name or column] = value


def _add_in_filter(where_clauses, params, columns, column, values, filters=None, filter_name=None):
    clean_values = [str(value).strip() for value in values if str(value).strip()]
    if clean_values and column in columns:
        placeholders = ','.join(['%s'] * len(clean_values))
        where_clauses.append(f'{_quote_identifier(column)} IN ({placeholders})')
        params.extend(clean_values)
        if filters is not None:
            filters[filter_name or column] = clean_values


def _search_any_columns(columns, candidate_columns, keyword, params):
    if not keyword:
        return None
    if candidate_columns == '__all__':
        candidate_columns = columns
    return _column_like_condition(columns, candidate_columns, keyword, params)


def _json_payload_records(payload):
    records, _ = _extract_records(payload)
    if records is not None:
        return records
    if isinstance(payload, dict):
        return [payload]
    return [{'value': payload}]


def _load_records_from_te_file(file_path):
    payload, error_response = _load_json_file(file_path)
    if error_response is not None:
        return None, error_response
    return _json_payload_records(payload), None


def _safe_te_species_dir(species):
    species = str(species or '').strip()
    if not species:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Missing required parameter: species',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', species):
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid species parameter. Only letters, numbers, underscores, hyphens and dots are allowed.',
                'species': species,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    base_dir = TE_JSON_DIR.resolve()
    species_dir = (base_dir / species).resolve()
    try:
        species_dir.relative_to(base_dir)
    except ValueError:
        return None, None, Response(
            {
                'status': 'error',
                'message': 'Invalid species path.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return species, species_dir, None


@api_view(['GET'])
@permission_classes([AllowAny])
def transposable_elements_species_api(request):
    """
    List species directories under static/TE_json/.

    Example:
    /api/genomics/transposable-elements/species/
    """
    data = []
    base_dir = TE_JSON_DIR.resolve()
    if base_dir.is_dir():
        for species_dir in sorted(base_dir.iterdir(), key=lambda item: item.name.lower()):
            if not species_dir.is_dir():
                continue
            json_files = sorted(species_dir.glob('*.json'))
            data.append({
                'species': species_dir.name,
                'json_file_count': len(json_files),
                'files': [file_path.name for file_path in json_files[:200]],
                'query_url': _api_url(request, 'genomics/transposable-elements/', {'species': species_dir.name}),
            })

    return Response(
        {
            'status': 'ok',
            'resource': 'transposable_elements_species',
            'count': len(data),
            'data': data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def transposable_elements_api(request):
    """
    Query TE JSON files under static/TE_json/{species}/.

    Examples:
    /api/genomics/transposable-elements/?species=Artemisia_annua&limit=100
    /api/genomics/transposable-elements/?species=Artemisia_annua&q=LTR
    /api/genomics/transposable-elements/?species=Artemisia_annua&filename=xxx.json
    """
    species, species_dir, error_response = _safe_te_species_dir(request.query_params.get('species'))
    if error_response is not None:
        return error_response

    if not species_dir.is_dir():
        return Response(
            {
                'status': 'error',
                'message': 'TE species directory not found.',
                'species': species,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    filename = str(request.query_params.get('filename') or request.query_params.get('file') or '').strip()
    json_files = []
    if filename:
        if (len(filename) > 255 or any(ord(char) < 32 or ord(char) == 127 for char in filename)
                or '/' in filename or '\\' in filename or filename.startswith('.')):
            return Response(
                {
                    'status': 'error',
                    'message': 'Invalid filename parameter.',
                    'filename': filename,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not filename.endswith('.json'):
            filename = f'{filename}.json'
        file_path = (species_dir / filename).resolve()
        try:
            file_path.relative_to(species_dir)
        except ValueError:
            return Response({'status': 'error', 'message': 'Invalid TE file path.'}, status=status.HTTP_400_BAD_REQUEST)
        if not file_path.is_file():
            return Response(
                {
                    'status': 'error',
                    'message': 'TE JSON file not found.',
                    'species': species,
                    'filename': filename,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        json_files = [file_path]
    else:
        json_files = sorted(species_dir.glob('*.json'))

    # Inspect metadata for the entire selection before opening any content.
    max_files = int(getattr(settings, 'AGRP_API_TE_MAX_FILES', 64))
    max_bytes = int(getattr(settings, 'AGRP_API_TE_MAX_BYTES', 16 * 1024 * 1024))
    if len(json_files) > max_files:
        return Response({'status': 'error', 'message': 'Too many TE files for one online query. Specify filename.'}, status=413)
    total_bytes = 0
    for selected_file in json_files:
        try:
            selected_file.resolve().relative_to(species_dir)
            total_bytes += selected_file.stat().st_size
        except (ValueError, OSError, RuntimeError):
            return Response({'status': 'error', 'message': 'TE resource is unavailable.'}, status=400)
        if total_bytes > max_bytes:
            return Response({'status': 'error', 'message': 'Selected TE data exceeds the online query size limit. Request a smaller file.', 'max_bytes': max_bytes}, status=413)

    limit, offset, error_response = _parse_limit_offset(request, default_limit=100, max_limit=1000)
    if error_response is not None:
        return error_response

    query = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    records = []
    warnings = []
    for file_path in json_files:
        file_records, error_response = _load_records_from_te_file(file_path)
        if error_response is not None:
            warnings.append({'file': file_path.name, 'message': 'Could not read JSON file.'})
            continue
        for record in file_records:
            if isinstance(record, dict):
                item = dict(record)
                item.setdefault('_source_file', file_path.name)
            else:
                item = {'value': record, '_source_file': file_path.name}
            records.append(item)

    filtered_records = _filter_records(records, query)
    if limit is None:
        page_records = filtered_records[offset:]
    else:
        page_records = filtered_records[offset:offset + limit]

    return Response(
        {
            'status': 'ok',
            'resource': 'transposable_elements',
            'source': 'static_json',
            'species': species,
            'file_count': len(json_files),
            'total_count': len(records),
            'filtered_count': len(filtered_records),
            'limit': limit,
            'offset': offset,
            'returned_count': len(page_records),
            'query': query,
            'warnings': warnings,
            'data': page_records,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def genosyn_blocks_api(request):
    """
    Query syntenic block records from {query_genome}_blocksyn_block.

    Examples:
    /api/genosyn/blocks/?query_genome=Aann&reference_genome=Chla&limit=50
    /api/genosyn/blocks/?query_genome=Aann&query_chromosome=1&reference_chromosome=2
    """
    query_genome, error_response = _safe_table_species(
        request.query_params.get('query_genome') or request.query_params.get('species') or request.query_params.get('sp1'),
        parameter_name='query_genome',
    )
    if error_response is not None:
        return error_response

    table_name = f'{query_genome}_blocksyn_block'
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {'query_genome': query_genome}

    _add_equal_filter(where_clauses, params, columns, 'Query_Genome', query_genome, filters)
    _add_equal_filter(
        where_clauses,
        params,
        columns,
        'Reference_Genome',
        request.query_params.get('reference_genome') or request.query_params.get('subject_genome') or request.query_params.get('sp2'),
        filters,
    )
    _add_in_filter(where_clauses, params, columns, 'Query_Chromosome', _get_csv_values(request, 'query_chromosome', 'query_chromosomes', 'chr1'), filters)
    _add_in_filter(where_clauses, params, columns, 'Reference_Chromosome', _get_csv_values(request, 'reference_chromosome', 'reference_chromosomes', 'chr2'), filters)
    _add_equal_filter(where_clauses, params, columns, 'unique_id', request.query_params.get('unique_id') or request.query_params.get('block_id'), filters)

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _search_any_columns(columns, '__all__', keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_by = 'unique_id' if 'unique_id' in columns else (columns[0] if columns else None)
    columns, data, error_response = _fetch_rows(table_name, where_clauses, params, order_by=order_by, limit=limit, offset=offset)
    if error_response is not None:
        return error_response

    return _database_response('genosyn_blocks', table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def genosyn_block_details_api(request):
    """
    Query syntenic gene-pair details from {query_genome}_blocksyn_pair.

    Examples:
    /api/genosyn/block-details/?query_genome=Aann&unique_id=Aann_xxx
    /api/genosyn/block-details/?query_genome=Aann&gene_id=Aann000001
    """
    query_genome, error_response = _safe_table_species(
        request.query_params.get('query_genome') or request.query_params.get('species') or request.query_params.get('sp1'),
        parameter_name='query_genome',
    )
    if error_response is not None:
        return error_response

    table_name = f'{query_genome}_blocksyn_pair'
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {'query_genome': query_genome}

    _add_equal_filter(where_clauses, params, columns, 'unique_id', request.query_params.get('unique_id') or request.query_params.get('block_id'), filters)

    terms = _get_query_terms(request, 'gene_id', 'gene_ids')[:50]
    if terms:
        gene_columns = [column for column in ('Gene1', 'Gene2', 'gene1', 'gene2', 'id1', 'id2') if column in columns]
        if gene_columns:
            term_conditions = []
            for term in terms:
                sub_conditions = []
                for column in gene_columns:
                    sub_conditions.append(f'{_quote_identifier(column)} = %s')
                    params.append(term)
                term_conditions.append('(' + ' OR '.join(sub_conditions) + ')')
            where_clauses.append('(' + ' OR '.join(term_conditions) + ')')
            filters['gene_ids'] = terms

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _search_any_columns(columns, '__all__', keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_by = 'unique_id' if 'unique_id' in columns else (columns[0] if columns else None)
    columns, data, error_response = _fetch_rows(table_name, where_clauses, params, order_by=order_by, limit=limit, offset=offset)
    if error_response is not None:
        return error_response

    return _database_response('genosyn_block_details', table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def hierarchical_alignments_api(request):
    """
    Query hierarchical alignment tables for MGAs.

    Examples:
    /api/genosyn/hierarchical-alignments/?reference=Hean&limit=50
    /api/genosyn/hierarchical-alignments/?reference=Vivi&q=Aann000001
    """
    reference, error_response = _normalize_hierarchical_reference(request.query_params.get('reference') or request.query_params.get('ref'))
    if error_response is not None:
        return error_response

    table_name = HIERARCHICAL_ALIGNMENT_API_TABLES[reference]
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {'reference': reference}

    hhh_number = str(request.query_params.get('hhh_number') or request.query_params.get('row_id') or '').strip()
    if hhh_number and 'hhh_number' in columns:
        if not re.fullmatch(r'\d+', hhh_number):
            return Response({'status': 'error', 'message': 'Invalid hhh_number parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        where_clauses.append(f'{_quote_identifier("hhh_number")} = %s')
        params.append(int(hhh_number))
        filters['hhh_number'] = int(hhh_number)

    keyword = (request.query_params.get('q') or request.query_params.get('gene_id') or request.query_params.get('keyword') or '').strip()
    if keyword:
        searchable_columns = [column for column in columns if column != 'hhh_number']
        condition = _column_like_condition(columns, searchable_columns, keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_by = 'hhh_number' if 'hhh_number' in columns else (columns[0] if columns else None)
    columns, data, error_response = _fetch_rows(table_name, where_clauses, params, order_by=order_by, limit=limit, offset=offset)
    if error_response is not None:
        return error_response

    return _database_response('hierarchical_alignments', table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def hierarchical_genes_api(request):
    """
    Query hierarchical gene coordinate tables.

    Examples:
    /api/genosyn/hierarchical-genes/?gene_id=Aann000001
    /api/genosyn/hierarchical-genes/?reference=Hean&species=Aann
    """
    reference, error_response = _normalize_hierarchical_reference(request.query_params.get('reference') or request.query_params.get('ref') or 'all', allow_all=True)
    if error_response is not None:
        return error_response

    table_name = HIERARCHICAL_GENE_API_TABLES[reference]
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {'reference': reference}

    if reference != 'all':
        # Apply a reference filter only when the unified table has a suitable column.
        # If not, still return data from the unified table instead of failing with a missing-table error.
        for column in ('reference', 'ref', 'ref_genome', 'Reference', 'source'):
            if column in columns:
                where_clauses.append(f'{_quote_identifier(column)} = %s')
                params.append(reference)
                break

    species = str(request.query_params.get('species') or request.query_params.get('sp_name') or '').strip()
    if species:
        for column in ('sp_name', 'species'):
            if column in columns:
                where_clauses.append(f'{_quote_identifier(column)} = %s')
                params.append(species)
                filters['species'] = species
                break

    chromosome = str(request.query_params.get('chromosome') or request.query_params.get('chr') or '').strip()
    if chromosome:
        for column in ('chromosome', 'chr_num'):
            if column in columns:
                where_clauses.append(f'{_quote_identifier(column)} = %s')
                params.append(chromosome)
                filters['chromosome'] = chromosome
                break

    terms = _get_query_terms(request, 'gene_id', 'gene_ids', 'new_gene', 'old_gene')[:50]
    if terms:
        gene_columns = [column for column in ('gene_id', 'new_gene', 'old_gene') if column in columns]
        if gene_columns:
            term_conditions = []
            for term in terms:
                sub_conditions = []
                for column in gene_columns:
                    sub_conditions.append(f'{_quote_identifier(column)} = %s')
                    params.append(term)
                term_conditions.append('(' + ' OR '.join(sub_conditions) + ')')
            where_clauses.append('(' + ' OR '.join(term_conditions) + ')')
            filters['gene_ids'] = terms

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _search_any_columns(columns, '__all__', keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_by = 'gene_id' if 'gene_id' in columns else ('new_gene' if 'new_gene' in columns else (columns[0] if columns else None))
    columns, data, error_response = _fetch_rows(table_name, where_clauses, params, order_by=order_by, limit=limit, offset=offset)
    if error_response is not None:
        return error_response

    return _database_response('hierarchical_genes', table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def evogenes_api(request):
    """
    Query evolutionary event genes from Event_genes_table.

    Examples:
    /api/genosyn/evogenes/?gene_id=Aann000001
    /api/genosyn/evogenes/?event=ECH
    """
    table_name = 'Event_genes_table'
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {}

    event = str(request.query_params.get('event') or '').strip()
    if event:
        for column in ('event', 'Event'):
            if column in columns:
                where_clauses.append(f'{_quote_identifier(column)} = %s')
                params.append(event)
                filters['event'] = event
                break

    terms = _get_query_terms(request, 'gene_id', 'gene_ids', 'gene')[:50]
    if terms:
        gene_columns = [column for column in ('gene_id1', 'gene_id2', 'gene1', 'gene2', 'Gene1', 'Gene2') if column in columns]
        if gene_columns:
            term_conditions = []
            for term in terms:
                sub_conditions = []
                for column in gene_columns:
                    sub_conditions.append(f'{_quote_identifier(column)} = %s')
                    params.append(term)
                term_conditions.append('(' + ' OR '.join(sub_conditions) + ')')
            where_clauses.append('(' + ' OR '.join(term_conditions) + ')')
            filters['gene_ids'] = terms

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _search_any_columns(columns, '__all__', keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_by = 'hhh_number' if 'hhh_number' in columns else (columns[0] if columns else None)
    columns, data, error_response = _fetch_rows(table_name, where_clauses, params, order_by=order_by, limit=limit, offset=offset)
    if error_response is not None:
        return error_response

    return _database_response('evogenes', table_name, columns, data, limit, offset, filters=filters)


def _simple_gene_table_api(request, table_name, resource_name, species_columns=('query_genome', 'sp_name', 'species'), function_columns=('function_name', 'function')):
    columns, error_response = _fetch_table_columns(table_name)
    if error_response is not None:
        return error_response

    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    filters = {}

    species = str(request.query_params.get('species') or request.query_params.get('query_genome') or request.query_params.get('sp_name') or '').strip()
    if species:
        for column in species_columns:
            if column in columns:
                where_clauses.append(f'{_quote_identifier(column)} = %s')
                params.append(species)
                filters['species'] = species
                break

    terms = _get_query_terms(request, 'gene_id', 'gene_ids')[:50]
    if terms and 'gene_id' in columns:
        placeholders = ','.join(['%s'] * len(terms))
        where_clauses.append(f'{_quote_identifier("gene_id")} IN ({placeholders})')
        params.extend(terms)
        filters['gene_ids'] = terms

    function = str(request.query_params.get('function') or request.query_params.get('function_name') or '').strip()
    if function:
        function_conditions = []
        for column in function_columns:
            if column in columns:
                function_conditions.append(f'{_quote_identifier(column)} LIKE %s')
                params.append(f'%{function}%')
        if function_conditions:
            where_clauses.append('(' + ' OR '.join(function_conditions) + ')')
            filters['function'] = function

    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _search_any_columns(columns, '__all__', keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_by = 'gene_id' if 'gene_id' in columns else (columns[0] if columns else None)
    columns, data, error_response = _fetch_rows(table_name, where_clauses, params, order_by=order_by, limit=limit, offset=offset)
    if error_response is not None:
        return error_response

    return _database_response(resource_name, table_name, columns, data, limit, offset, filters=filters)


@api_view(['GET'])
@permission_classes([AllowAny])
def gene_families_api(request):
    """
    Query function gene family records from function_GF_table.

    Examples:
    /api/genosyn/gene-families/?species=Aann&gene_id=Aann000001
    /api/genosyn/gene-families/?species=Aann&function=floral
    """
    return _simple_gene_table_api(request, 'function_GF_table', 'gene_families')


@api_view(['GET'])
@permission_classes([AllowAny])
def rubber_genes_api(request):
    """
    Query rubber-related gene family records from rubber_GF_table.

    Example:
    /api/genosyn/rubber-genes/?gene_id=Tako000001
    """
    return _simple_gene_table_api(request, 'rubber_GF_table', 'rubber_genes')


@api_view(['GET'])
@permission_classes([AllowAny])
def inulin_genes_api(request):
    """
    Query inulin-related gene family records from Inulin_GF_table.

    Example:
    /api/genosyn/inulin-genes/?gene_id=Cich000001
    """
    return _simple_gene_table_api(request, 'Inulin_GF_table', 'inulin_genes')


@api_view(['GET'])
@permission_classes([AllowAny])
def orthologous_api(request):
    """
    Query orthologous groups and related genes.

    Examples:
    /api/genosyn/orthologous/?orthogroup=OG0000001
    /api/genosyn/orthologous/?gene_id=Aann000001&include_genes=1
    /api/genosyn/orthologous/?q=OG0001&limit=20
    """
    limit, offset, error_response = _parse_db_limit_offset(request)
    if error_response is not None:
        return error_response

    og_type = str(request.query_params.get('og_type') or '').strip().lower()
    use_block = og_type == 'block'
    genes_table = 'block_Orthofinder_genes_table' if use_block else 'Orthofinder_genes_table'
    summary_table = 'block_Orthogroups_number' if use_block else 'Orthofinder_num_table'

    gene_id = str(request.query_params.get('gene_id') or request.query_params.get('gene') or '').strip()
    orthogroup = str(request.query_params.get('orthogroup') or request.query_params.get('og') or '').strip()

    filters = {'og_type': 'block' if use_block else 'normal'}

    if gene_id and not orthogroup:
        columns, error_response = _fetch_table_columns(genes_table)
        if error_response is not None:
            return error_response
        where_clauses = []
        params = []
        if 'gene_id' in columns:
            where_clauses.append(f'{_quote_identifier("gene_id")} = %s')
            params.append(gene_id)
        elif 'Gene_ID' in columns:
            where_clauses.append(f'{_quote_identifier("Gene_ID")} = %s')
            params.append(gene_id)
        else:
            return Response(
                {
                    'status': 'error',
                    'message': 'Could not find a gene_id column in orthologous genes table.',
                    'table': genes_table,
                    'columns': columns,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        columns, gene_rows, error_response = _fetch_rows(genes_table, where_clauses, params, limit=1, offset=0)
        if error_response is not None:
            return error_response
        if gene_rows:
            for candidate in ('orthogroup', 'Orthogroup'):
                if candidate in gene_rows[0]:
                    orthogroup = gene_rows[0][candidate]
                    break
        filters['gene_id'] = gene_id

    if orthogroup:
        filters['orthogroup'] = orthogroup
        response_payload = {
            'status': 'ok',
            'resource': 'orthologous',
            'source': 'mysql',
            'filters': filters,
            'orthogroup': orthogroup,
        }

        summary_columns, error_response = _fetch_table_columns(summary_table)
        if error_response is not None:
            return error_response
        summary_where = []
        summary_params = []
        for column in ('orthogroup', 'Orthogroup'):
            if column in summary_columns:
                summary_where.append(f'{_quote_identifier(column)} = %s')
                summary_params.append(orthogroup)
                break
        summary_columns, summary_data, error_response = _fetch_rows(summary_table, summary_where, summary_params, limit=10, offset=0)
        if error_response is not None:
            return error_response
        response_payload['summary_table'] = summary_table
        response_payload['summary_columns'] = summary_columns
        response_payload['summary'] = summary_data

        # Also expose block summary when the normal table is queried, because the old page shows both.
        if not use_block:
            block_columns, block_error = _fetch_table_columns('block_Orthogroups_number')
            if block_error is None:
                block_where = []
                block_params = []
                for column in ('orthogroup', 'Orthogroup'):
                    if column in block_columns:
                        block_where.append(f'{_quote_identifier(column)} = %s')
                        block_params.append(orthogroup)
                        break
                block_columns, block_summary, block_error = _fetch_rows('block_Orthogroups_number', block_where, block_params, limit=10, offset=0)
                if block_error is None:
                    response_payload['block_summary_table'] = 'block_Orthogroups_number'
                    response_payload['block_summary_columns'] = block_columns
                    response_payload['block_summary'] = block_summary

        include_genes = _truthy(request.query_params.get('include_genes')) or bool(gene_id) or bool(request.query_params.get('species'))
        if include_genes:
            gene_columns, error_response = _fetch_table_columns(genes_table)
            if error_response is not None:
                return error_response
            gene_where = []
            gene_params = []
            for column in ('orthogroup', 'Orthogroup'):
                if column in gene_columns:
                    gene_where.append(f'{_quote_identifier(column)} = %s')
                    gene_params.append(orthogroup)
                    break
            species = str(request.query_params.get('species') or request.query_params.get('sp_name') or '').strip()
            if species:
                for column in ('species', 'sp_name'):
                    if column in gene_columns:
                        gene_where.append(f'{_quote_identifier(column)} = %s')
                        gene_params.append(species)
                        filters['species'] = species
                        break
            gene_columns, genes_data, error_response = _fetch_rows(genes_table, gene_where, gene_params, order_by='gene_id', limit=limit, offset=offset)
            if error_response is not None:
                return error_response
            response_payload['genes_table'] = genes_table
            response_payload['genes_columns'] = gene_columns
            response_payload['limit'] = limit
            response_payload['offset'] = offset
            response_payload['returned_gene_count'] = len(genes_data)
            response_payload['genes'] = genes_data

        return Response(response_payload, status=status.HTTP_200_OK)

    # No orthogroup or gene_id: list/search summary table.
    columns, error_response = _fetch_table_columns(summary_table)
    if error_response is not None:
        return error_response

    where_clauses = []
    params = []
    keyword = (request.query_params.get('q') or request.query_params.get('keyword') or '').strip()
    if keyword:
        condition = _search_any_columns(columns, '__all__', keyword, params)
        if condition:
            where_clauses.append(condition)
            filters['q'] = keyword

    order_by = 'orthogroup' if 'orthogroup' in columns else ('Orthogroup' if 'Orthogroup' in columns else (columns[0] if columns else None))
    columns, data, error_response = _fetch_rows(summary_table, where_clauses, params, order_by=order_by, limit=limit, offset=offset)
    if error_response is not None:
        return error_response

    return _database_response('orthologous', summary_table, columns, data, limit, offset, filters=filters)

# =================== End remaining Genomics / Geno-Syn API endpoints ===================
