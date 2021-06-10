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
        cls.shipment_advice = cls.env["shipment.advice"].create({})
        cls.dock = cls.env.ref("shipment_advice.stock_dock_demo")

    def _confirm_shipment_advice(self, arrival_date=None):
        if self.shipment_advice.state != "draft":
            return
        if arrival_date is None:
            arrival_date = fields.Datetime.now()
        self.shipment_advice.arrival_date = arrival_date
        self.shipment_advice.action_confirm()
        self.assertEqual(self.shipment_advice.state, "confirmed")

    def _in_progress_shipment_advice(self, dock=None):
        self._confirm_shipment_advice()
        if self.shipment_advice.state != "confirmed":
            return
        self.shipment_advice.dock_id = dock or self.dock
        self.shipment_advice.action_in_progress()
        self.assertEqual(self.shipment_advice.state, "in_progress")

    def _cancel_shipment_advice(self, dock=None):
        self._confirm_shipment_advice()
        if self.shipment_advice.state != "confirmed":
            return
        self.shipment_advice.action_cancel()
        self.assertEqual(self.shipment_advice.state, "cancel")

    def test_shipment_advice_confirm(self):
        with self.assertRaises(UserError):
            self.shipment_advice.action_confirm()
        self.shipment_advice.arrival_date = fields.Datetime.now()
        self.shipment_advice.action_confirm()
        self.assertEqual(self.shipment_advice.state, "confirmed")

    def test_shipment_advice_in_progress(self):
        self._confirm_shipment_advice()
        with self.assertRaises(UserError):
            self.shipment_advice.action_in_progress()
        self.shipment_advice.dock_id = self.dock
        self.shipment_advice.action_in_progress()
        self.assertEqual(self.shipment_advice.state, "in_progress")

    def test_shipment_advice_done(self):
        # TODO test validation of transfers/moves
        self._in_progress_shipment_advice()
        self.shipment_advice.action_done()
        self.assertEqual(self.shipment_advice.state, "done")

    def test_shipment_advice_cancel(self):
        self._in_progress_shipment_advice()
        self.shipment_advice.action_cancel()
        self.assertEqual(self.shipment_advice.state, "cancel")

    def test_shipment_advice_draft(self):
        self._cancel_shipment_advice()
        self.shipment_advice.action_draft()
        self.assertEqual(self.shipment_advice.state, "draft")
