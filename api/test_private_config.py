import json
import os
from pathlib import Path
import tempfile

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from LGBP.private_config import load_private_config


class PrivateConfigTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.private').mkdir(mode=0o700)
        self.path = self.root / '.private/settings.json'
        self.values = {
            'SECRET_KEY': 'fixture-key-with-\u4e2d\u6587-"-and-newline\n',
            'DATABASES': {'default': {
                'ENGINE': 'django.db.backends.mysql', 'NAME': 'fixture',
                'PASSWORD': 'fixture-password-"-\\-\u4e2d\u6587', 'PORT': '3306',
                'CONN_MAX_AGE': 120,
                'OPTIONS': {'connect_timeout': 10, 'charset': 'utf8mb4'},
            }},
        }

    def write(self, values):
        self.path.write_text(json.dumps(values, ensure_ascii=False), encoding='utf-8')
        self.path.chmod(0o600)

    def test_connection_values_and_types_are_preserved(self):
        self.write(self.values)
        self.assertEqual(load_private_config(self.root), self.values)

    def test_missing_file_fails_without_using_a_default_secret(self):
        with self.assertRaises(ImproperlyConfigured):
            load_private_config(self.root)

    def test_invalid_json_error_does_not_echo_file_contents(self):
        self.path.write_text('{"PASSWORD":"fixture-sensitive-value", bad-json', encoding='utf-8')
        self.path.chmod(0o600)
        with self.assertRaises(ImproperlyConfigured) as caught:
            load_private_config(self.root)
        self.assertNotIn('fixture-sensitive-value', str(caught.exception))

    def test_missing_site_key_is_rejected(self):
        self.values.pop('SECRET_KEY')
        self.write(self.values)
        with self.assertRaises(ImproperlyConfigured):
            load_private_config(self.root)

    def test_invalid_database_structure_is_rejected(self):
        self.values['DATABASES'] = []
        self.write(self.values)
        with self.assertRaises(ImproperlyConfigured):
            load_private_config(self.root)

    def test_missing_database_engine_is_rejected(self):
        del self.values['DATABASES']['default']['ENGINE']
        self.write(self.values)
        with self.assertRaises(ImproperlyConfigured):
            load_private_config(self.root)

    def test_unix_world_readable_settings_are_rejected(self):
        if os.name == 'nt':
            self.skipTest('Windows permissions are verified through the directory ACL.')
        self.write(self.values)
        self.path.chmod(0o644)
        with self.assertRaises(ImproperlyConfigured):
            load_private_config(self.root)
