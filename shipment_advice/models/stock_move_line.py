# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        ondelete="set null",
        string="Shipment advice",
        index=True,
    )

    def button_load_in_shipment(self):
        action = self.env.ref(
            "shipment_advice.wizard_load_shipment_picking_action"
        ).read()[0]
        action["context"] = {"active_model": self._name, "active_ids": self.ids}
        return action
