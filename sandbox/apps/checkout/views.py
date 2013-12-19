from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.conf import settings
from django.utils.translation import ugettext as _

from oscar.apps.checkout.views import PaymentDetailsView as OscarPaymentDetailsView
from oscar.apps.payment.forms import BankcardForm
from oscar.apps.payment.models import SourceType, Source
from oscar.apps.order.models import ShippingAddress
from oscar.apps.address.models import UserAddress

from datacash.facade import Facade
from datacash import the3rdman


class PaymentDetailsView(OscarPaymentDetailsView):

    def get_context_data(self, **kwargs):
        # Add bankcard form to the template context
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        ctx['bankcard_form'] = kwargs.get('bankcard_form', BankcardForm())
        return ctx

    def post(self, request, *args, **kwargs):
        bankcard_form = BankcardForm(request.POST)

        if request.POST.get('action', '') == 'place_order':
            if not bankcard_form.is_valid():
                messages.error(request, _("Invalid submission"))
                return HttpResponseRedirect(
                    reverse('checkout:payment-details'))
            submission = self.build_submission(
                bankcard=bankcard_form.bankcard)
            return self.submit(**submission)

        # Check bankcard form is valid
        if not bankcard_form.is_valid():
            ctx = self.get_context_data(**kwargs)
            ctx['bankcard_form'] = bankcard_form
            return self.render_to_response(ctx)

        # Render preview page (with bankcard details hidden)
        return self.render_preview(request, bankcard_form=bankcard_form)

    def build_submission(self, **kwargs):
        submission = super(PaymentDetailsView, self).build_submission(**kwargs)
        if 'bankcard' in kwargs:
            submission['payment_kwargs']['bankcard'] = kwargs['bankcard']
        # Fraud screening needs access to shipping address
        submission['payment_kwargs']['shipping_address'] = submission[
            'shipping_address']
        return submission

    def handle_payment(self, order_number, order_total, **kwargs):
        # Make request to DataCash - if there any problems (eg bankcard
        # not valid / request refused by bank) then an exception would be
        # raised and handled)
        facade = Facade()

        # Use The3rdMan - so build a dict of data to pass
        email = None
        if not self.request.user.is_authenticated():
            email = self.checkout_session.get_guest_email()
        fraud_data = the3rdman.build_data_dict(
            request=self.request,
            email=email,
            order_number=order_number,
            shipping_address=kwargs['shipping_address'])

        # We're not using 3rd-man by default
        datacash_ref = facade.pre_authorise(
            order_number, order_total.incl_tax, kwargs['bankcard'])

        # Request was successful - record the "payment source".  As this
        # request was a 'pre-auth', we set the 'amount_allocated' - if we had
        # performed an 'auth' request, then we would set 'amount_debited'.
        source_type, _ = SourceType.objects.get_or_create(name='Datacash')
        source = Source(source_type=source_type,
                        currency=settings.DATACASH_CURRENCY,
                        amount_allocated=order_total.incl_tax,
                        reference=datacash_ref)
        self.add_payment_source(source)

        # Also record payment event
        self.add_payment_event('pre-auth', order_total.incl_tax)
