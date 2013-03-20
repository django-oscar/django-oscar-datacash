from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.conf import settings

from oscar.apps.checkout.views import PaymentDetailsView as OscarPaymentDetailsView
from oscar.apps.payment.forms import BankcardForm
from oscar.apps.payment.models import SourceType, Source

from datacash.facade import Facade


class PaymentDetailsView(OscarPaymentDetailsView):

    def get_context_data(self, **kwargs):
        # Add bankcard form to the template context
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        ctx['bankcard_form'] = kwargs.get('bankcard_form', BankcardForm())
        return ctx

    def post(self, request, *args, **kwargs):
        if request.POST.get('action', '') == 'place_order':
            return self.do_place_order(request)

        # Check bankcard form is valid
        bankcard_form = BankcardForm(request.POST)
        if not bankcard_form.is_valid():
            ctx = self.get_context_data(**kwargs)
            ctx['bankcard_form'] = bankcard_form
            return self.render_to_response(ctx)

        # Render preview page (with bankcard details hidden)
        return self.render_preview(request, bankcard_form=bankcard_form)

    def do_place_order(self, request):
        bankcard_form = BankcardForm(request.POST)
        if not bankcard_form.is_valid():
            messages.error(request, "Invalid submission")
            return HttpResponseRedirect(reverse('checkout:payment-details'))
        bankcard = bankcard_form.get_bankcard_obj()

        # Call oscar's submit method, passing through the bankcard object so it
        # gets passed to the 'handle_payment' method
        return self.submit(request.basket,
                           payment_kwargs={'bankcard': bankcard})

    def handle_payment(self, order_number, total_incl_tax, **kwargs):
        # Make request to DataCash - if there any problems (eg bankcard
        # not valid / request refused by bank) then an exception would be
        # raised ahd handled)
        facade = Facade()
        datacash_ref = facade.pre_authorise(
            order_number, total_incl_tax, kwargs['bankcard'])

        # Request was successful - record the "payment source".  As this
        # request was a 'pre-auth', we set the 'amount_allocated' - if we had
        # performed an 'auth' request, then we would set 'amount_debited'.
        source_type, _ = SourceType.objects.get_or_create(name='Datacash')
        source = Source(source_type=source_type,
                        currency=settings.DATACASH_CURRENCY,
                        amount_allocated=total_incl_tax,
                        reference=datacash_ref)
        self.add_payment_source(source)

        # Also record payment event
        self.add_payment_event('pre-auth', total_incl_tax)
