# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields
from odoo.exceptions import UserError

from .common import Common


class TestShipmentAdvice(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
