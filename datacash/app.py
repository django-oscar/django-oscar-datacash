from django.conf.urls.defaults import patterns, url
from django.contrib.admin.views.decorators import staff_member_required

from oscar.core.application import Application
from oscar.apps.dashboard.nav import register, Node

from datacash.views import TransactionListView, TransactionDetailView

node = Node('Datacash', 'datacash-transaction-list')
register(node, 100)


class DatacashDashboardApplication(Application):
    name = None
    list_view = TransactionListView
    detail_view = TransactionDetailView

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^transactions/$', self.list_view.as_view(), 
                name='datacash-transaction-list'),
            url(r'^transactions/(?P<pk>\d+)/$', self.detail_view.as_view(), 
                name='datacash-transaction-detail'),
        )
        return self.post_process_urls(urlpatterns)

    def get_url_decorator(self, url_name):
        return staff_member_required


application = DatacashDashboardApplication()
