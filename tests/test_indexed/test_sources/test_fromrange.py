import unittest

import rxbp
from rxbp.acknowledgement.continueack import continue_ack
from rxbp.observerinfo import ObserverInfo
from rxbp.indexed.selectors.bases.numericalbase import NumericalBase
from rxbp.subscriber import Subscriber
from rxbp.testing.testobserver import TestObserver
from rxbp.testing.testscheduler import TestScheduler


class TestFromRange(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = TestScheduler()

    def test_base(self):
        subscription = rxbp.from_range(1, 4).unsafe_subscribe(Subscriber(
            scheduler=self.scheduler, subscribe_scheduler=self.scheduler))

        self.assertEqual(NumericalBase(3), subscription.info.base)

    def test_use_case(self):
        sink = TestObserver(immediate_continue=0)
        subscription = rxbp.from_range(1, 4).unsafe_subscribe(Subscriber(
            scheduler=self.scheduler, subscribe_scheduler=self.scheduler))
        subscription.observable.observe(ObserverInfo(observer=sink))

        self.scheduler.advance_by(1)

        self.assertEqual([1, 2, 3], sink.received)
        self.assertTrue(sink.is_completed)

    def test_from_list_batch_size_of_one(self):
        sink = TestObserver(immediate_continue=0)
        subscription = rxbp.from_range(1, 4, batch_size=1).unsafe_subscribe(Subscriber(
            scheduler=self.scheduler, subscribe_scheduler=self.scheduler))
        subscription.observable.observe(ObserverInfo(observer=sink))

        self.scheduler.advance_by(1)

        self.assertEqual([1], sink.received)
        self.assertFalse(sink.is_completed)

        sink.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        self.assertEqual([1, 2], sink.received)

    def test_from_list_batch_size_of_two(self):
        sink = TestObserver(immediate_continue=0)
        subscription = rxbp.from_range(1, 4, batch_size=2).unsafe_subscribe(Subscriber(
            scheduler=self.scheduler, subscribe_scheduler=self.scheduler))
        subscription.observable.observe(ObserverInfo(observer=sink))

        self.scheduler.advance_by(1)

        self.assertEqual([1, 2], sink.received)

        sink.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        self.assertEqual([1, 2, 3], sink.received)
        self.assertTrue(sink.is_completed)