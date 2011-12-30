#!/usr/bin/env python
import sys
import os

from django.conf import settings, global_settings

if not settings.configured:
    datacash_settings = {}
    try:
        from integration import *
    except ImportError:
        pass
    else:
        for key, value in locals().items():
            if key.startswith('DATACASH'):
                datacash_settings[key] = value
    settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    }
                },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.admin',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.sites',
                'datacash',
                'south',
                ],
            DEBUG=False,
            SITE_ID=1,
            **datacash_settings
        )

from django.test.simple import DjangoTestSuiteRunner


def run_tests():
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    # Run tests
    test_runner = DjangoTestSuiteRunner(verbosity=2)
    failures = test_runner.run_tests(['datacash'])
    sys.exit(failures)

def generate_migration():
    from south.management.commands.schemamigration import Command
    com = Command()
    com.handle(app='datacash', initial=True)


if __name__ == '__main__':
    run_tests()
