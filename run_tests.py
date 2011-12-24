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
                ],
            ROOT_URLCONF='tests.urls',
            DEBUG=False,
            SITE_ID=1,
            **datacash_settings
        )

from django.test.simple import DjangoTestSuiteRunner


def run_tests():
    # Modify path
    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    # Run tests
    test_runner = DjangoTestSuiteRunner(verbosity=2)
    failures = test_runner.run_tests(['datacash'])
    sys.exit(failures)

if __name__ == '__main__':
    run_tests()
