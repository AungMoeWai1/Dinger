from odoo import api, fields, models
import requests
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_v1_5
from odoo.addons.payment_dinger import const

class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    #=== FIELDS ===#
    code = fields.Selection(
        selection_add=[("dinger", "Dinger")], ondelete={"dinger": "set default"}
    )

    project_name = fields.Char(
        string="Dinger Project Name",
        help="Name of the project in the Dinger dashboard.",
        required_if_provider="dinger",
        groups="base.group_system",
    )

    api_key = fields.Char(
        string="Dinger Wallet Api Key",
        help="Wallet API key from the Dinger dashboard.",
        required_if_provider="dinger",
        groups="base.group_system",
    )

    public_key = fields.Char(
        string="Dinger Wallet Public Key",
        help="Wallet public key from the Dinger dashboard.",
        required_if_provider="dinger",
        groups="base.group_system",
    )

    merchant_key = fields.Char(
        string="Dinger Wallet Merchant Key",
        help="Wallet Merchant key from the Dinger dashboard.",
        required_if_provider="dinger",
        groups="base.group_system",
    )

    description = fields.Text(
        string="Description",
        default="Payment made by an Odoo website.",
        required_if_provider="dinger",
        groups="base.group_system",
    )

    #===  BUSINESS METHODS   ===#

    #Getting the token form the api by using project name,api key and merchant key,
    def _get_dinger_auth_token(self):
        url = "https://staging.dinger.asia/payment-gateway-uat/api/token"
        params = {
            "projectName": "sannkyi staging",  # self.project_name,
            "apiKey": "m7v9vlk.eaOE1x3k9FnSH-Wm6QtdM1xxcEs",  # self.api_key,
            "merchantName": "mtktest",  # self.merchant_key
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            print("Payment Token getting success...")
            return data.get("response", {}).get("paymentToken")
        return None

    # Segmentation encryption
    def encrypt(self, public_key, message):
        try:
            cipher_rsa = PKCS1_v1_5.new(public_key)
            res = []
            for i in range(0, len(message), 64):
                enc_tmp = cipher_rsa.encrypt(message[i:i + 64])
                res.append(enc_tmp)
            cipher_text = b''.join(res)
        except Exception as e:
            print(e)
        else:
            return base64.b64encode(cipher_text).decode()

    #To request for payment by send payload
    def _make_payment(self):
        token = self._get_dinger_auth_token()
        if not token:
            return None

        # self.public_key //need to assign this
        public_key = ("-----BEGIN PUBLIC KEY-----\n"
                      "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCy7O9ULgdfc1SUXrU0W2qWg3l8VbvNpvq+ilwPDdq4EYzKwOe97Zd2wtW8HJQF7"
                      "GNn2SaeHLCilsAJTYPLb+uRzXz3Aozxx8u6Bk5mGMVqi9rXXCNQCpRZYgM/7JDvtO5UhLCiMFHFO2f2c0QCmdR+yzdP6anJk9vLikuBwWxY6wIDAQAB"
                      "\n-----END PUBLIC KEY-----")

        # Correct JSON payload
        payload = """{
            'providerName': 'AYA Pay',
            'methodName': 'QR',
            'totalAmount': 1000,
            'orderId': '0286',
            'customerPhone': '09790710683',
            'customerName': 'Min Thu Kyaw',
            'items': [{'name': 'Dinger University Donation', 'amount': '1000', 'quantity': '1'}]
        }"""

        encoded_payload = payload.encode()
        public_key = RSA.import_key(public_key)
        encrypted_payload = self.encrypt(public_key, encoded_payload)
        # print("Static Encrypted Payload:", payload_encrypt)

        # encrypted_payload = """TtAJd/u2ZGevBVcSftg6z1KP7MTz3B2D3sujZfg4C46FRRS/WLrbKI4kQEdyQk+GNEp6Xk9uVOSgSnZ5oebwh4FUvfZsm1P9A85HXB4MZKldaddxkenCht9mQWHlJA4S/PCRtjFt9EJQiw06lHcwFRFj7EVtslc6LGnhkkYbt6lpU+Kt50SDz+ChDTN/tlrBq78xOWlnECR0ytnuvpS0KFZw03F/1KklIamM0E2Y9cklnbh9ypbuBhaMzA030h7WyRw/fazPsRjIlsk9KFdz9OlraYwGeTXRmEyqTFpt1ZICyJqDjuEOgTlmwp2L6l8a88zQEuPCCAHZ8/6xIjt4WAWdg8AIGThaTsRkHUvxzYgmLXWGdLJA9A/X5JScDXvNZWhhxjRKXkkPQ5wxGyHQZMqST75MVoeDItSQ7STD1lKYqxkQHrQSSoORKCBGnOzvSqe0o+lnacFhyfRh4rcPpcWFKowU8GO0GIal1MzSj/NS4Lr4cpSkQaUFQ6bLCEJe"""

        url = "https://staging.dinger.asia/payment-gateway-uat/api/pay"
        # Headers
        headers = {
            "Authorization": f"Bearer {token}"
        }
        # Payload (as multipart/form-data)
        files = {
            'payload': encrypted_payload  # `None` ensures it is sent as a plain form field
        }
        # Make the POST request
        response = requests.post(url, headers=headers, data=files)
        if response.status_code == 200:
            print("Post payload to Dinger success")
            return response.json()
        # res = {
        #     'code': '000',
        #     'message': 'Request Success',
        #     'time': '20201224 103734',
        #     'response': {
        #         'amount': 200,
        #         'merchOrderId': 'kothanzawlynn-172597',
        #         'formToken': 'd9422446-2532-49de-8d0e-9db221bf0597',
        #         'transactionNum': '9186115919',
        #         'sign': '71005BCDDF3AF7968A504B64012B1E680145E5D4568C9ACB1ADBE0E2F4C4DAC1',
        #         'signType': 'SHA256'
        #     }
        # }
        # return res

    def _dinger_make_request(self,data=None, method='POST'):
        if method == 'POST':
            return self._make_payment()
        return None

    def _get_country_code(self,country):
        url="https://staging.dinger.asia/payment-gateway-uat/api/countryCodeListEnquiry"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("Dinger Country Code getting success...")
            country_list=data.get("response",[])
            for entry in country_list:
                countries = entry.get("country", "").lower()
                if  country.lower() in countries:
                    return {"country":country,"code":entry.get("code")}
        return None



    def _get_default_payment_method_codes(self):
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'dinger':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
