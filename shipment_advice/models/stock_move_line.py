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
        action["context"] = {
            "active_model": self._name,
            "active_ids": self.ids,
            "default_open_shipment": self.env.context.get("open_shipment", True),
        }
        return action

    def _load_in_shipment(self, shipment_advice):
        """Load the move lines into the given shipment advice."""
        for move_line in self:
            move_line.shipment_advice_id = shipment_advice.id
            move_line.qty_done = move_line.product_uom_qty
