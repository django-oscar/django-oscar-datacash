import re

from django.db import models


class OrderTransaction(models.Model):
    
    # Note we don't use a foreign key as the order hasn't been created
    # by the time the transaction takes place
    order_number = models.CharField(max_length=128, db_index=True)
    
    # The 'method' of the transaction - one of 'auth', 'pre', 'cancel', ...
    method = models.CharField(max_length=12)
    amount = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True)
    merchant_reference = models.CharField(max_length=128, blank=True, null=True)
    
    # Response fields
    datacash_reference = models.CharField(max_length=128, blank=True, null=True)
    auth_code = models.CharField(max_length=128, blank=True, null=True)
    status = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    
    # Store full XML for debugging purposes
    request_xml = models.TextField()
    response_xml = models.TextField()
    
    date_created = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Ensure sensitive data isn't saved
        if not self.pk:
            cc_regex = re.compile(r'\d{12}')
            self.request_xml = cc_regex.sub('XXXXXXXXXXXX', self.request_xml)
            ccv_regex = re.compile(r'<cv2>\d+</cv2>')
            self.request_xml = ccv_regex.sub('<cv2>XXX</cv2>', self.request_xml)
        super(OrderTransaction, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'Datacash txn %s for order %s' % (self.datacash_reference, self.order_number)
