# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import pprint
from urllib.parse import quote as url_quote
from werkzeug import urls
from odoo import _, models,api
from odoo.tools import float_round
from odoo.exceptions import ValidationError
from odoo.addons.payment_dinger import const
from odoo.addons.payment_dinger.controllers.main import DingerPayController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, transaction):
        """
        Override this method to pass custom values to the redirect form.
        """
        rendering_values = super()._get_specific_rendering_values(transaction)

        if self.provider_code != 'dinger':
            return rendering_values

        rendering_values=self._dinger_prepare_preference_request_payload()

        _logger.info(
            "Sending '/checkout/preferences' request for link creation:\n%s",
            pprint.pformat(rendering_values),
        )

        verified_payment_data = self.provider_id._dinger_make_request(method='POST')
        self._set_done()

        # payment_status = verified_payment_data.data.get("response", {}).get("status")
        # if not payment_status:
        #     raise ValidationError("Dinger: " + _("Received data with missing status."))
        #
        # if payment_status in const.TRANSACTION_STATUS_MAPPING['pending']:
        #     self._set_pending()
        # elif payment_status in const.TRANSACTION_STATUS_MAPPING['done']:
        #     self._set_done()
        # elif payment_status in const.TRANSACTION_STATUS_MAPPING['canceled']:
        #     self._set_canceled()
        # elif payment_status in const.TRANSACTION_STATUS_MAPPING['error']:
        #     status_detail = verified_payment_data.data.get("response", {}).get("status_detail")
        #     _logger.warning(
        #         "Received data for transaction with reference %s with status %s and error code: %s",
        #         self.reference, payment_status, status_detail
        #     )
        #     error_message = self._dinger_get_error_msg(status_detail)
        #     self._set_error(error_message)
        # else:  # Classify unsupported payment status as the `error` tx state.
        #     _logger.warning(
        #         "Received data for transaction with reference %s with invalid payment status: %s",
        #         self.reference, payment_status
        #     )
        #     self._set_error(
        #         "Dinger: " + _("Received data with invalid status: %s", payment_status)
        #     )
        return rendering_values


    def _dinger_prepare_preference_request_payload(self):
        """ Create the payload for the preference request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        return_url = urls.url_join(base_url, DingerPayController._return_url)
        sanitized_reference = url_quote(self.reference)
        webhook_url = urls.url_join(
            base_url, f'{DingerPayController._webhook_url}/{sanitized_reference}'
        )  # Append the reference to identify the transaction from the webhook notification data.

        unit_price = self.amount
        decimal_places = const.CURRENCY_DECIMALS.get(self.currency_id.name)
        if decimal_places is not None:
            unit_price = float_round(unit_price, decimal_places, rounding_method='DOWN')

        return {
            'auto_return': 'all',
            'back_urls': {
                'success': return_url,
                'pending': return_url,
                'failure': return_url,
            },
            'external_reference': self.reference,
            'items': [{
                'title': self.reference,
                'quantity': 1,
                'currency_id': self.currency_id.name,
                'unit_price': unit_price,
            }],
            'notification_url': webhook_url,
            'payer': {
                'name': self.partner_name,
                'email': self.partner_email,
                'phone': {
                    'number': self.partner_phone,
                },
                'address': {
                    'zip_code': self.partner_zip,
                    'street_name': self.partner_address,
                },
            },
            'payment_methods': self.payment_method_id,
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Mercado Pago data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'dinger' or len(tx) == 1:
            return tx

        reference = notification_data.get('external_reference')
        if not reference:
            raise ValidationError("Dinger: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'dinger')])
        if not tx:
            raise ValidationError(
                "Dinger: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    @api.model
    def _dinger_get_error_msg(self, status_detail):
        """ Return the error message corresponding to the payment status.

        :param str status_detail: The status details sent by the provider.
        :return: The error message.
        :rtype: str
        """
        return "Dinger: " + const.ERROR_MESSAGE_MAPPING.get(
            status_detail, const.ERROR_MESSAGE_MAPPING['cc_rejected_other_reason']
        )

