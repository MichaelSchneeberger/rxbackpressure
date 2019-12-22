import unittest

from rxbp.ack.ackimpl import continue_ack, Continue
from rxbp.observables.mergeobservable import MergeObservable
from rxbp.observerinfo import ObserverInfo
from rxbp.states.measuredstates.mergestates import MergeStates
from rxbp.states.measuredstates.terminationstates import TerminationStates
from rxbp.testing.testobservable import TestObservable
from rxbp.testing.testobserver import TestObserver
from rxbp.testing.testscheduler import TestScheduler


class TestMergeObservable(unittest.TestCase):
    def setUp(self):
        self.scheduler = TestScheduler()
        self.s1 = TestObservable()
        self.s2 = TestObservable()
        self.exception = Exception('test')

    def measure_state(self, obs: MergeObservable):
        return obs.state.get_measured_state(obs.termination_state)

    def measure_termination_state(self, obs: MergeObservable):
        return obs.termination_state.get_measured_state()

    def test_init_state(self):
        sink = TestObserver()
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.assertIsInstance(self.measure_termination_state(obs), TerminationStates.InitState)
        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceived)

    def test_left_complete(self):
        """
                      s1.on_completed
        NoneReceived -----------------> NoneReceived
         InitState                   LeftCompletedState
        """

        sink = TestObserver()
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_completed()

        self.assertFalse(sink.is_completed)
        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceived)
        self.assertIsInstance(self.measure_termination_state(obs), TerminationStates.LeftCompletedState)

    def test_left_complete_to_both_complete(self):
        """
                      s1.on_completed
        NoneReceived -----------------> Stopped
        LeftCompletedState         BothCompletedState
        """

        sink = TestObserver()
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_completed()
        self.s2.on_completed()

        self.assertIsInstance(self.measure_termination_state(obs), TerminationStates.BothCompletedState)
        self.assertIsInstance(self.measure_state(obs), MergeStates.Stopped)
        self.assertTrue(sink.is_completed)

    def test_left_complete_to_error_asynchronous_ack(self):
        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_completed()
        self.s2.on_error(self.exception)

        self.assertIsInstance(self.measure_termination_state(obs), TerminationStates.ErrorState)
        self.assertIsInstance(self.measure_state(obs), MergeStates.Stopped)
        self.assertEqual(self.exception, sink.exception)

    def test_emit_left_with_synchronous_ack(self):
        """
                      s1.on_next
        NoneReceived ------------> NoneReceived
         InitState                  InitState
        """

        sink = TestObserver()
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(1)

        self.assertIsInstance(self.measure_termination_state(obs), TerminationStates.InitState)
        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceived)
        self.assertEqual(sink.received, [1])

    def test_emit_right_with_synchronous_ack(self):
        """
                      s2.on_next
        NoneReceived ------------> NoneReceived
         InitState                  InitState
        """

        sink = TestObserver()
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s2.on_next_single(2)

        self.assertIsInstance(self.measure_termination_state(obs), TerminationStates.InitState)
        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceived)
        self.assertEqual(sink.received, [2])

    def test_left_complete_and_emit_right_with_synchronous_ack(self):
        """
                       s2.on_next
        NoneReceived ------------> NoneReceived
        LeftCompletedState       LeftCompletedState
        """

        sink = TestObserver()
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_completed()
        self.s2.on_next_single(2)

        self.assertIsInstance(self.measure_termination_state(obs), TerminationStates.LeftCompletedState)
        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceived)
        self.assertEqual(sink.received, [2])

    def test_emit_left_with_asynchronous_ack(self):
        """
                      s1.on_next
        NoneReceived ------------> NoneReceivedWaitAck
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        left_ack = self.s1.on_next_single(1)

        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceivedWaitAck)
        self.assertEqual(sink.received, [1])
        self.assertIsInstance(left_ack, Continue)

    def test_emit_right_with_asynchronous_ack(self):
        """
                      s2.on_next
        NoneReceived ------------> NoneReceivedWaitAck
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        right_ack = self.s2.on_next_single(2)

        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceivedWaitAck)
        self.assertEqual(sink.received, [2])
        self.assertIsInstance(right_ack, Continue)

    def test_none_received_to_left_received_with_asynchronous_ack(self):
        """
                             s1.on_next
        NoneReceivedWaitAck ------------> LeftReceived
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(1)
        left_ack = self.s1.on_next_single(1)

        self.assertIsInstance(self.measure_state(obs), MergeStates.LeftReceived)
        self.assertEqual(sink.received, [1])
        self.assertFalse(left_ack.has_value)

    def test_none_received_to_right_received_with_asynchronous_ack(self):
        """
                             s2.on_next
        NoneReceivedWaitAck ------------> RightReceived
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(2)
        left_ack = self.s1.on_next_single(2)

        self.assertIsInstance(self.measure_state(obs), MergeStates.LeftReceived)
        self.assertEqual(sink.received, [2])
        self.assertFalse(left_ack.has_value)

    def test_left_received_to_both_received_with_asynchronous_ack(self):
        """
                       s2.on_next
        LeftReceived ------------> BothReceivedContinueLeft
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(1)
        self.s1.on_next_single(1)
        right_ack = self.s2.on_next_single(2)

        self.assertIsInstance(self.measure_state(obs), MergeStates.BothReceivedContinueLeft)
        self.assertEqual(sink.received, [1])
        self.assertFalse(right_ack.has_value)

    def test_right_received_to_both_received_with_asynchronous_ack(self):
        """
                       s1.on_next
        RightReceived ------------> BothReceivedContinueRight
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s2.on_next_single(2)
        self.s2.on_next_single(2)
        left_ack = self.s1.on_next_single(1)

        self.assertIsInstance(self.measure_state(obs), MergeStates.BothReceivedContinueRight)
        self.assertEqual(sink.received, [2])
        self.assertFalse(left_ack.has_value)

    def test_acknowledge_non_received(self):
        """
                            ack.on_next
        NoneReceivedWaitAck ------------> NoneReceived
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(1)
        sink.ack.on_next(continue_ack)

        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceived)
        self.assertEqual(sink.received, [1])

    def test_acknowledge_left_received(self):
        """
                      ack.on_next
        LeftReceived ------------> NoneReceivedWaitAck
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(1)
        left_ack = self.s1.on_next_single(1)
        sink.ack.on_next(continue_ack)

        self.assertIsInstance(self.measure_state(obs), MergeStates.NoneReceivedWaitAck)
        self.assertEqual(sink.received, [1, 1])
        self.assertIsInstance(left_ack.value, Continue)

    def test_acknowledge_both_received(self):
        """
                                  ack.on_next
        BothReceivedContinueLeft ------------> RightReceived
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(1)
        left_ack = self.s1.on_next_single(1)
        right_ack = self.s2.on_next_single(2)
        sink.ack.on_next(continue_ack)

        self.assertIsInstance(self.measure_state(obs), MergeStates.LeftReceived)
        self.assertEqual(sink.received, [1, 1])
        self.assertIsInstance(left_ack.value, Continue)
        self.assertFalse(right_ack.has_value)

    def test_wait_ack_and_continue_with_asynchronous_ack(self):
        """
                 ack.on_next
        Stopped -------------> Stopped
        """

        sink = TestObserver(immediate_continue=0)
        obs = MergeObservable(self.s1, self.s2)
        obs.observe(ObserverInfo(sink))

        self.s1.on_next_single(1)
        self.s1.on_completed()
        self.s2.on_completed()
        sink.ack.on_next(continue_ack)

        self.assertIsInstance(self.measure_state(obs), MergeStates.Stopped)
        self.assertEqual(sink.received, [1])
