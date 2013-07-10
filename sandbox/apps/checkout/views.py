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
            messages.error(request, _("Invalid submission"))
            return HttpResponseRedirect(reverse('checkout:payment-details'))
        bankcard = bankcard_form.get_bankcard_obj()

        # Call oscar's submit method, passing through the bankcard object so it
        # gets passed to the 'handle_payment' method
        return self.submit(request.basket,
                           payment_kwargs={'bankcard': bankcard})

    # This is only required for Oscar < 0.6 which doesn't support a nice
    # way of getting a ShippingAddress instance without saving it.
    def get_shipping_address(self):
        addr_data = self.checkout_session.new_shipping_address_fields()
        if addr_data:
            return ShippingAddress(**addr_data)

        addr_id = self.checkout_session.user_address_id()
        if addr_id:
            # Create shipping address from an existing user address
            user_addr = UserAddress.objects.get(id=addr_id)
            shipping_addr = ShippingAddress()
            user_addr.populate_alternative_model(shipping_addr)
            return shipping_addr

    def handle_payment(self, order_number, total_incl_tax, **kwargs):
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
            shipping_address=self.get_shipping_address())

        datacash_ref = facade.pre_authorise(
            order_number, total_incl_tax, kwargs['bankcard'],
            the3rdman_data=fraud_data)

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
