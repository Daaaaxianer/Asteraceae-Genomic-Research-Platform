"""Focused checks for real schema and gene-association edge cases."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browse.agrp_switch import exact_token, expression_data, ko_terms, named_rows


class ExpressionFixture:
    def __init__(self, sample_names):
        self.columns = ['geneid'] + sample_names + ['Express_index']
        self.rows = [dict(zip(self.columns, ['Aann1g00001'] + list(range(len(sample_names))) + ['FPKM'])),
                     dict(zip(self.columns, ['Aann1g00001'] + [0] * len(sample_names) + ['TPM']))]

    def schema(self, table):
        return self.columns

    def select(self, table, where, params):
        assert where == '`geneid` = %s' and params == ['Aann1g00001']
        return self.rows


class SwitchAssociationTests(unittest.TestCase):
    def test_gene_membership_does_not_match_longer_identifiers(self):
        self.assertTrue(exact_token("['Aann1g00001', 'Soca1g00200']", 'Aann1g00001'))
        self.assertFalse(exact_token('Aann1g000010;Aann1g00001.1', 'Aann1g00001'))
        self.assertFalse(exact_token('Aann1g00001-extra', 'Aann1g00001'))

    def test_ko_identifiers_are_not_pathway_identifiers(self):
        self.assertEqual(ko_terms('K07198,K04506; K07198'), ['K07198', 'K04506'])
        self.assertEqual(ko_terms('ko07198;map07198;K071980;NA'), [])

    def test_expression_retains_all_samples_and_units(self):
        for samples in [['SRR1', 'SRR2', 'SRR3'], ['F1', 'R1', 'RH1', 'TI-gen']]:
            columns, rows = expression_data(ExpressionFixture(samples), 'Aann', 'Aann1g00001')
            self.assertEqual(columns, ['geneid'] + samples + ['Express_index'])
            self.assertEqual(len(rows), 2)
            self.assertEqual([row[-1]['value'] for row in rows], ['FPKM', 'TPM'])
            self.assertEqual(rows[0][1]['value'], 0)

    def test_event_uses_the_actual_named_event_field(self):
        rows = named_rows([{'hhh_number': 1, 'gene1': 'Aann1g00001', 'gene2': 'Soca1g00002', 'event': 'ACH'}],
                          ['gene1', 'gene2', 'event'])
        self.assertEqual([c['value'] for c in rows[0]], ['Aann1g00001', 'Soca1g00002', 'ACH'])


if __name__ == '__main__':
    unittest.main()
