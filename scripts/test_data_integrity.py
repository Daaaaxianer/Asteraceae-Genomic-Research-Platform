"""Regression checks for source-schema and published-resource edge cases."""
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browse.data_integrity import expression_projection, metabolite_image_path, available_analysis_links


class DataIntegrityTests(unittest.TestCase):
    def test_expression_two_and_seventeen_samples_keep_units_and_zero(self):
        for size in (2, 17):
            samples = ['SRR' + str(i) for i in range(size)]
            columns = ['geneid'] + samples + ['Express_index']
            values = [0] + list(range(1, size))
            headers, rows, heatmap = expression_projection(columns, [('g1', *values, 'FPKM')])
            self.assertEqual(headers, ['Gene ID', 'Unit'] + samples)
            self.assertEqual(rows, [['g1', 'FPKM'] + values])
            self.assertEqual(heatmap[0][0], 0)
            self.assertTrue(all(math.isfinite(n) for n in heatmap[0]))

    def test_unit_location_is_not_assumed(self):
        headers, rows, heatmap = expression_projection(
            ['Express_index', 'SRR2', 'geneid', 'SRR1'], [('TPM', 3, 'g1', None)])
        self.assertEqual(rows, [['g1', 'TPM', 3, None]])
        self.assertEqual(heatmap, [[2, None]])

    def test_structure_reuses_same_cid_and_keeps_unknown_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'static/image/pubchem/plant/CID_440967.png'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'known fixture')
            self.assertEqual(metabolite_image_path(directory, 'CID_440967', 440967, 'scent'),
                             'image/pubchem/plant/CID_440967.png')
            self.assertEqual(metabolite_image_path(directory, 'NA', 440967, 'plant'),
                             'image/pubchem/plant/CID_440967.png')
            self.assertEqual(metabolite_image_path(directory, 'NA', 999, 'plant'), '')
            self.assertEqual(metabolite_image_path(directory, 'CID_440967', 999, 'plant'), '')
            self.assertEqual(metabolite_image_path(directory, '../../secret', '', 'plant'), '')

    def test_analysis_links_reflect_files_and_preserve_method(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'collinearscan').mkdir()
            (root / 'collinearscan/known.txt').touch()
            (root / 'mcscanx').mkdir()
            (root / 'mcscanx/missing.txt').touch()
            payload = {'data': [['<a href="../../static/collinearscan/known.txt">Download</a>',
                                 '<a href="../../static/collinearscan/missing.txt">Download</a>']]}
            result = available_analysis_links(payload, root)
            self.assertIn('href="/static/collinearscan/known.txt"', result['data'][0][0])
            self.assertEqual(result['data'][0][1], '<span class="text-muted">Not available</span>')
            self.assertIn('../../static/', payload['data'][0][0])


if __name__ == '__main__':
    unittest.main()
