from django.contrib import admin
from datacash.models import OrderTransaction


class OrderTransactionAdmin(admin.ModelAdmin):
    readonly_fields = ('order_number', 'method', 'amount', 'merchant_reference',
                       'datacash_reference', 'auth_code', 'status', 'reason',
                       'request_xml', 'response_xml', 'date_created')


admin.site.register(OrderTransaction, OrderTransactionAdmin)