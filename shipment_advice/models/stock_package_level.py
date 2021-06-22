# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockPackageLevel(models.Model):
    _inherit = "stock.package_level"

    shipment_advice_id = fields.Many2one(related="move_line_ids.shipment_advice_id")

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
        """Load the package levels into the given shipment advice."""
        self.is_done = True
        self.move_line_ids._load_in_shipment(shipment_advice)

    def _unload_from_shipment(self):
        """Unload the package levels from their related shipment advice."""
        self.move_line_ids._unload_from_shipment()
