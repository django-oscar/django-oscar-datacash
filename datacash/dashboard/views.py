from django.views.generic import ListView, DetailView

from datacash import models


class TransactionListView(ListView):
    model = models.OrderTransaction
    context_object_name = 'transactions'
    template_name = 'datacash/dashboard/transaction_list.html'


class TransactionDetailView(DetailView):
    model = models.OrderTransaction
    context_object_name = 'txn'
    template_name = 'datacash/dashboard/transaction_detail.html'


class FraudResponseListView(ListView):
    model = models.FraudResponse
    context_object_name = 'responses'
    template_name = 'datacash/dashboard/fraudresponse_list.html'
