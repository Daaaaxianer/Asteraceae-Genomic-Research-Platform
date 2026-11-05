"""Regression probes use temporary inputs; no biological jobs or database."""
import ast
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from tools import command_safety as safe
from api import compute_limits as limits
from api.shared_limits import acquire_slot


PROJECT = Path(__file__).resolve().parent.parent


def selected_functions(relative, names, namespace):
    tree = ast.parse((PROJECT / relative).read_text(encoding='utf-8'))
    nodes = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    selected = [nodes[name] for name in names]
    for node in selected:
        node.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
                 relative, 'exec'), namespace)


class ToolSecurityTests(SimpleTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.job = self.root / 'file_keep/123456789'
        self.job.mkdir(parents=True)
        self.override = override_settings(BASE_DIR=self.root, AGRP_API_STATE_DIR=self.root / '.limits')
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.calls = []

        def keep_file(na, c):
            (self.job / na.name).write_bytes(b'A\tB\tC\n')

        ns = {name: getattr(safe, name) for name in (
            'execute_argv', 'choice', 'identifier', 'iq_model', 'bootstrap', 'columns',
            'PARAAT_FORMATS', 'KAKS_METHODS', 'DIAMOND_SENSITIVITY', 'ToolInputError')}
        ns.update(os=os, tempfile=tempfile, subprocess=subprocess, path_get=str(self.root),
                  name_set=lambda: '123456789', keep_file=keep_file,
                  render=lambda *a, **k: HttpResponse('result'),
                  HttpResponse=HttpResponse, JsonResponse=JsonResponse,
                  zip_file=lambda *a, **k: HttpResponse('download'),
                  mcscanx_zip_file=lambda *a: HttpResponse('download'),
                  kaks_calculator_zip_file=lambda *a: HttpResponse('download'),
                  get_tool_path=lambda name: name,
                  parse_standard_gff_to_custom=lambda *a: None)
        helpers = ('mcscanx_run_tools', 'paraat_run_tools', 'kaks_calculator_run_tools',
                   'iqtree_run_tools', 'find_replace_run_tools', 'extr_row_run')
        selected_functions('LGBP/tools.py', helpers, ns)
        self.views = ('mcscanx_run', 'paraat_run', 'kaks_calculator_run', 'iq_tree_run',
                      'find_replace_run', 'extract_column_run', 'blast_run', 'diamond_run',
                      'cds2geno_dotplot_view')
        selected_functions('tools/views.py', self.views + ('run_command',), ns)
        self.ns = ns

    def call(self, name, post, files):
        uploads = {key: SimpleNamespace(name=value, chunks=lambda: [b'>fixture\nACGT\n'])
                   for key, value in files.items()}
        request = SimpleNamespace(method='POST', POST=post, FILES=uploads)
        return safe.guarded_tool_view(self.ns[name])(request)

    def test_original_injection_fields_are_rejected_or_treated_as_data(self):
        marker = '1; __ASTERACEAE_AUDIT_MARKER__; #'
        cases = [
            ('iq_tree_run', {'patten': marker, 'bs_num': '1000'}, {'file': 'x.phy'}),
            ('iq_tree_run', {'patten': 'GTR', 'bs_num': marker}, {'file': 'x.phy'}),
            ('paraat_run', {'patten': marker}, {'homologs': 'x', 'cds': 'y', 'pep': 'z'}),
            ('kaks_calculator_run', {'patten': marker}, {'kaks': 'x'}),
            ('extract_column_run', {'row_num': marker}, {'row': 'x.tsv'}),
            ('blast_run', {'patten': marker}, {'file1': 'x', 'file2': 'y'}),
            ('diamond_run', {'patten': marker}, {'file1': 'x', 'file2': 'y'}),
            ('diamond_run', {'patten': 'blastp', 'sensitive': marker}, {'file1': 'x', 'file2': 'y'}),
            ('cds2geno_dotplot_view', {'target_abbr': marker}, {'target_genome': 'x', 'ref_cds': 'y', 'ref_gff': 'z'}),
            ('cds2geno_dotplot_view', {'ref_abbr': marker}, {'target_genome': 'x', 'ref_cds': 'y', 'ref_gff': 'z'}),
        ]
        with patch.object(safe, 'run_tool') as run:
            for name, post, files in cases:
                with self.subTest(view=name, post=post):
                    self.assertEqual(self.call(name, post, files).status_code, 400)
            run.assert_not_called()

    def test_uploaded_filenames_do_not_enter_commands(self):
        with patch.object(safe, 'run_tool') as run:
            response = self.call('mcscanx_run', {}, {'file1': 'x;marker;#.blast', 'file2': 'y.gff'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue((self.job / 'mcscanx_input.blast').is_file())
            response = self.call('extract_column_run', {'row_num': '1-2'}, {'row': 'x;marker;#.tsv'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue((self.job / 'input.tsv').is_file())
            self.assertNotIn('marker', repr(run.call_args_list))

    def test_species_path_escape_rejected_before_any_write(self):
        for field in ('target_abbr', 'ref_abbr'):
            for value in ('../outside', '/tmp/outside', 'C:\\outside', 'a/b'):
                with self.subTest(field=field, value=value), patch.object(safe, 'run_tool') as run:
                    with patch('tools.command_safety.subprocess.Popen') as process:
                        response = self.call('cds2geno_dotplot_view', {field: value},
                                             {'target_genome': 'x', 'ref_cds': 'y', 'ref_gff': 'z'})
                    self.assertEqual(response.status_code, 400)
                    process.assert_not_called()
                    run.assert_not_called()

    def test_sed_semantics_and_delimiter_injection_neutralization(self):
        # Real sed on a tiny controlled file; no biological program is launched.
        (self.job / 'upload.txt').write_text("scaffold_1\na/b\n", encoding='utf-8')
        safe.find_replace('123456789', 'scaffold_', 'Chr')
        self.assertEqual((self.job / 'result.txt').read_text(), 'Chr1\na/b\n')
        safe.find_replace('123456789', 'a/b', "x'; marker; #")
        self.assertEqual((self.job / 'result.txt').read_text(), "scaffold_1\nx'; marker; #\n")
        safe.find_replace('123456789', 'a', 'x/e; marker')
        self.assertIn('x/e; marker/b', (self.job / 'result.txt').read_text())

    def test_cut_ranges_preserve_results(self):
        (self.job / 'input.tsv').write_text('a\tb\tc\td\n')
        safe.extract_columns('123456789', '1,3-', 'input', 'tsv')
        self.assertEqual((self.job / 'input.new.tsv').read_text(), 'a\tc\td\n')

    def test_invalid_column_ranges_rejected(self):
        for value in ('0', '9-1', '--help', '1; echo', '1\n2', '1 2', ''):
            with self.subTest(value=value), self.assertRaises(safe.ToolInputError):
                safe.columns(value)

    def test_job_symlink_cannot_escape_result_root(self):
        (self.root / 'outside').mkdir()
        (self.root / 'file_keep/link').symlink_to(self.root / 'outside', target_is_directory=True)
        with self.assertRaises(safe.ToolInputError):
            safe.job_directory('link')

    def test_runner_uses_argv_and_timeout(self):
        with patch.object(safe.subprocess, 'Popen') as popen:
            process = popen.return_value
            process.communicate.return_value = (b'ok', b'')
            process.returncode = 0
            safe.run_tool('sed', ['-e', "s/a/x';marker;#/g", '--', 'upload.txt'], cwd=self.job)
            args, kwargs = popen.call_args
            self.assertIsInstance(args[0], list)
            self.assertIs(kwargs['shell'], False)
            self.assertEqual(args[0][2], "s/a/x';marker;#/g")
            process.communicate.assert_called_once_with(timeout=3600)

    def test_runner_timeout_kills_group(self):
        with patch.object(safe.subprocess, 'Popen') as popen, patch.object(safe.os, 'killpg') as kill:
            process = popen.return_value
            process.communicate.side_effect = [subprocess.TimeoutExpired('fixture', 1), (b'', b'')]
            with self.assertRaises(subprocess.TimeoutExpired):
                safe.run_tool('sed', ['--version'])
            kill.assert_called_once()

    def test_string_commands_rejected(self):
        with self.assertRaises(safe.ToolInputError):
            safe.execute_argv('blastn; marker')

    def test_valid_legacy_arguments_preserved(self):
        (self.job / 'result').mkdir()
        (self.job / 'result/example.axt').write_bytes(b'alignment\n')
        with patch.object(safe, 'run_tool') as run:
            safe.paraat('123456789', 'axt')
            self.assertEqual((self.job / 'result.axt').read_bytes(), b'alignment\n')
            self.assertIn('processors.txt', run.call_args.args[1])
            safe.kaks('123456789', 'NG')
            self.assertEqual(run.call_args.args[:2], ('KaKs_Calculator', ['-i', 'kaks.axt', '-o', 'result_kaks.txt', '-m', 'NG']))
            safe.iqtree('123456789', 'GTR+G', '1000')
            self.assertIn('GTR+G', run.call_args.args[1])

    def test_valid_alignment_views_pass_complete_argument_lists(self):
        with patch.object(safe, 'run_tool') as run:
            for view in ('blast_run', 'diamond_run'):
                response = self.call(view, {'patten': 'blastp'}, {'file1': 'db.fa', 'file2': 'query.fa'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(run.call_args.args[0], 'blastp' if view == 'blast_run' else 'diamond')
                self.assertIsInstance(run.call_args.args[1], list)
                self.assertIn('2', run.call_args.args[1])
            response = self.call('cds2geno_dotplot_view', {'target_abbr': 'Aann', 'ref_abbr': 'Ecan'},
                                 {'target_genome': 'genome.fa', 'ref_cds': 'ref.fa', 'ref_gff': 'ref.gff'})
            self.assertEqual(response.status_code, 400)  # Stub produces no BLAST hits.
            self.assertEqual(run.call_args.args[0], 'blastn')


class ComputeLimitsTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.override = override_settings(BASE_DIR=self.root, AGRP_API_STATE_DIR=self.root / '.limits',
                                          AGRP_COMPUTE_CONCURRENCY=1, AGRP_COMPUTE_PER_CALLER=1)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def test_global_running_slot_and_release(self):
        leases = limits.computation_leases()
        try:
            with self.assertRaises(limits.ComputeBusy):
                limits.computation_leases()
        finally:
            for lease in leases:
                lease.close()
        again = limits.computation_leases()
        for lease in again:
            lease.close()

    @override_settings(AGRP_COMPUTE_SUBMISSIONS_PER_MINUTE=1)
    def test_browse_submission_rate_and_get_unchanged(self):
        middleware = limits.ComputeSubmissionMiddleware(lambda request: HttpResponse('ok'))
        factory = RequestFactory()
        self.assertEqual(middleware(factory.post('/browse/kegg_index')).status_code, 200)
        limited = middleware(factory.post('/browse/kegg_index'))
        self.assertEqual(limited.status_code, 429)
        self.assertIn('Retry-After', limited)
        self.assertEqual(middleware(factory.get('/browse/kegg_index')).status_code, 200)

    def test_worker_keeps_slot_after_launcher_returns(self):
        status = self.root / 'status.json'
        status.write_text('{"status":"queued"}')
        # Capture and reap the harmless supervisor after verifying lock handoff.
        original = subprocess.Popen
        children = []
        def start(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child
        with patch('api.compute_limits.subprocess.Popen', side_effect=start):
            limits.launch_background([sys.executable, '-c', 'import time; time.sleep(0.3)'],
                                     cwd=self.root, log_path=self.root / 'log', status_path=status)
        try:
            with self.assertRaises(limits.ComputeBusy):
                limits.computation_leases()
        finally:
            children[0].wait(timeout=5)
        leases = limits.computation_leases()
        for lease in leases:
            lease.close()

    def test_background_timeout_updates_status(self):
        runner = PROJECT / 'api/background_runner.py'
        status = self.root / 'status.json'
        status.write_text('{"status":"running"}')
        command = [sys.executable, '-c', 'import time; time.sleep(20)']
        result = subprocess.run([sys.executable, str(runner), '1', str(status), json.dumps(command)], timeout=5)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(json.loads(status.read_text())['status'], 'error')
        self.assertIn('timed out', json.loads(status.read_text())['message'])

    def test_background_timeout_stops_descendants(self):
        if os.name == 'nt':
            self.skipTest('POSIX process group regression')
        runner = PROJECT / 'api/background_runner.py'
        status = self.root / 'status.json'
        status.write_text('{}')
        pidfile = self.root / 'descendant.pid'
        child = ("import subprocess,sys,time,pathlib; "
                 "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)']); "
                 "pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(20)")
        command = [sys.executable, '-c', child, str(pidfile)]
        result = subprocess.run([sys.executable, str(runner), '1', str(status), json.dumps(command)], timeout=5)
        self.assertEqual(result.returncode, 124)
        pid = int(pidfile.read_text())
        proc = Path('/proc') / str(pid) / 'stat'
        # A stopped descendant can briefly remain as a zombie awaiting init.
        self.assertTrue(not proc.exists() or proc.read_text().split()[2] == 'Z')
