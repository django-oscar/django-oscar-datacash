=================================
Datacash package for django-oscar
=================================

This package provides integration with the payment gateway, DataCash.  It is designed to
integrate seamlessly with the e-commerce framework `django-oscar`_ but can be used without 
using oscar.

.. _`django-oscar`: https://github.com/tangentlabs/django-oscar

Getting started
===============

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
checkout views.  See `oscar's documentation`_ on how to create a local version of the checkout app.

.. _`oscar's documentation`: http://django-oscar.readthedocs.org/en/latest/index.html

Override the ``handle_payment`` method (which is blank by default) and add your integration code.  An example
integration might look like::

    # myshop.checkout.views
    from django.conf import settings
    
    from oscar.apps.checkout.views import PaymentDetails as OscarPaymentDetails
    from oscar.apps.payment.utils import Bankcard
    from oscar.apps.checkout.forms import BankcardForm
    from datacash.facade import Facade

    ...

    class PaymentDetailsView(OscarPaymentDetails):

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
            
            kwargs['bankcard'] = form.get_bankcard_obj()
            super(PaymentDetailsView, self).post(request, *args, **kwargs)

        def handle_payment(self, order_number, total, **kwargs):
            # Make request to DataCash - if there any problems (eg bankcard
            # not valid / request refused by bank) then an exception would be 
            # raised ahd handled) within oscar's PaymentDetails view.
            bankcard = kwargs['bankcard']
            datacash_ref = Facade().pre_authorise(order_number, total, bankcard)

            # Request was successful - record the "payment source".  As this 
            # request was a 'pre-auth', we set the 'amount_allocated' - if we had
            # performed an 'auth' request, then we woudl set 'amount_debited'.
            source_type,_ = SourceType.objects.get_or_create(name='Datacash')
            source = Source(source_type=source_type,
                            currency=settings.DATACASH_CURRENCY,
                            amount_allocated=total,
                            reference=datacash_ref)
            self.add_payment_source(source)

Oscar's view will handle the various exceptions that can get raised.  See `DataCash's documentation`_
for further details on the various processing models that are available.

.. _`DataCash's documentation`: http://www.datacash.com/gettingproducts.php?id=Bank-Card-Processing-

Packages structure
==================

There are two key components:

Gateway
-------

The class ``datacash.gateway.Gateway`` provides fine-grained access to the
various DataCash APIs, which involve constructing XML requests and decoding XML
responses.  All calls return a ``datacash.gateway.Response`` instance which
provides dictionary-like access to the attributes of the response.

Example calls::

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

    python setup.py develop

then install the testing dependencies::

    pip install -r requirements.txt

The test suite can then be run using::

    ./run_tests.py
