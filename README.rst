=================================
Datacash package for django-oscar
=================================

Installation
------------

From PyPi (not ready just yet)::

    pip install django-oscar-datacash

or from Github::

    pip install -e git://github.com/tangentlabs/django-oscar-datacash.git#egg=django-oscar-datacash

Add ``datacash`` to ``INSTALLED_APPS`` and run::

    ./manage.py migrate datacash

to create the appropriate models.

Settings
--------

* ``DATACASH_HOST`` - Host of DataCash server

* ``DATACASH_CLIENT`` - Username

* ``DATACASH_PASSWORD`` - Password

* ``DATACASH_CURRENCY`` - Currency to use for transactions

* ``DATACASH_USE_CV2AVS`` - Whether to pass CV2AVS data
