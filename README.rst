=================================
Datacash package for django-oscar
=================================

This package provides integration with the payment gateway, DataCash_.  It is designed to
work seamlessly with the e-commerce framework `django-oscar`_ but can be used without 
Oscar.

It also supports batch fraud screeing using The3rdMan.

.. _DataCash: http://www.datacash.com/
.. _`django-oscar`: https://github.com/tangentlabs/django-oscar

* `PyPI homepage`_
* `crate.io page`_

.. _`continuous integration status`: http://travis-ci.org/#!/tangentlabs/django-oscar-datacash
.. _`PyPI homepage`: http://pypi.python.org/pypi/django-oscar-datacash/
.. _`crate.io page`: https://crate.io/packages/django-oscar-datacash/

.. image:: https://secure.travis-ci.org/tangentlabs/django-oscar-datacash.png
    :alt: Continuous integration
    :target: http://travis-ci.org/#!/tangentlabs/django-oscar-datacash

.. image:: https://coveralls.io/repos/tangentlabs/django-oscar-datacash/badge.png?branch=master
    :alt: Coverage
    :target: https://coveralls.io/r/tangentlabs/django-oscar-datacash

Getting started
===============

Sandbox
-------

When following the below instructions, it may be helpful to browse the sandbox
folder above as this is an example Oscar install which has been integrated with
Datacash.

Installation
------------

From PyPi::

    pip install django-oscar-datacash

or from Github::

    pip install git+git://github.com/tangentlabs/django-oscar-datacash.git#egg=django-oscar-datacash

Add ``'datacash'`` to ``INSTALLED_APPS`` and run::

    ./manage.py migrate datacash

to create the appropriate database tables.

Configuration
-------------

Edit your ``settings.py`` to set the following settings::

    DATACASH_HOST = 'testserver.datacash.com'
    DATACASH_CLIENT = '...'
    DATACASH_PASSWORD = '...'
    DATACASH_CURRENCY = 'GBP'

There are other settings available (see below).  Obviously, you'll need to
specify different settings in your test environment as opposed to your
production environment.  

Integration into checkout
-------------------------

You'll need to use a subclass of ``oscar.apps.checkout.views.PaymentDetailsView`` within your own 
checkout views.  See `Oscar's documentation`_ on how to create a local version of the checkout app.

.. _`Oscar's documentation`: http://django-oscar.readthedocs.org/en/latest/index.html

Override the ``handle_payment`` method (which is blank by default) and add your integration code.  An example
integration might look like:

.. code:: python

    # myshop.checkout.views
    from django.conf import settings
    
    from oscar.apps.checkout.views import PaymentDetailsView as OscarPaymentDetailsView
    from oscar.apps.payment.utils import Bankcard
    from oscar.apps.payment.forms import BankcardForm
    from datacash.facade import Facade
    from datacash import DATACASH

    ...

    class PaymentDetailsView(OscarPaymentDetailsView):

        def get_context_data(self):
            ...
            # Render a bankcard form
            ctx['bankcard_form'] = BankcardForm()
            ...
            return ctx

        def post(self, request, *args, **kwargs):
            # Check bankcard form is valid
            form = BankcardForm(request.POST)
            if not form.is_valid():
                ctx = self.get_context_data(**kwargs)
                ctx['bankcard_form'] = form
                return self.render_to_response(ctx)
            
            bankcard = form.get_bankcard_obj()
            return self.submit(request.basket, payment_kwargs={'bankcard': bankcard})

        def handle_payment(self, order_number, total, **kwargs):
            # Make request to DataCash - if there any problems (eg bankcard
            # not valid / request refused by bank) then an exception would be 
            # raised ahd handled) within oscar's PaymentDetails view.
            bankcard = kwargs['bankcard']
            datacash_ref = Facade().pre_authorise(order_number, total, bankcard)

            # Request was successful - record the "payment source".  As this 
            # request was a 'pre-auth', we set the 'amount_allocated' - if we had
            # performed an 'auth' request, then we woudl set 'amount_debited'.
            source_type,_ = SourceType.objects.get_or_create(name=DATACASH)
            source = Source(source_type=source_type,
                            currency=settings.DATACASH_CURRENCY,
                            amount_allocated=total,
                            reference=datacash_ref)
            self.add_payment_source(source)

            # Also record payment event
            self.add_payment_event('pre-auth', total_incl_tax)

Oscar's view will handle the various exceptions that can get raised.  See `DataCash's documentation`_
for further details on the various processing models that are available.

.. _`DataCash's documentation`: http://www.datacash.com/gettingproducts.php?id=Bank-Card-Processing-

Oscar also has a billing address form that can be used to collect billing address information
to submit to DataCash.  This is only required if your merchant account has Cv2Avs enabled. 

Integration into dashboard
--------------------------

Simply include the URLs in your ``urls.py``:

.. code:: python

    from datacash.dashboard.app import application

    urlpatterns = patterns('',
        ...
        (r'^dashboard/datacash/', include(application.urls)),
        ...
    )

Logging
-------

The gateway modules uses the named logger ``datacash``.

The3rdMan callbacks use the named logger ``datacash.the3rdman``.  It is
recommended that you use ``django.utils.log.AdminMailHandler`` with this logger
to ensure error emails are sent out for 500 responses.

