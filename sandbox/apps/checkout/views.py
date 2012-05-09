from oscar.apps.checkout.views import PaymentDetailsView as OscarPaymentDetailsView
from oscar.apps.payment.forms import BankcardForm



class PaymentDetailsView(OscarPaymentDetailsView):
    
    def get_context_data(self, **kwargs):
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        ctx['bankcard_form'] = BankcardForm()
        return ctx

    def handle_payment(self, order_number, total_incl_tax, **kwargs):
        assert False


