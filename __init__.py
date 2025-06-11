# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import reset_payment_provider, setup_provider

from . import controllers, models


def post_init_hook(env):
    setup_provider(env, "dinger")

def uninstall_hook(env):
    reset_payment_provider(env, "dinger")
