from django.views.generic import ListView, DetailView

from datacash.models import OrderTransaction


class TransactionListView(ListView):
    model = OrderTransaction
    context_object_name = 'transactions'
    template_name = 'dashboard/datacash/transaction_list.html'


class TransactionDetailView(DetailView):
    model = OrderTransaction
    context_object_name = 'txn'
    template_name = 'dashboard/datacash/transaction_detail.html'
