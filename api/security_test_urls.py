from django.urls import include, path
from django.http import HttpResponse
from django.http import JsonResponse
from django.conf import settings
from pathlib import Path
import uuid


def fixture_job(request):
    from api.download_access import register_job_directory
    job_id = uuid.uuid4().hex
    job = Path(settings.BASE_DIR) / 'file_keep' / job_id
    job.mkdir(parents=True)
    (job / 'result.tsv').write_bytes(b'private-result')
    (job / 'input.fasta').write_bytes(b'private-upload')
    register_job_directory(job)
    return JsonResponse({'path': job_id + '/result.tsv'})


def fixture_download(request):
    from api.downloads import public_file
    return public_file(request, 'static', 'example_file/example.txt')


def fixture_run(request):
    return fixture_download(request)


def fixture_status(request, place):
    return JsonResponse({'status': 'done', 'private': 'task-details'})


def fixture_page(request):
    return HttpResponse('<html><head></head><body><link href="/static/css/style.css">'
                        '<a download href="/static/example_file/example.txt">Download</a>'
                        '<a href="/tools/fixture-download?file=/srv/file_keep/job/result.zip">Result</a>'
                        '<form action="/tools/fixture-run" method="post"></form></body></html>')


def fixture_preview_urls(request):
    return JsonResponse({'image_url': '/static/Orthogroup_tree_png/tree.png',
                         'download_url': '/static/Orthogroup_tree_png/tree.png'})


def fixture_real_allocator(request):
    from LGBP import tools
    from unittest.mock import patch
    with patch.object(tools, 'path_get', str(settings.BASE_DIR)):
        job_id = tools.name_set()
    result = Path(settings.BASE_DIR) / 'file_keep' / job_id / 'result.tsv'
    result.write_text('allocated-result')
    return JsonResponse({'path': job_id + '/result.tsv'})


urlpatterns = [path('api/', include('api.urls')), path('other-page', lambda request: HttpResponse('other-page')),
               path('api/test-create-job/', fixture_job),
               path('api/test-allocate-job/', fixture_real_allocator),
               path('api/test-preview-urls/', fixture_preview_urls),
               path('tools/fixture-download', fixture_download, name='fixture_download'),
               path('tools/fixture-run', fixture_run, name='fixture_run'),
               path('tools/fixture-status/<str:place>', fixture_status),
               path('fixture-page', fixture_page)]

from api.download_routing import build_download_patterns
urlpatterns.append(path('api/download/', include(build_download_patterns(urlpatterns))))
