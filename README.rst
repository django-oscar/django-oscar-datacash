=================================
Datacash package for django-oscar
=================================

Installation
------------

From PyPi::

    pip install django-oscar-datacash

or from Github::

    pip install -e git://github.com/tangentlabs/django-oscar-datacash.git#egg=django-oscar-datacash

Add ``datacash`` to ``INSTALLED_APPS`` and run::

    ./manage.py migrate datacash

to create the appropriate models.

Settings
--------

``DATACASH_HOST`` - Host of DataCash server
``DATACASH_CLIENT`` - Username
``DATACASH_PASSWORD`` - Password
