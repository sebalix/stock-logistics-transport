# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardUnloadShipment(models.TransientModel):
    _name = "wizard.unload.shipment"
    _description = "Unload shipment"

    picking_ids = fields.Many2many(
        comodel_name="stock.picking", string="Transfers to unload",
    )
    warning = fields.Char(string="Warning", readonly=True)

    @api.model
    def default_get(self, fields_list):
        """'default_get' method overloaded."""
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_ids:
            raise UserError(
                _("Please select at least one record to unload from shipment.")
            )
        if active_model == "stock.picking" and active_ids:
            pickings = self.env[active_model].browse(active_ids)
            # We keep only deliveries not canceled/done
            pickings_to_keep = pickings.filtered(
                lambda o: (
                    o.state not in ["cancel", "done"]
                    and o.move_line_ids.shipment_advice_id
                    and all(
                        state == "in_progress"
                        for state in o.move_line_ids.shipment_advice_id.mapped("state")
                    )
                    and o.picking_type_code == "outgoing"
                )
            )
            res["picking_ids"] = pickings_to_keep.ids
            if not pickings_to_keep:
                res["warning"] = _(
                    "No transfer to unload among selected ones (already done or "
                    "not related to a shipment)."
                )
            elif pickings != pickings_to_keep:
                res["warning"] = _(
                    "Transfers to include have been updated, keeping only those "
                    "still in progress and related to a shipment."
                )
        return res

    def action_unload(self):
        """Unload the selected records from their related shipment."""
        self.ensure_one()
        self.picking_ids.move_line_ids.shipment_advice_id = False
        return True
