# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShipmentAdvice(models.Model):
    _name = "shipment.advice"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Shipment Advice"
    _order = "arrival_date asc, id desc"

    def _default_warehouse_id(self):
        wh = self.env.ref("stock.warehouse0", raise_if_not_found=False)
        return wh.id or False

    name = fields.Char(
        default="/", copy=False, index=True, required=True, readonly=True
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("in_progress", "In progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        ondelete="cascade",
        string="Warehouse",
        required=True,
        states={"draft": [("readonly", False)]},
        readonly=True,
        check_company=True,
        default=_default_warehouse_id,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="warehouse_id.company_id",
        readonly=True,
        store=True,
        index=True,
    )
    shipment_type = fields.Selection(
        selection=[("outgoing", "Outgoing"), ("incoming", "Incoming")],
        string="Type",
        default="outgoing",
        required=True,
        states={"draft": [("readonly", False)]},
        readonly=True,
        help="Use incoming to plan receptions, use outgoing for deliveries.",
    )
    dock_id = fields.Many2one(
        comodel_name="stock.dock",
        ondelete="restrict",
        string="Loading dock",
        states={"draft": [("readonly", False)], "confirmed": [("readonly", False)]},
        readonly=True,
    )
    arrival_date = fields.Datetime(
        string="Arrival date",
        states={"draft": [("readonly", False)], "confirmed": [("readonly", False)]},
        readonly=True,
        help=(
            "When will the shipment arrives at the (un)loading dock, it is a "
            "planned date until in progress, then it represent the real one."
        ),
    )
    departure_date = fields.Datetime(
        string="Departure date",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
        help=(
            "When will the shipment leaves the (un)loading dock, it is a "
            "planned date until in progress, then it represent the real one."
        ),
    )
    ref = fields.Char(
        string="Consignment/Truck Ref.",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
    )
    total_load = fields.Float(
        string="Total load (kg)", digits=(16, 2), compute="_compute_total_load",
    )
    planned_move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="shipment_advice_id",
        string="Planned content list",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
    )
    planned_moves_count = fields.Integer(compute="_compute_count")
    planned_picking_ids = fields.One2many(
        comodel_name="stock.picking",
        compute="_compute_picking_ids",
        string="Planned transfers",
    )
    planned_pickings_count = fields.Integer(compute="_compute_count")
    loaded_move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="shipment_advice_id",
        string="Loaded content list",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
    )
    loaded_picking_ids = fields.One2many(
        comodel_name="stock.picking",
        compute="_compute_picking_ids",
        string="Loaded transfers",
    )
    loaded_package_ids = fields.One2many(
        comodel_name="stock.quant.package",
        compute="_compute_package_ids",
        string="Packages",
    )

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name, company_id)",
            "Reference must be unique per company!",
        ),
    ]

    @api.depends("loaded_package_ids")
    def _compute_total_load(self):
        for shipment in self:
            shipment.total_load = 0.0  # TODO

    @api.depends("planned_move_ids", "loaded_move_line_ids")
    def _compute_picking_ids(self):
        for shipment in self:
            shipment.planned_picking_ids = shipment.planned_move_ids.picking_id
            shipment.loaded_picking_ids = shipment.loaded_move_line_ids.picking_id

    @api.depends("loaded_move_line_ids")
    def _compute_package_ids(self):
        for shipment in self:
            shipment.loaded_package_ids = (
                shipment.loaded_move_line_ids.result_package_id
            )

    @api.depends("planned_picking_ids", "planned_move_ids")
    def _compute_count(self):
        for shipment in self:
            shipment.planned_pickings_count = len(self.planned_picking_ids)
            shipment.planned_moves_count = len(self.planned_move_ids)

    @api.model
    def create(self, vals):
        defaults = self.default_get(["name", "shipment_type"])
        sequence = self.env.ref("shipment_advice.shipment_advice_outgoing_sequence")
        if defaults["shipment_type"] == "incoming":
            sequence = self.env.ref("shipment_advice.shipment_advice_incoming_sequence")
        if vals.get("name", "/") == "/" and defaults.get("name", "/") == "/":
            vals["name"] = sequence.next_by_id()
        return super().create(vals)

    def action_confirm(self):
        for shipment in self:
            if shipment.state != "draft":
                raise UserError(
                    _("Shipment {} is not draft, operation aborted.").format(
                        shipment.name
                    )
                )
            if not shipment.arrival_date:
                raise UserError(
                    _(
                        "Arrival/departure date should be set on the "
                        "shipment advice {}."
                    ).format(shipment.name)
                )
            shipment.state = "confirmed"
        return True

    def action_in_progress(self):
        for shipment in self:
            if shipment.state != "confirmed":
                raise UserError(
                    _("Shipment {} is not confirmed, operation aborted.").format(
                        shipment.name
                    )
                )
            if not shipment.dock_id:
                raise UserError(
                    _("Dock should be set on the shipment advice {}.").format(
                        shipment.name
                    )
                )
            shipment.arrival_date = fields.Datetime.now()
            shipment.state = "in_progress"
        return True

    def action_done(self):
        for shipment in self:
            if shipment.state != "in_progress":
                raise UserError(
                    _("Shipment {} is not started, operation aborted.").format(
                        shipment.name
                    )
                )
            # Validate transfers (create backorders for unprocessed lines)
            if shipment.shipment_type == "incoming":
                # TODO: mark as done all unloaded transfers and create related
                #       back order if any line have not being processed
                pass
            else:
                # TODO
                # If Shipment advice backorder policy = create back
                #   order → mark as done all loaded transfers and create related
                #   back order if any
                # Elif leave it open
                #   → if all move of the transfer has a qty done = reserved qty
                #     and all package marked as done → mark as done the transfer
                #   → If some move or package have not been processed
                #     (qty done != reserved qty or package not marked as done)
                #     → do nothing and leave the transfer open
                pass
            shipment.departure_date = fields.Datetime.now()
            shipment.state = "done"
        return True

    def action_cancel(self):
        for shipment in self:
            if shipment.state not in ("confirmed", "in_progress"):
                raise UserError(
                    _("Shipment {} is not started, operation aborted.").format(
                        shipment.name
                    )
                )
            shipment.state = "cancel"

    def action_draft(self):
        for shipment in self:
            if shipment.state != "cancel":
                raise UserError(
                    _("Shipment {} is not canceled, operation aborted.").format(
                        shipment.name
                    )
                )
            shipment.state = "draft"

    def button_open_planned_pickings(self):
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        action["domain"] = [("id", "in", self.planned_picking_ids.ids)]
        return action

    def button_open_planned_moves(self):
        action = self.env.ref("stock.stock_move_action").read()[0]
        action["views"] = [
            (self.env.ref("stock.view_picking_move_tree").id, "tree"),
        ]
        action["domain"] = [("id", "in", self.planned_move_ids.ids)]
        action["context"] = {}  # Disable filters
        return action

    def button_open_loaded_pickings(self):
        # TODO
        pass

    def button_open_loaded_move_lines(self):
        # TODO
        pass

    def button_open_loaded_packages(self):
        # TODO
        pass

    def button_open_deliveries_in_progress(self):
        # TODO
        pass