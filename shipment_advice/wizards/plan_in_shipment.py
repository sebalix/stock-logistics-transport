# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardPlanInShipment(models.TransientModel):
    _name = "wizard.plan.in.shipment"
    _description = "Plan in shipment"

    picking_ids = fields.Many2many(
        comodel_name="stock.picking", string="Transfers to plan",
    )
    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        string="Shipment Advice",
        required=True,
        domain=[("state", "=", "draft")],
    )

    @api.model
    def default_get(self, fields_list):
        """'default_get' method overloaded."""
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_ids:
            raise UserError(
                _("Please select at least one record to plan in a shipment.")
            )
        if active_model == "stock.picking" and active_ids:
            pickings = self.env[active_model].browse(active_ids)
            # We keep only deliveries and receptions not canceled/done
            pickings = pickings.filtered_domain(
                [
                    ("state", "not in", ["cancel", "done"]),
                    ("picking_type_code", "in", ["incoming", "outgoing"]),
                ]
            )
            res["picking_ids"] = pickings.ids
        return res

    @api.onchange("shipment_advice_id")
    def _onchange_shipment_advice_id(self):
        pickings = self.picking_ids.filtered(
            lambda o: o.picking_type_code == self.shipment_advice_id.shipment_type
        )
        res = {}
        if not self.shipment_advice_id:
            return
        if self.picking_ids != pickings:
            res.update(
                warning={
                    "title": _("Transfers updated"),
                    "message": _(
                        "Transfers to include have been updated "
                        "to match the selected shipment type."
                    ),
                }
            )
        self.picking_ids = pickings
        return res

    def action_plan(self):
        """Plan the selected records in the selected shipment."""
        self.ensure_one()
        self.picking_ids.move_lines.shipment_advice_id = self.shipment_advice_id
        action = self.env.ref("shipment_advice.shipment_advice_action").read()[0]
        action["res_id"] = self.shipment_advice_id.id
        action["view_mode"] = "form"
        return action
