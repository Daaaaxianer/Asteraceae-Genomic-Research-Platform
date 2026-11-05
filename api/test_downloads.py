import json
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse
from unittest.mock import patch
import io


class PublicDownloadTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data = self.root / 'static/example_file'
        data.mkdir(parents=True)
        (data / 'example.txt').write_bytes(b'0123456789')
        self.settings = override_settings(BASE_DIR=self.root, AGRP_API_STATE_DIR=self.root / '.limits')
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def test_example_download_uses_api_and_preserves_bytes(self):
        response = self.client.get('/api/download/public/static/example_file/example.txt')
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'0123456789')
            self.assertIn('attachment', response['Content-Disposition'])
        finally:
            response.close()

    def test_inline_public_data_uses_api_without_attachment(self):
        response = self.client.get('/api/files/public/static/example_file/example.txt')
        try:
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('attachment', response.get('Content-Disposition', ''))
        finally:
            response.close()

    def test_range_download_returns_only_requested_bytes(self):
        response = self.client.get('/api/download/public/static/example_file/example.txt', HTTP_RANGE='bytes=2-4')
        try:
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response['Content-Range'], 'bytes 2-4/10')
            self.assertEqual(b''.join(response.streaming_content), b'234')
        finally:
            response.close()

    def test_head_does_not_return_file_body(self):
        response = self.client.head('/api/download/public/static/example_file/example.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Length'], '10')
        response.close()

    def test_symlink_cannot_escape_published_root(self):
        (self.root / 'private.txt').write_text('not-public')
        (self.root / 'static/example_file/link.txt').symlink_to(self.root / 'private.txt')
        response = self.client.get('/api/download/public/static/example_file/link.txt')
        self.assertEqual(response.status_code, 404)

    def test_source_code_is_not_a_published_download(self):
        private = self.root / 'static/example_file/config.py'
        private.write_text('private-password')
        response = self.client.get('/api/download/public/static/example_file/config.py')
        self.assertEqual(response.status_code, 404)

    def test_browser_generated_export_is_audited_api_download(self):
        upload = SimpleUploadedFile('selected.tsv', b'name\tvalue\na\t1\n', content_type='text/tab-separated-values')
        response = self.client.post('/api/download/export/', {'file': upload})
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'name\tvalue\na\t1\n')
            self.assertIn('X-Request-ID', response)
        finally:
            response.close()

    @override_settings(AGRP_API_EXPORT_MAX_BYTES=8)
    def test_browser_export_has_a_size_budget(self):
        upload = SimpleUploadedFile('selected.tsv', b'x' * 9)
        response = self.client.post('/api/download/export/', {'file': upload})
        self.assertEqual(response.status_code, 413)

    @override_settings(AGRP_API_EXPORT_MAX_BYTES=8)
    def test_oversized_export_is_rejected_before_multipart_parsing(self):
        response = self.client.generic('POST', '/api/download/export/', b'abc',
                                       content_type='application/octet-stream', CONTENT_LENGTH='1000000')
        self.assertEqual(response.status_code, 413)

    def test_foreign_origin_cannot_submit_export_with_browser_credentials(self):
        response = self.client.post('/api/download/export/', {'file': SimpleUploadedFile('a.txt', b'x')}, HTTP_ORIGIN='https://foreign.invalid')
        self.assertEqual(response.status_code, 403)

    def test_legacy_download_name_resolves_to_api(self):
        self.assertEqual(reverse('fixture_download'), '/api/download/tools/fixture-download')

    def test_existing_download_logic_can_only_be_called_through_api(self):
        old = self.client.get('/tools/fixture-download')
        self.assertEqual(old.status_code, 404)
        response = self.client.get('/api/download/tools/fixture-download')
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'0123456789')
        finally:
            response.close()

    def test_page_download_link_and_form_are_canonical_api_urls(self):
        response = self.client.get('/fixture-page')
        html = response.content.decode()
        self.assertIn('/api/download/public/static/example_file/example.txt', html)
        self.assertIn('/api/download/tools/fixture-run', html)
        self.assertIn('/static/css/style.css', html)
        self.assertIn('/static/js/download-gateway.js', html)

    def test_file_parameters_are_not_corrupted_when_links_are_rewritten(self):
        html = self.client.get('/fixture-page').content.decode()
        self.assertIn('/api/download/tools/fixture-download?file=/srv/file_keep/job/result.zip', html)
        self.assertNotIn('/srv/api/files/result/', html)

    def page_attributes(self, markup):
        from api.download_routing import rewrite_response
        elements = []

        class PageParser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                elements.append((tag, dict(attrs)))

        response = rewrite_response(HttpResponse(markup), RequestFactory().get('/fixture-page'))
        PageParser().feed(response.content.decode())
        return elements

    def test_existing_api_download_links_preserve_query_parameters(self):
        from api import views
        for species, file_type, filename in [('Amar', 'pep', 'Amar.pep'), ('Amtr', 'gff', 'Amtr.new.gff')]:
            with self.subTest(species=species, file_type=file_type):
                (self.root / filename).write_bytes(b'genome-file-content')
                elements = self.page_attributes(
                    '<a href="/api/download/genome/?species=%s&amp;type=%s">Download</a>'
                    % (species, file_type))
                href = elements[0][1]['href']
                self.assertEqual(parse_qs(urlsplit(href).query), {'species': [species], 'type': [file_type]})
                with patch.object(views, 'GENOME_FILE_DIR', self.root):
                    response = self.client.get(href)
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(b''.join(response.streaming_content), b'genome-file-content')
                finally:
                    response.close()

    def test_html_links_and_forms_preserve_query_entities(self):
        elements = self.page_attributes(
            '<a href="https://example.org/?first=1&amp;second=A%26B">Reference</a>'
            '<form action="/api/download/export/?first=1&amp;second=A%26B" method="post"></form>')
        for tag, attrs in elements:
            value = attrs['action' if tag == 'form' else 'href']
            self.assertEqual(parse_qs(urlsplit(value).query), {'first': ['1'], 'second': ['A&B']})

    def test_private_image_query_entities_are_not_double_escaped(self):
        elements = self.page_attributes(
            '<img src="/api/files/result/missing/plot.svg?first=1&amp;second=A%26B">')
        self.assertEqual(parse_qs(urlsplit(elements[0][1]['src']).query),
                         {'first': ['1'], 'second': ['A&B']})

    def test_preview_urls_are_not_mistaken_for_download_buttons(self):
        payload = self.client.get('/api/test-preview-urls/').json()
        self.assertEqual(payload['image_url'], '/api/files/public/static/Orthogroup_tree_png/tree.png')
        self.assertEqual(payload['download_url'], '/api/download/public/static/Orthogroup_tree_png/tree.png')

    def test_public_file_downloads_share_the_download_rate(self):
        statuses = []
        for _ in range(6):
            response = self.client.get('/api/download/public/static/example_file/example.txt')
            statuses.append(response.status_code)
            response.close()
        self.assertEqual(statuses, [200, 200, 200, 200, 200, 429])

    def test_embedded_viewer_files_use_a_fixed_published_root(self):
        base = self.root / 'jbrowse'
        base.mkdir()
        (base / 'config.json').write_bytes(b'{"tracks":[]}')
        with override_settings(AGRP_JBROWSE_ROOT=base):
            response = self.client.get('/api/files/public/jbrowse/config.json')
            try:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b''.join(response.streaming_content), b'{"tracks":[]}')
            finally:
                response.close()

    def test_embedded_viewer_search_indexes_can_be_read_through_api(self):
        base = self.root / 'jbrowse'
        base.mkdir()
        for suffix in ('.ix', '.ixx'):
            (base / ('search' + suffix)).write_bytes(b'index-data')
            with override_settings(AGRP_JBROWSE_ROOT=base):
                response = self.client.get('/api/files/public/jbrowse/search' + suffix)
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(b''.join(response.streaming_content), b'index-data')
                finally:
                    response.close()

    def test_embedded_report_download_is_streamed_through_api(self):
        with patch('api.downloads.HTTPConnection') as connection:
            upstream = connection.return_value.getresponse.return_value
            upstream.status = 200
            upstream.getheader.side_effect = lambda name, default=None: {'Content-Type': 'text/plain', 'Content-Disposition': 'attachment; filename="report.tsv"'}.get(name, default)
            data = io.BytesIO(b'report-result')
            upstream.read.side_effect = data.read
            response = self.client.get('/api/download/service/sequenceserver/download/' + 'a' * 32 + '.tsv')
            try:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b''.join(response.streaming_content), b'report-result')
            finally:
                response.close()
        self.assertIn('X-Request-ID', response)

    def test_service_gateway_cannot_proxy_arbitrary_paths(self):
        with patch('api.downloads.HTTPConnection') as connection:
            response = self.client.get('/api/download/service/sequenceserver/etc/passwd')
        self.assertEqual(response.status_code, 404)
        connection.assert_not_called()


class OwnedResultTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = override_settings(BASE_DIR=self.root, AGRP_API_STATE_DIR=self.root / '.limits')
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.client = Client(raise_request_exception=False)

    def create_job(self):
        response = self.client.post('/api/test-create-job/')
        self.assertEqual(response.status_code, 200)
        return response.json()['path']

    def test_creator_can_download_own_result(self):
        relative = self.create_job()
        response = self.client.get('/api/download/result/' + relative)
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'private-result')
        finally:
            response.close()

    def test_other_browser_cannot_download_or_claim_existing_result(self):
        relative = self.create_job()
        other = Client(raise_request_exception=False)
        for _ in range(2):
            response = other.get('/api/download/result/' + relative)
            self.assertEqual(response.status_code, 404)

    def test_unowned_old_result_is_not_automatically_claimed(self):
        job = self.root / 'file_keep' / '123456789'
        job.mkdir(parents=True)
        (job / 'result.tsv').write_text('old-private-result')
        response = self.client.get('/api/download/result/123456789/result.tsv')
        self.assertEqual(response.status_code, 404)

    def test_private_preview_requires_the_same_owner(self):
        relative = self.create_job()
        response = self.client.get('/api/files/result/' + relative)
        self.assertEqual(response.status_code, 200)
        response.close()
        other = Client(raise_request_exception=False)
        self.assertEqual(other.get('/api/files/result/' + relative).status_code, 404)

    def test_task_status_does_not_leak_to_another_browser(self):
        relative = self.create_job()
        job_id = relative.split('/')[0]
        response = self.client.get('/tools/fixture-status/' + job_id)
        self.assertEqual(response.status_code, 200)
        other = Client(raise_request_exception=False)
        self.assertEqual(other.get('/tools/fixture-status/' + job_id).status_code, 404)

    def test_result_cookie_is_http_only_and_stable(self):
        self.client.get('/other-page')
        self.assertIn('agrp_download_owner', self.client.cookies)
        cookie = self.client.cookies['agrp_download_owner']
        self.assertTrue(cookie['httponly'])
        value = cookie.value
        self.client.get('/other-page')
        self.assertEqual(self.client.cookies['agrp_download_owner'].value, value)

    def test_result_credential_allows_access_from_another_browser(self):
        relative = self.create_job()
        response = self.client.get('/api/download/result/' + relative)
        try:
            self.assertIn('X-AGRP-Result-Link', response)
            link = response['X-AGRP-Result-Link']
        finally:
            response.close()
        other = Client(raise_request_exception=False)
        shared = other.get(link)
        try:
            self.assertEqual(shared.status_code, 200)
            self.assertEqual(b''.join(shared.streaming_content), b'private-result')
        finally:
            shared.close()

    def test_wrong_result_credential_is_rejected(self):
        relative = self.create_job()
        other = Client(raise_request_exception=False)
        response = other.get('/api/download/result/' + relative, {'access_token': '0' * 64})
        self.assertEqual(response.status_code, 404)

    def test_result_link_does_not_authorize_other_uploaded_files(self):
        relative = self.create_job()
        response = self.client.get('/api/download/result/' + relative)
        link = response['X-AGRP-Result-Link']
        response.close()
        other = Client(raise_request_exception=False)
        response = other.get(link.replace('/result.tsv?', '/input.fasta?'))
        self.assertEqual(response.status_code, 404)

    def test_real_tool_allocator_registers_new_result_access(self):
        response = self.client.post('/api/test-allocate-job/')
        self.assertEqual(response.status_code, 200)
        download = self.client.get('/api/download/result/' + response.json()['path'])
        try:
            self.assertEqual(download.status_code, 200)
            self.assertEqual(b''.join(download.streaming_content), b'allocated-result')
        finally:
            download.close()
