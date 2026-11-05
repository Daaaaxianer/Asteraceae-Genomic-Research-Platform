import json
import multiprocessing
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from django.http import FileResponse
from django.core.cache import cache
from django.test import Client, SimpleTestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from api import views
from api.access_control import get_client_ip, get_request_access
from api.middleware import DownloadConcurrencyLimitMiddleware
from api.throttles import AGRPIPRateThrottle


def throttle_in_child(state_dir):
    with override_settings(AGRP_API_STATE_DIR=state_dir):
        req = APIRequestFactory().get('/api/download/genome/', REMOTE_ADDR='192.0.2.71')
        return AGRPIPRateThrottle().allow_request(req, None)


def download_in_child(state_dir):
    with override_settings(AGRP_API_STATE_DIR=state_dir):
        middleware = DownloadConcurrencyLimitMiddleware(lambda request: FileResponse(
            open(Path(state_dir) / 'fixture', 'rb')))
        response = middleware(APIRequestFactory().get('/api/download/genome/', REMOTE_ADDR='192.0.2.73'))
        try:
            return response.status_code
        finally:
            response.close()


class APISecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        cache.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_override = override_settings(AGRP_API_STATE_DIR=self.temp.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def request(self, path='/api/genomics/kegg/', **params):
        return Request(self.factory.get(path, params, REMOTE_ADDR='192.0.2.71'))

    def test_public_limit_cannot_exceed_access_tier(self):
        self.assertEqual(views._parse_db_limit_offset(self.request(limit=1000))[0], 100)

    def test_full_export_aliases_are_bounded(self):
        for raw in ['all', 'none', '0']:
            with self.subTest(raw=raw):
                self.assertEqual(views._parse_limit_offset(self.request(limit=raw))[0], 100)

    def test_trusted_tier_receives_configured_limit(self):
        with override_settings(AGRP_API_TRUSTED_IPS={'192.0.2.71'}):
            self.assertEqual(views._parse_db_limit_offset(self.request(limit=2000))[0], 2000)

    def test_excessive_offset_is_rejected(self):
        result = views._parse_limit_offset(self.request(offset=10**30))
        self.assertIsNotNone(result[2])
        self.assertEqual(result[2].status_code, 400)

    def test_untrusted_peer_cannot_spoof_cloudflare_or_whitelist(self):
        req = self.factory.get('/api/ping/', REMOTE_ADDR='192.0.2.71',
                               HTTP_CF_CONNECTING_IP='198.51.100.99',
                               HTTP_X_FORWARDED_FOR='198.51.100.99')
        with override_settings(AGRP_API_TRUSTED_IPS={'198.51.100.99'}):
            self.assertEqual(get_client_ip(req), '192.0.2.71')
            self.assertEqual(get_request_access(req)['tier'], 'public')

    def test_local_proxy_uses_verified_right_hand_chain(self):
        req = self.factory.get('/api/whoami/', REMOTE_ADDR='127.0.0.1',
                               HTTP_X_FORWARDED_FOR='198.51.100.99, 192.0.2.71',
                               HTTP_CF_CONNECTING_IP='198.51.100.99')
        self.assertEqual(get_client_ip(req), '192.0.2.71')

    def test_cloudflare_chain_preserves_real_client(self):
        req = self.factory.get('/api/whoami/', REMOTE_ADDR='127.0.0.1',
                               HTTP_X_FORWARDED_FOR='192.0.2.71, 104.23.166.136',
                               HTTP_CF_CONNECTING_IP='192.0.2.71')
        self.assertEqual(get_client_ip(req), '192.0.2.71')

    def test_null_filename_returns_validation_error(self):
        _, error = views._validate_transcriptome_json_filename('audit\x00')
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)

    def test_missing_json_does_not_disclose_absolute_path(self):
        _, response = views._load_json_file(Path(self.temp.name) / 'missing.json')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.temp.name, json.dumps(response.data))

    def test_database_failure_does_not_disclose_raw_exception(self):
        with patch('api.views.connection') as connection:
            connection.cursor.side_effect = RuntimeError('private-database-host')
            _, response = views._fetch_table_columns('Aann_express_table')
        self.assertNotIn('private-database-host', json.dumps(response.data))
        self.assertNotIn('error', response.data)

    def test_json_size_is_checked_before_decode(self):
        path = Path(self.temp.name) / 'large.json'
        path.write_bytes(b'x' * 1025)
        with override_settings(AGRP_API_JSON_MAX_BYTES=1024):
            _, response = views._load_json_file(path)
        self.assertEqual(response.status_code, 413)

    def test_te_combined_budget_is_enforced_before_any_decode(self):
        root = Path(self.temp.name) / 'TE'
        species = root / 'Aann'
        species.mkdir(parents=True)
        for name in ['a.json', 'b.json']:
            (species / name).write_text(' ' * 600)
        with patch.object(views, 'TE_JSON_DIR', root), override_settings(AGRP_API_TE_MAX_BYTES=1024):
            response = views.transposable_elements_api(self.factory.get(
                '/api/genomics/transposable-elements/', {'species': 'Aann', 'limit': 1}))
        self.assertEqual(response.status_code, 413)

    def test_small_te_query_still_filters_and_paginates(self):
        root = Path(self.temp.name) / 'TE'
        species = root / 'Aann'
        species.mkdir(parents=True)
        (species / 'a.json').write_text(json.dumps([{'name': 'LTR1'}, {'name': 'DNA'}]))
        (species / 'b.json').write_text(json.dumps([{'name': 'LTR2'}]))
        with patch.object(views, 'TE_JSON_DIR', root):
            response = views.transposable_elements_api(self.factory.get(
                '/api/genomics/transposable-elements/', {'species': 'Aann', 'q': 'LTR', 'limit': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filtered_count'], 2)
        self.assertEqual(response.data['returned_count'], 1)
        self.assertEqual(response.data['data'][0]['name'], 'LTR1')

    def test_file_download_content_is_preserved(self):
        root = Path(self.temp.name)
        (root / 'Aann.lens').write_bytes(b'chr1\t123\n')
        with patch.object(views, 'GENOME_FILE_DIR', root):
            response = views.genome_file_download(self.factory.get(
                '/api/download/genome/', {'species': 'Aann', 'type': 'lens'}))
            try:
                self.assertEqual(b''.join(response.streaming_content), b'chr1\t123\n')
                self.assertIn('Aann.lens', response['Content-Disposition'])
            finally:
                response.close()

    def test_rate_limit_is_shared_across_workers(self):
        req = self.factory.get('/api/download/genome/', REMOTE_ADDR='192.0.2.71')
        for _ in range(5):
            self.assertTrue(AGRPIPRateThrottle().allow_request(req, None))
        with multiprocessing.get_context('spawn').Pool(1) as pool:
            self.assertFalse(pool.apply(throttle_in_child, (self.temp.name,)))

    def test_threaded_requests_do_not_lose_rate_counts(self):
        def run(_):
            req = self.factory.get('/api/download/genome/', REMOTE_ADDR='192.0.2.72')
            return AGRPIPRateThrottle().allow_request(req, None)
        with ThreadPoolExecutor(max_workers=12) as pool:
            self.assertEqual(sum(pool.map(run, range(30))), 5)

    def test_streaming_download_holds_and_releases_concurrency_slots(self):
        def response(_):
            return FileResponse(open(Path(self.temp.name) / 'fixture', 'rb'))
        (Path(self.temp.name) / 'fixture').write_bytes(b'data')
        middleware = DownloadConcurrencyLimitMiddleware(response)
        req = self.factory.get('/api/download/genome/', REMOTE_ADDR='192.0.2.73')
        first, second = middleware(req), middleware(req)
        try:
            blocked = middleware(req)
            self.assertEqual(blocked.status_code, 429)
            first.close()
            again = middleware(req)
            self.assertEqual(again.status_code, 200)
            again.close()
        finally:
            first.close()
            second.close()

    def test_download_concurrency_is_shared_across_processes(self):
        path = Path(self.temp.name) / 'fixture'
        path.write_bytes(b'data')
        middleware = DownloadConcurrencyLimitMiddleware(lambda request: FileResponse(open(path, 'rb')))
        req = self.factory.get('/api/download/genome/', REMOTE_ADDR='192.0.2.73')
        first, second = middleware(req), middleware(req)
        try:
            with multiprocessing.get_context('spawn').Pool(1) as pool:
                self.assertEqual(pool.apply(download_in_child, (self.temp.name,)), 429)
        finally:
            first.close()
            second.close()

    def test_unknown_api_exception_does_not_render_debug_page(self):
        client = Client(raise_request_exception=False)
        with patch.object(views, '_safe_resolve', side_effect=RuntimeError('private-service-secret')):
            response = client.get('/api/multiomics/transcriptome/sample/', {'filename': 'a'})
        self.assertEqual(response.status_code, 500)
        self.assertTrue(response['Content-Type'].startswith('application/json'))
        self.assertNotIn(b'private-service-secret', response.content)
        self.assertNotIn(b'Traceback', response.content)

    @override_settings(AGRP_API_REQUIRE_EDGE=True)
    def test_origin_api_requests_are_rejected_even_with_forged_headers(self):
        response = self.client.get('/api/ping/', REMOTE_ADDR='192.0.2.73',
                                   HTTP_CF_CONNECTING_IP='192.0.2.71',
                                   HTTP_X_FORWARDED_FOR='192.0.2.71, 104.23.166.136',
                                   HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 403)

    @override_settings(AGRP_API_REQUIRE_EDGE=True, AGRP_API_REQUIRE_HTTPS=True)
    def test_verified_https_edge_request_is_allowed(self):
        response = self.client.get('/api/ping/', REMOTE_ADDR='127.0.0.1',
                                   HTTP_CF_CONNECTING_IP='192.0.2.71',
                                   HTTP_X_FORWARDED_FOR='192.0.2.71, 104.23.166.136',
                                   HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 200)

    @override_settings(AGRP_API_REQUIRE_EDGE=True, AGRP_API_REQUIRE_HTTPS=True)
    def test_plain_http_edge_request_is_rejected(self):
        response = self.client.get('/api/ping/', REMOTE_ADDR='127.0.0.1',
                                   HTTP_CF_CONNECTING_IP='192.0.2.71',
                                   HTTP_X_FORWARDED_FOR='192.0.2.71, 104.23.166.136',
                                   HTTP_X_FORWARDED_PROTO='http')
        self.assertEqual(response.status_code, 426)

    def test_static_genome_alias_redirects_to_controlled_download(self):
        response = self.client.get('/static/Species_data/Aann.new.gff')
        self.assertEqual(response.status_code, 404)

    def test_static_ancestral_alias_redirects_to_controlled_download(self):
        response = self.client.get('/static/ancestral_data/AAKI/AAKI.cds')
        self.assertEqual(response.status_code, 404)

    def test_large_query_is_rejected_before_view(self):
        response = self.client.get('/api/ping/', {'q': 'x' * 10000})
        self.assertEqual(response.status_code, 414)

    def test_audit_log_has_request_id_but_no_key_or_query_content(self):
        with self.assertLogs('agrp.api', level='INFO') as log:
            response = self.client.get('/api/ping/', {'q': 'private-query-content'},
                                       HTTP_X_AGRP_API_KEY='private-raw-key')
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-Request-ID', response)
        self.assertIn(response['X-Request-ID'], '\n'.join(log.output))
        self.assertNotIn('private-query-content', '\n'.join(log.output))
        self.assertNotIn('private-raw-key', '\n'.join(log.output))

    def test_non_api_pages_are_not_restricted(self):
        with override_settings(AGRP_API_REQUIRE_EDGE=True):
            response = self.client.get('/other-page')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'other-page')

    @override_settings(AGRP_API_REQUIRE_EDGE=True)
    def test_nginx_direct_request_cannot_forge_an_edge_hop(self):
        response = self.client.get('/api/ping/', REMOTE_ADDR='127.0.0.1',
                                   HTTP_CF_CONNECTING_IP='198.51.100.99',
                                   HTTP_X_FORWARDED_FOR='198.51.100.99, 104.23.166.136, 192.0.2.71',
                                   HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 403)

    def test_te_directory_listing_cannot_read_outside_symlinks(self):
        root = Path(self.temp.name) / 'TE'
        species = root / 'Aann'
        species.mkdir(parents=True)
        outside = Path(self.temp.name) / 'private.json'
        outside.write_text('[{"secret":"outside-data"}]')
        (species / 'linked.json').symlink_to(outside)
        with patch.object(views, 'TE_JSON_DIR', root):
            response = views.transposable_elements_api(self.factory.get(
                '/api/genomics/transposable-elements/', {'species': 'Aann'}))
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('outside-data', json.dumps(response.data))

    def test_api_404_is_json_even_when_global_debug_is_enabled(self):
        response = self.client.get('/api/nonexistent-audit-route/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response['Content-Type'].startswith('application/json'))
        self.assertNotIn(b'urlpatterns', response.content)

    def test_resource_guard_failure_returns_safe_unavailable_response(self):
        with patch('api.security.acquire_slot', side_effect=OSError('private-path')):
            response = self.client.get('/api/ping/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'private-path', response.content)
        self.assertIn('Retry-After', response)
