from datacash.gateway import Gateway


class Facade(object):

    """
    Responsible for dealing with oscar objects
    """
    
    def __init__(self):
        self.gateway = Gateway(settings.DATACASH_CLIENT, 
                               settings.DATACASH_PASSWORD, 
                               settings.DATACASH_HOST)
        self.currency = settings.DATACASH_CURRENCY

    def pre_auth(self):
        pass

    def fulfil(self):
        pass

    def refund(self
        pass
    
    def auth(self, order_number, amount, bankcard, billing_address=None):
        with transaction.commit_on_success():
            response = self.gateway.auth(card_number=bankcard.card_number,
                                         expiry_date=bankcard.expiry_date,
                                         amount=amount,
                                         currency='GBP',
                                         merchant_reference=self.generate_merchant_reference(order_number),
                                         ccv=bankcard.ccv)
            
            # Create transaction model irrespective of whether transaction was successful or not
            txn = OrderTransaction.objects.create(order_number=order_number,
                                                  basket=basket,
                                                  method='auth',
                                                  datacash_ref=response['datacash_reference'],
                                                  merchant_ref=response['merchant_reference'],
                                                  amount=amount,
                                                  auth_code=response['auth_code'],
                                                  status=int(response['status']),
                                                  reason=response['reason'],
                                                  request_xml=self.gateway.last_request_xml(),
                                                  response_xml=self.gateway.last_response_xml())
        
        # Test if response is successful
        if response['status'] == INVALID_CREDENTIALS:
            # This needs to notify the administrators straight away
            import pprint
            msg = "Order #%s:\n%s" % (order_number, pprint.pprint(response))
            mail_admins("Datacash credentials are not valid", msg)
            raise InvalidGatewayRequestError("Unable to communicate with payment gateway, please try again later")
        
        if response['status'] == DECLINED:
            raise TransactionDeclined("Your bank declined this transaction, please check your details and try again")
        
        return response['datacash_reference']
        
    def generate_merchant_reference(self, order_number):
        return '%s_%s' % (order_number, datetime.datetime.now().microsecond)
        
        

