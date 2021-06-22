# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.exceptions import UserError

from .common import Common


class TestShipmentAdviceLoad(Common):
    def test_shipment_advice_load_picking_not_planned(self):
        self._in_progress_shipment_advice(self.shipment_advice_out)
        picking = self.move_out1.picking_id
        wiz_model = self.env["wizard.load.shipment"].with_context(
            active_model=picking._name, active_ids=picking.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": self.shipment_advice_out.id})
        self.assertEqual(wiz.picking_ids, picking)
        self.assertFalse(wiz.move_line_ids)
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
        self.assertFalse(wiz.move_line_ids)
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

    def test_shipment_advice_load_move_line_not_planned(self):
        self._in_progress_shipment_advice(self.shipment_advice_out)
        move = self.move_out1
        wiz_model = self.env["wizard.load.shipment"].with_context(
            active_model=move.move_line_ids._name, active_ids=move.move_line_ids.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": self.shipment_advice_out.id})
        self.assertEqual(wiz.move_line_ids, move.move_line_ids)
        self.assertFalse(wiz.picking_ids)
        wiz.action_load()
        # Check planned entries
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertFalse(wiz.shipment_advice_id.planned_picking_ids)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 0)
        self.assertFalse(wiz.shipment_advice_id.planned_move_ids)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 0)
        # Check loaded entries
        self.assertEqual(wiz.shipment_advice_id.loaded_picking_ids, move.picking_id)
        self.assertEqual(wiz.shipment_advice_id.loaded_pickings_count, 1)
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_line_ids, move.move_line_ids
        )
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_lines_without_package_count, 1
        )

    def test_shipment_advice_load_move_line_already_planned(self):
        move = self.move_out1
        self._plan_moves_in_shipment(self.shipment_advice_out, move)
        self._in_progress_shipment_advice(self.shipment_advice_out)
        wiz = self._load_move_lines_in_shipment(
            self.shipment_advice_out, move.move_line_ids
        )
        self.assertEqual(wiz.move_line_ids, move.move_line_ids)
        self.assertFalse(wiz.picking_ids)
        # Check planned entries
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertEqual(wiz.shipment_advice_id.planned_picking_ids, move.picking_id)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 1)
        self.assertEqual(wiz.shipment_advice_id.planned_move_ids, move)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 1)
        # Check loaded entries
        self.assertEqual(wiz.shipment_advice_id.loaded_picking_ids, move.picking_id)
        self.assertEqual(wiz.shipment_advice_id.loaded_pickings_count, 1)
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_line_ids, move.move_line_ids
        )
        self.assertEqual(
            wiz.shipment_advice_id.loaded_move_lines_without_package_count, 1
        )

    def test_shipment_advice_already_planned_load_move_line_not_planned(self):
        # Plan the first move
        move1 = self.move_out1
        move2 = self.move_out2
        self._plan_moves_in_shipment(self.shipment_advice_out, move1)
        # But load the second move => error
        self._in_progress_shipment_advice(self.shipment_advice_out)
        with self.assertRaisesRegex(UserError, "planned already"):
            self._load_move_lines_in_shipment(
                self.shipment_advice_out, move2.move_line_ids
            )
