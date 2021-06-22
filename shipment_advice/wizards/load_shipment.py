# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardLoadInShipment(models.TransientModel):
    _name = "wizard.load.shipment"
    _description = "Load shipment"

    picking_ids = fields.Many2many(
        comodel_name="stock.picking", string="Transfers to load",
    )
    move_line_ids = fields.Many2many(
        comodel_name="stock.move.line", string="Products to load"
    )
    package_level_ids = fields.Many2many(
        comodel_name="stock.package_level", string="Packages to load"
    )
    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        string="Shipment Advice",
        required=True,
        domain=[("state", "in", ("confirm", "in_progress"))],
    )
    warning = fields.Char(string="Warning", readonly=True)
    open_shipment = fields.Boolean(default=True)

    @api.model
    def default_get(self, fields_list):
        """'default_get' method overloaded."""
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_ids:
            raise UserError(
                _("Please select at least one record to load in a shipment.")
            )
        if active_model == "stock.picking" and active_ids:
            pickings = self.env[active_model].browse(active_ids)
            # We keep only deliveries and receptions not canceled/done
            pickings_to_keep = pickings.filtered_domain(
                [("state", "=", "assigned"), ("picking_type_id.code", "=", "outgoing")]
            )
            res["picking_ids"] = pickings_to_keep.ids
            if not pickings_to_keep:
                res["warning"] = _(
                    "No transfer to load among selected ones (already done or "
                    "not qualified as delivery)."
                )
            elif pickings != pickings_to_keep:
                res["warning"] = _(
                    "Transfers to include have been updated, keeping only those "
                    "assigned and qualified as delivery."
                )
            # Prefill the shipment if any (we take the first one)
            res["shipment_advice_id"] = fields.first(
                pickings_to_keep.move_lines.shipment_advice_id
            ).id
            # Prefill the shipment with the planned one if any (we take the first one)
            res["shipment_advice_id"] = fields.first(
                pickings_to_keep.move_lines.shipment_advice_id
            ).id
        if active_model == "stock.move.line" and active_ids:
            lines = self.env[active_model].browse(active_ids)
            # We keep only deliveries not canceled/done
            package_lines = lines.filtered_domain([("package_level_id", "!=", False)])
            lines_of_packages = package_lines.package_level_id.move_line_ids
            if package_lines != lines_of_packages:
                raise UserError(
                    _(
                        "You cannot load move lines which are part of a package, "
                        "unless to select all the move lines related to this package."
                    )
                )
            lines_to_keep = lines.filtered_domain(
                [
                    ("state", "in", ("assigned", "partially_available")),
                    ("picking_id.picking_type_id.code", "=", "outgoing"),
                ]
            )
            res["move_line_ids"] = lines.ids
            if not lines_to_keep:
                res["warning"] = _(
                    "No product to load among selected ones (already done or "
                    "not qualified as delivery)."
                )
            elif lines != lines_to_keep:
                res["warning"] = _(
                    "Lines to include have been updated, keeping only those "
                    "qualified as delivery."
                )
            # Prefill the shipment with the planned one if any
            res["shipment_advice_id"] = fields.first(
                lines_to_keep.move_id.shipment_advice_id
            ).id
        if active_model == "stock.package_level" and active_ids:
            package_levels = self.env[active_model].browse(active_ids)
            # We keep only deliveries and receptions not canceled/done
            package_levels_to_keep = package_levels.filtered_domain(
                [("state", "=", "assigned"), ("picking_type_code", "=", "outgoing")]
            )
            res["package_level_ids"] = package_levels.ids
            if not package_levels_to_keep:
                res["warning"] = _(
                    "No package to load among selected ones (already done or "
                    "not qualified as delivery)."
                )
            elif package_levels != package_levels_to_keep:
                res["warning"] = _(
                    "Packages to include have been updated, keeping only those "
                    "qualified as delivery."
                )
            # Prefill the shipment with the planned one if any
            res["shipment_advice_id"] = fields.first(
                package_levels_to_keep.move_ids.shipment_advice_id
                or package_levels_to_keep.move_line_ids.move_id.shipment_advice_id
            ).id
        return res

    @api.onchange("shipment_advice_id")
    def _onchange_shipment_advice_id(self):
        if not self.shipment_advice_id:
            return
        # Transfers
        pickings = self.picking_ids.filtered(
            lambda o: o.picking_type_code == self.shipment_advice_id.shipment_type
        )
        res = {}
        if self.picking_ids != pickings:
            res.update(
                warning={
                    "title": _("Transfers updated"),
                    "message": _(
                        "Transfers to load have been updated "
                        "to match the selected shipment type."
                    ),
                }
            )
        self.picking_ids = pickings
        # Lines
        lines = self.move_line_ids.filtered(
            lambda o: o.picking_id.picking_type_code
            == self.shipment_advice_id.shipment_type
        )
        res = {}
        if self.move_line_ids != lines:
            res.update(
                warning={
                    "title": _("Products updated"),
                    "message": _(
                        "Products to load have been updated "
                        "to match the selected shipment type."
                    ),
                }
            )
        self.move_line_ids = lines
        # Packages
        package_levels = self.package_level_ids.filtered(
            lambda o: o.picking_id.picking_type_code
            == self.shipment_advice_id.shipment_type
        )
        res = {}
        if self.package_level_ids != package_levels:
            res.update(
                warning={
                    "title": _("Packages updated"),
                    "message": _(
                        "Packages to load have been updated "
                        "to match the selected shipment type."
                    ),
                }
            )
        self.package_level_ids = package_levels
        return res

    def action_load(self):
        """Load the selected records in the selected shipment."""
        self.ensure_one()
        # Load whole transfers / move lines / package levels
        self.picking_ids._load_in_shipment(self.shipment_advice_id)
        self.move_line_ids._load_in_shipment(self.shipment_advice_id)
        self.package_level_ids._load_in_shipment(self.shipment_advice_id)
        # Update the shipment status if needed
        if self.shipment_advice_id.state == "confirmed":
            self.shipment_advice_id.action_in_progress()
        if self.open_shipment:
            action = self.env.ref("shipment_advice.shipment_advice_action").read()[0]
            action["res_id"] = self.shipment_advice_id.id
            return action
        return True
