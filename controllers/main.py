import logging
from odoo.http import route, request, Controller
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64, hashlib, json

_logger = logging.getLogger(__name__)

class DingerPayController(Controller):
    _webhook_url = '/payment/dinger/webhook'
    secret_key = 'd655c33205363f5450427e6b6193e466'

    @route(_webhook_url, type='json', auth='none', csrf=False, methods=['POST'])
    def dinger_webhook(self, **post):
        _logger.info("Dinger Webhook Received: %s", post)

        encrypted_b64 = post.get('paymentResult')
        checksum = post.get('checksum')

        try:
            # Decrypt
            cipher = AES.new(self.secret_key.encode(), AES.MODE_ECB)
            decrypted = unpad(cipher.decrypt(base64.b64decode(encrypted_b64)), AES.block_size)
            decrypted_str = decrypted.decode('utf-8')

            # Validate checksum
            if hashlib.sha256(decrypted_str.encode()).hexdigest() != checksum:
                return "Invalid checksum", 400

            payment_result = json.loads(decrypted_str)
            _logger.info("Decrypted Payment Result: %s", payment_result)

            tx = request.env['payment.transaction'].sudo()._get_tx_from_notification_data('dinger', {
                'ref': payment_result.get('orderId'),
                'payment_id': payment_result.get('transactionNum'),
                'status': payment_result.get('status')
            })

            tx._process_notification_data({
                'payment_id': payment_result.get('transactionNum'),
                'status': payment_result.get('status')
            })
            return "OK"

        except Exception as e:
            _logger.error("Webhook Decryption/Processing Error: %s", str(e))
            return "Error", 500
