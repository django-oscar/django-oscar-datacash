SAMPLE_REQUEST = """<?xml version="1.0" encoding="UTF-8" ?>
<Request>
    <Authentication>
        <client>99000001</client>
        <password>boomboom</password>
    </Authentication>
    <Transaction>
    <CardTxn>
        <Card>
            <pan>1000011100000004</pan>
            <expirydate>04/06</expirydate>
            <startdate>01/04</startdate>
        </Card>
        <method>auth</method>
    </CardTxn>
    <TxnDetails>
        <merchantreference>1000001</merchantreference>
        <amount currency="GBP">95.99</amount>
    </TxnDetails>
    </Transaction>
</Request>"""

SAMPLE_CV2AVS_REQUEST = """<?xml version="1.0" ?>
<Request>
    <Authentication>
        <client>99001381</client>
        <password>hbANDMzErH</password>
    </Authentication>
    <Transaction>
        <CardTxn>
            <method>pre</method>
            <Card>
                <pan>XXXXXXXXXXXX0007</pan>
                <expirydate>02/12</expirydate>
                <Cv2Avs>
                    <street_address1>1
                    house</street_address1>
                    <street_address2/>
                    <street_address3/>
                    <street_address4/>
                    <postcode>n12
                    9et</postcode>
                    <cv2>123</cv2>
                </Cv2Avs>
            </Card>
        </CardTxn>
        <TxnDetails>
            <merchantreference>100024_182223</merchantreference>
            <amount currency="GBP">35.21</amount>
            <capturemethod>ecomm</capturemethod>
        </TxnDetails>
    </Transaction>
</Request>"""

SAMPLE_RESPONSE = """<?xml version="1.0" encoding="UTF-8" ?>
<Response>
    <CardTxn>
        <authcode>060642</authcode>
        <card_scheme>Switch</card_scheme>
        <country>United Kingdom</country>
        <issuer>HSBC</issuer>
    </CardTxn>
    <datacash_reference>3000000088888888</datacash_reference>
    <merchantreference>1000001</merchantreference>
    <mode>LIVE</mode>
    <reason>ACCEPTED</reason>
    <status>1</status>
    <time>1071567305</time>
</Response>"""

SAMPLE_SUCCESSFUL_FULFILL_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <datacash_reference>3000000088888888</datacash_reference>
    <merchantreference>3000000088888888</merchantreference>
    <mode>TEST</mode>
    <reason>FULFILLED OK</reason>
    <status>1</status>
    <time>1338297619</time>
</Response>"""

SAMPLE_DATACASH_REFERENCE_REQUEST = """<?xml version="1.0" ?>
<Request>
    <Authentication>
        <client>99001381</client>
        <password>samplepassword</password>
    </Authentication>
    <Transaction>
        <HistoricTxn>
            <reference>1234567890124209</reference>
            <method>fulfill</method>
            <authcode>747595</authcode>
        </HistoricTxn>
        <TxnDetails>
            <merchantreference>100001_FULFILL_1_6664</merchantreference>
            <amount>767.00</amount>
            <capturemethod>ecomm</capturemethod>
        </TxnDetails>
    </Transaction>
</Request>"""
