from django.conf.urls.defaults import patterns, url
from django.contrib.admin.views.decorators import staff_member_required

from oscar.core.application import Application

from . import views


class DatacashDashboardApplication(Application):
    name = None
    list_view = views.TransactionListView
    detail_view = views.TransactionDetailView
    fraud_list_view = views.FraudResponseListView

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^transactions/$', self.list_view.as_view(),
                name='datacash-transaction-list'),
            url(r'^transactions/(?P<pk>\d+)/$', self.detail_view.as_view(),
                name='datacash-transaction-detail'),
            url(r'^fraud-responses/$', self.fraud_list_view.as_view(),
                name='datacash-fraud-response-list'),
        )
        return self.post_process_urls(urlpatterns)

    def get_url_decorator(self, url_name):
        return staff_member_required


application = DatacashDashboardApplication()
