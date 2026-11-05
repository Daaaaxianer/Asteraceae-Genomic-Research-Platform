"""Read deployment secrets from the project's owner-only private directory."""
import json
import os
from pathlib import Path
import stat

from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.debug import sensitive_variables


@sensitive_variables()
def load_private_config(base_dir):
    path = Path(base_dir) / '.private' / 'settings.json'
    try:
        if os.name != 'nt':
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise ImproperlyConfigured('Private settings must be readable only by the application owner (mode 0600).')
        with path.open(encoding='utf-8') as source:
            config = json.load(source)
    except (OSError, ValueError):
        raise ImproperlyConfigured('Cannot read private settings. Check .private/settings.json and its permissions.') from None

    if not isinstance(config, dict):
        raise ImproperlyConfigured('Private settings must be a JSON object.')
    key = config.get('SECRET_KEY')
    databases = config.get('DATABASES')
    if not isinstance(key, str) or not key:
        raise ImproperlyConfigured('Private settings require a non-empty SECRET_KEY.')
    if not isinstance(databases, dict) or not isinstance(databases.get('default'), dict):
        raise ImproperlyConfigured('Private settings require a DATABASES.default object.')
    if not isinstance(databases['default'].get('ENGINE'), str) or not databases['default']['ENGINE']:
        raise ImproperlyConfigured('Private settings require DATABASES.default.ENGINE.')
    return {'SECRET_KEY': key, 'DATABASES': databases}