Integration trouble-shooting
----------------------------

Many Datacash features require your merchant account to be configured correctly.
For instance, the default Datacash set-up won't include:

* Payments using historic transactions 
* Split settlements

When investigating problems, make sure your Datacash account is set-up
correctly.

Integration with The3rdMan
--------------------------

Using realtime fraud services requires submitting a dict of relevant data as part
of the initial transaction.  A helper method is provided that will extract all
it needs from Oscar's models:

.. code:: python

    from datacash.the3rdman import build_data_dict

    fraud_data = build_data_dict(
        request=request,
        order_number='1234',
        basket=request.basket,
        email=email
        shipping_address=shipping_address,
        billing_addres=billing_address)

then pass this data as a named argument when creating the transaction:

.. code:: python

    ref = Facade().pre_authorise(..., the3rdman_data=fraud_data)

To receive the callback, include the following in your ``urls.py``:

.. code:: python

    urlpatterns = patterns('',
        ...
        (r'^datacash/', include('datacash.urls')),
        ...
    )

When a fraud response is received, a custom signal is raised which your client
code should listen for.  Example:

.. code:: python

    from django.dispatch import receiver
    from datacash.the3rdman import signals

    @receiver(signals.response_received)
    def handle_fraud_response(sender, response, **kwargs):
        # Do something with response

Packages structure
==================

There are two key components:

Gateway
-------

The class ``datacash.gateway.Gateway`` provides fine-grained access to the
various DataCash APIs, which involve constructing XML requests and decoding XML
responses.  All calls return a ``datacash.gateway.Response`` instance which
provides dictionary-like access to the attributes of the response.

Example calls:

.. code:: python

    from decimal import Decimal as D
    from datacash.gateway import Gateway

    gateway = Gateway()

    # Single stage processing
    response = gateway.auth(amount=D('100.00'), currency='GBP',
                            merchant_reference='AA_1234',
                            card_number='4500203021916406',
                            expiry_date='10/14',
                            ccv='345')

    response = gateway.refund(amount=D('100.00'), currency='GBP',
                              merchant_reference='AA_1234',
                              card_number='4500203021916406',
                              expiry_date='10/14',
                              ccv='345')

    # Two-stage processing (using pre-registered card)
    response = gateway.pre(amount=D('50.00'), currency='GBP',
                           previous_txn_reference='3000000088888888')
    response = gateway.fulfill(amount=D('50.00'), currency='GBP',
                               txn_reference=response['datacash_reference'])

The gateway object know nothing of Oscar's classes and can be used in a stand-alone
manner.

Facade
------

The class ``datacash.facade.Facade`` wraps the above gateway object and provides a
less granular API, as well as saving instances of ``datacash.models.OrderTransaction`` to
provide an audit trail for Datacash activity.

Settings
========

* ``DATACASH_HOST`` - Host of DataCash server

* ``DATACASH_CLIENT`` - Username

* ``DATACASH_PASSWORD`` - Password

* ``DATACASH_CURRENCY`` - Currency to use for transactions

* ``DATACASH_USE_CV2AVS`` - Whether to pass CV2AVS data

* ``DATACASH_CAPTURE_METHOD`` - The 'capture method' to use.  Defaults to 'ecomm'.

Contributing
============

To work on ``django-oscar-datacash``, clone the repo, set up a virtualenv and install
in develop mode::

    make install

The test suite can then be run using::

    ./runtests.py

There is a sandbox Oscar site that can be used for development.  Create it
with::

    make sandbox

and browse it with::

    python sandbox/manage.py runserver

Magic card numbers are available on the Datacash site:
https://testserver.datacash.com/software/download.cgi?show=magicnumbers

Here's an example:

    1000010000000007

Have fun!

Changelog
=========

0.6
---
* Allow the transaction currency to be set pre transaction.  This is to support
  the new multi-currency features of Oscar 0.6.

0.5.3
-----
* Fix logging formatting bug

0.5.2
-----
* Remove uniqueness constraint for 3rdman response
* Add links to Gatekeeper from dashboard

0.5.1
-----
* Adjust how the response type of callback is determined

0.5
---
* Add support for The3rdMan fraud screening 

0.4.2
-----
* Fix mis-handling of datetimes introduced in 0.4.1

0.4.1
-----
* Handle bankcard dates passed as ``datetime.datetime`` instances instead of
  strings.  This is a compatability fix for Oscar 0.6 development.

0.4
---
* Oscar 0.5 support

0.3.5 / 2012-07-08
------------------
* Merchants passwords now removed from saved raw request XML
* A random int is now appended to the merchant ref to avoid having duplicates

0.3.4 / 2012-07-08
------------------
* Minor tweak to sort order of transactions in dashboard

0.3.2, 0.3.3 / 2012-06-13
-------------------------
* Updated packaging to include HTML templates

0.3.1 / 2012-06-12
------------------
* Added handling for split shipment payments

0.3 / 2012-05-10
----------------
* Added sandbox site
* Added dashboard view of transactions

0.2.3 / 2012-05-09
------------------
* Added admin.py
* Added travis.ci support

0.2.2 / 2012-02-14
------------------
* Fixed bug with currency in refund transactions

0.2.1 / 2012-02-7
------------------
* Fixed issue with submitting currency attribute for historic transactions
