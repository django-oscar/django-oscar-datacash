#!/usr/bin/env python
import sys
from optparse import OptionParser
import logging

import django
from django.conf import settings

logging.disable(logging.CRITICAL)

if not settings.configured:
    datacash_settings = {}
    try:
        from integration import *
    except ImportError:
        datacash_settings.update({
            'DATACASH_HOST': 'testserver.datacash.com',
            'DATACASH_CLIENT': '',
            'DATACASH_PASSWORD': '',
            'DATACASH_CURRENCY': 'GBP',
            'DATACASH_USE_CV2AVS': True,
        })
    else:
        for key, value in locals().items():
            if key.startswith('DATACASH'):
                datacash_settings[key] = value

    from oscar.defaults import *
    for key, value in locals().items():
        if key.startswith('OSCAR'):
            datacash_settings[key] = value
    datacash_settings['OSCAR_EAGER_ALERTS'] = False

    from oscar import get_core_apps

    sandbox_settings = {
        'DATABASES': {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        'INSTALLED_APPS': [
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'datacash',
        ] + get_core_apps(),
        'DEBUG': False,
        'SITE_ID': 1,
        'ROOT_URLCONF': 'tests.urls',
        'NOSE_ARGS': ['-s'],
        'HAYSTACK_CONNECTIONS': {
            'default': {
                'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
            },
        },
        'MIDDLEWARE_CLASSES': (
                'django.middleware.common.CommonMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'oscar.apps.basket.middleware.BasketMiddleware',
        ),
    }
    if django.VERSION < (1,7):
        sandbox_settings['INSTALLED_APPS'] += ['south']
    sandbox_settings.update(datacash_settings)
    settings.configure(**sandbox_settings)

# Needs to be here to avoid missing SETTINGS env var
from django_nose import NoseTestSuiteRunner


def run_tests(*test_args):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['tests']

    # Run tests
    test_runner = NoseTestSuiteRunner(verbosity=1)

    num_failures = test_runner.run_tests(test_args)

    if num_failures > 0:
        sys.exit(num_failures)


def generate_migration():
    from south.management.commands.schemamigration import Command
    com = Command()
    com.handle(app='datacash', initial=True)


if __name__ == '__main__':
    parser = OptionParser()
    (options, args) = parser.parse_args()
    run_tests(*args)
