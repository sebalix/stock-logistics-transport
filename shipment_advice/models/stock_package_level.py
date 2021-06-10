# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockPackageLevel(models.Model):
    _inherit = "stock.package_level"

    shipment_advice_id = fields.Many2one(related="move_line_ids.shipment_advice_id")
