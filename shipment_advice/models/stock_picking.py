# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    planned_shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        related="move_lines.shipment_advice_id",
        store=True,
        index=True,
    )
    is_loaded_in_shipment = fields.Boolean(
        string="Is loaded in a shipment?", compute="_compute_is_loaded_in_shipment",
    )
    loaded_packages_progress = fields.Char(
        "Packages loaded/total", compute="_compute_shipment_count"
    )
    loaded_move_lines_progress = fields.Char(
        "Lines loaded/total", compute="_compute_shipment_count"
    )
    loaded_weight_progress = fields.Char(
        "Weight/total", compute="_compute_shipment_count"
    )

    @api.depends("move_line_ids.shipment_advice_id")
    def _compute_is_loaded_in_shipment(self):
        for picking in self:
            picking.is_loaded_in_shipment = all(
                line.shipment_advice_id for line in picking.move_line_ids
            )

    @api.depends("package_level_ids.package_id")
    def _compute_shipment_count(self):
        for picking in self:
            picking.loaded_packages_progress = ""
            picking.loaded_move_lines_progress = ""
            picking.loaded_weight_progress = ""
            total_packages_count = len(picking.package_level_ids.package_id)
            total_move_lines_count = len(picking.move_line_ids)
            # Packages loading progress
            if total_packages_count:
                loaded_packages_count = len(
                    [pl for pl in picking.package_level_ids if pl.shipment_advice_id]
                )
                picking.loaded_packages_progress = (
                    f"{loaded_packages_count}/{total_packages_count}"
                )
            # Lines loading progress
            if total_move_lines_count:
                loaded_move_lines_count = len(
                    [
                        ml
                        for ml in picking.move_line_ids_without_package
                        if ml.shipment_advice_id
                    ]
                )
                picking.loaded_move_lines_progress = (
                    f"{loaded_move_lines_count}/{total_move_lines_count}"
                )
            # Weight/total
            if picking.shipping_weight:
                loaded_weight = sum(
                    [
                        ml.result_package_id.shipping_weight or ml.move_id.weight
                        for ml in picking.move_line_ids_without_package
                        if ml.shipment_advice_id
                    ]
                ) + sum(
                    [
                        pl.package_id.shipping_weight
                        for pl in picking.package_level_ids
                        if pl.shipment_advice_id
                    ]
                )
                picking.loaded_weight_progress = (
                    f"{loaded_weight}/{picking.shipping_weight}"
                )

    def button_load_in_shipment(self):
        action = self.env.ref(
            "shipment_advice.wizard_load_shipment_picking_action"
        ).read()[0]
        action["context"] = {"active_model": self._name, "active_ids": self.ids}
        return action

    def button_unload_from_shipment(self):
        action = self.env.ref(
            "shipment_advice.wizard_unload_shipment_picking_action"
        ).read()[0]
        action["context"] = {"active_model": self._name, "active_ids": self.ids}
        return action

    def _load_in_shipment(self, shipment_advice):
        """Load the whole transfers content into the given shipment advice."""
        self.package_level_ids._load_in_shipment(shipment_advice)
        self.move_line_ids._load_in_shipment(shipment_advice)

    def _unload_from_shipment(self):
        """Unload the whole transfers content from their related shipment advice."""
        self.package_level_ids._unload_from_shipment()
        self.move_line_ids._unload_from_shipment()
