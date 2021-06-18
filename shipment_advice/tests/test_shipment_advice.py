# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase


class TestShipmentAdvice(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.shipment_advice_in = cls.env["shipment.advice"].create(
            {"shipment_type": "incoming"}
        )
        cls.shipment_advice_out = cls.env["shipment.advice"].create(
            {"shipment_type": "outgoing"}
        )
        cls.dock = cls.env.ref("shipment_advice.stock_dock_demo")
        cls.product_in = cls.env.ref("product.product_delivery_01")
        cls.product_out = cls.env.ref("product.product_delivery_02")
        cls.picking_type_in = cls.env.ref("stock.picking_type_in")
        cls.picking_type_in.default_location_src_id = cls.env.ref(
            "stock.stock_location_suppliers"
        )
        cls.picking_type_out = cls.env.ref("stock.picking_type_out")
        cls.picking_type_out.default_location_dest_id = cls.env.ref(
            "stock.stock_location_customers"
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product_out, cls.picking_type_out.default_location_src_id, 20.0,
        )
        cls.move_in = cls._create_move(cls.picking_type_in, cls.product_in, 10)
        cls.group = cls.env["procurement.group"].create({})
        cls.move_out1 = cls._create_move(
            cls.picking_type_out, cls.product_out, 10, cls.group
        )
        cls.move_out2 = cls._create_move(
            cls.picking_type_out, cls.product_out, 10, cls.group
        )

    @classmethod
    def _create_move(cls, picking_type, product, quantity, group=False):
        move = cls.env["stock.move"].create(
            {
                "name": product.display_name,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": product.uom_id.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "warehouse_id": picking_type.warehouse_id.id,
                "picking_type_id": picking_type.id,
                "group_id": group and group.id or False,
                # "procure_method": "make_to_order",
                # "state": "draft",
            }
        )
        move._assign_picking()
        move._action_confirm(merge=False)
        move.picking_id.action_assign()
        return move

    def _confirm_shipment_advice(self, shipment_advice, arrival_date=None):
        if shipment_advice.state != "draft":
            return
        if arrival_date is None:
            arrival_date = fields.Datetime.now()
        shipment_advice.arrival_date = arrival_date
        shipment_advice.action_confirm()
        self.assertEqual(shipment_advice.state, "confirmed")

    def _in_progress_shipment_advice(self, shipment_advice, dock=None):
        self._confirm_shipment_advice(shipment_advice)
        if shipment_advice.state != "confirmed":
            return
        shipment_advice.dock_id = dock or self.dock
        shipment_advice.action_in_progress()
        self.assertEqual(shipment_advice.state, "in_progress")

    def _cancel_shipment_advice(self, shipment_advice, dock=None):
        self._confirm_shipment_advice(shipment_advice)
        if shipment_advice.state != "confirmed":
            return
        shipment_advice.action_cancel()
        self.assertEqual(shipment_advice.state, "cancel")

    def _plan_pickings_in_shipment(self, shipment_advice, pickings):
        wiz_model = self.env["wizard.plan.shipment"].with_context(
            active_model=pickings._name, active_ids=pickings.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        wiz.action_plan()
        return wiz

    def _plan_moves_in_shipment(self, shipment_advice, moves):
        wiz_model = self.env["wizard.plan.shipment"].with_context(
            active_model=moves._name, active_ids=moves.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        wiz.action_plan()
        return wiz

    def _load_pickings_in_shipment(self, shipment_advice, pickings):
        wiz_model = self.env["wizard.load.shipment"].with_context(
            active_model=pickings._name, active_ids=pickings.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        wiz.action_load()
        return wiz

    def test_shipment_advice_confirm(self):
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_confirm()
        self.shipment_advice_out.arrival_date = fields.Datetime.now()
        self.shipment_advice_out.action_confirm()
        self.assertEqual(self.shipment_advice_out.state, "confirmed")

    def test_shipment_advice_in_progress(self):
        self._confirm_shipment_advice(self.shipment_advice_out)
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_in_progress()
        self.shipment_advice_out.dock_id = self.dock
        self.shipment_advice_out.action_in_progress()
        self.assertEqual(self.shipment_advice_out.state, "in_progress")

    def test_shipment_advice_done(self):
        # TODO test validation of transfers/moves
        self._in_progress_shipment_advice(self.shipment_advice_out)
        self.shipment_advice_out.action_done()
        self.assertEqual(self.shipment_advice_out.state, "done")

    def test_shipment_advice_cancel(self):
        self._in_progress_shipment_advice(self.shipment_advice_out)
        self.shipment_advice_out.action_cancel()
        self.assertEqual(self.shipment_advice_out.state, "cancel")

    def test_shipment_advice_draft(self):
        self._cancel_shipment_advice(self.shipment_advice_out)
        self.shipment_advice_out.action_draft()
        self.assertEqual(self.shipment_advice_out.state, "draft")

    def test_shipment_advice_plan_picking(self):
        picking = self.move_out1.picking_id
        wiz = self._plan_pickings_in_shipment(self.shipment_advice_out, picking)
        self.assertEqual(wiz.picking_ids, picking)
        self.assertFalse(wiz.move_ids)
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertEqual(wiz.shipment_advice_id.planned_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 1)
        self.assertEqual(wiz.shipment_advice_id.planned_move_ids, picking.move_lines)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 2)

    def test_shipment_advice_plan_move(self):
        picking = self.move_out1.picking_id
        wiz = self._plan_moves_in_shipment(self.shipment_advice_out, self.move_out1)
        self.assertEqual(wiz.move_ids, self.move_out1)
        self.assertFalse(wiz.picking_ids)
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertEqual(wiz.shipment_advice_id.planned_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 1)
        self.assertEqual(wiz.shipment_advice_id.planned_move_ids, self.move_out1)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 1)

    def test_shipment_advice_load_picking_not_planned(self):
        self._in_progress_shipment_advice(self.shipment_advice_out)
        picking = self.move_out1.picking_id
        wiz_model = self.env["wizard.load.shipment"].with_context(
            active_model=picking._name, active_ids=picking.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": self.shipment_advice_out.id})
        self.assertEqual(wiz.picking_ids, picking)
        # self.assertFalse(wiz.move_ids)
        wiz.action_load()
        # Check planned entries
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertFalse(wiz.shipment_advice_id.planned_picking_ids)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 0)
        self.assertFalse(wiz.shipment_advice_id.planned_move_ids)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 0)
        # Check loaded entries
        self.assertEqual(wiz.shipment_advice_id.loaded_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.loaded_pickings_count, 1)
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_line_ids,
            self.move_out1.move_line_ids | self.move_out2.move_line_ids,
        )
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_lines_without_package_count, 2
        )

    def test_shipment_advice_load_picking_already_planned(self):
        picking = self.move_out1.picking_id
        self._plan_pickings_in_shipment(self.shipment_advice_out, picking)
        self._in_progress_shipment_advice(self.shipment_advice_out)
        wiz = self._load_pickings_in_shipment(self.shipment_advice_out, picking)
        self.assertEqual(wiz.picking_ids, picking)
        # self.assertFalse(wiz.move_line_ids)
        # Check planned entries
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertEqual(wiz.shipment_advice_id.planned_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 1)
        self.assertEqual(wiz.shipment_advice_id.planned_move_ids, picking.move_lines)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 2)
        # Check loaded entries
        self.assertEqual(wiz.shipment_advice_id.loaded_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.loaded_pickings_count, 1)
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_line_ids,
            self.move_out1.move_line_ids | self.move_out2.move_line_ids,
        )
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_lines_without_package_count, 2
        )
