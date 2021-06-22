# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, fields, models
from odoo.exceptions import UserError


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
            planned_shipment = move_line.move_id.shipment_advice_id
            if planned_shipment and planned_shipment != shipment_advice:
                raise UserError(
                    _(
                        "You cannot load this into this shipment as it has been "
                        "planned to be loaded in {}"
                    ).format(planned_shipment.name)
                )
            elif not planned_shipment and shipment_advice.planned_move_ids:
                raise UserError(
                    _(
                        "You cannot load this into this shipment because its "
                        "content is planned already."
                    )
                )
            move_line.shipment_advice_id = shipment_advice.id
            move_line.qty_done = move_line.product_uom_qty

    def _unload_from_shipment(self):
        """Unload the move lines from their related shipment advice."""
        self.shipment_advice_id = False
