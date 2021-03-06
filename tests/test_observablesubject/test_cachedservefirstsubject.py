from rxbp.acknowledgement.continueack import ContinueAck, continue_ack
from rxbp.init.initobserverinfo import init_observer_info
from rxbp.observablesubjects.cacheservefirstobservablesubject import CacheServeFirstObservableSubject
from rxbp.observerinfo import ObserverInfo
from rxbp.testing.testcasebase import TestCaseBase
from rxbp.testing.tobservable import TObservable
from rxbp.testing.tobserver import TObserver
from rxbp.testing.tscheduler import TScheduler


class TestCachedServeFirstSubject(TestCaseBase):

    def setUp(self):
        self.scheduler = TScheduler()
        self.source = TObservable()
        self.subject = CacheServeFirstObservableSubject(scheduler=self.scheduler)
        self.source.observe(init_observer_info(self.subject))
        self.exc = Exception()

    def test_initialize(self):
        CacheServeFirstObservableSubject(scheduler=self.scheduler)

    def test_on_next_synchronously(self):
        """
                                     on_next
        inactive_subscriptions = [s1] -> inactive_subscriptions = [s1]
        """

        # preparation
        observer = TObserver()
        self.subject.observe(init_observer_info(observer))

        # state change (change to the same state)
        ack = self.source.on_next_single(1)

        # verification
        self.assertIsInstance(ack, ContinueAck)
        self.assertEqual([1], observer.received)
        self.assertEqual(0, len(self.subject.shared_state.queue))

    def test_on_completed(self):
        """
               on_completed
        NormalState -> CompletedState
        """

        # preparation
        o1 = TObserver()
        self.subject.observe(init_observer_info(o1))

        # state change
        self.source.on_completed()

        # verification
        self.assertTrue(o1.is_completed)
        self.assertIsInstance(self.subject.state,
                              CacheServeFirstObservableSubject.CompletedState)

    def test_on_next_assynchronously(self):
        """
                                     on_next
        inactive_subscriptions = [s1] -> inactive_subscriptions = []
        """

        # preparation
        o1 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))

        # state change
        ack = self.source.on_next_single(1)

        # verification
        self.assertNotEqual(continue_ack, ack)
        self.assertEqual([1], o1.received)

    def test_on_next_assynchronously2(self):
        """
                                ack.on_next
        inactive_subscriptions = [] -> inactive_subscriptions = [s1]
        """

        # preparation
        o1 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        ack = self.source.on_next_single(1)

        # state change
        o1.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        # verification
        self.assertEqual(
            len(self.subject.shared_state.inactive_subscriptions),
            1
        )

    def test_on_next_multiple_elements_asynchronously(self):
        """
                 on_next
        queue = [] -> queue = [OnNext(2)]
        """

        # preparation
        o1 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.source.on_next_single(1)

        # state change
        self.source.on_next_single(2)

        # verification
        self.assertEqual([1], o1.received)
        queue = self.subject.shared_state.queue
        self.assertEqual(1, len(queue))
        self.assertEqual([2], queue[0].value)

    def test_on_next_assynchronously_enter_fast_loop(self):
        """
                        ack.on_next
        queue = [OnNext(2)] -> queue = []
        """

        #preparation
        o1 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.source.on_next_single(1)
        self.source.on_next_single(2)

        # enter fast loop
        o1.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        # verification
        self.assertEqual([1, 2], o1.received)

    def test_on_next_assynchronously_iterate_in_fast_loop(self):
        """
                 on_next
        queue = [] -> queue = [OnNext(2)]
        """

        # preparation
        o1 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.source.on_next_single(1)
        self.source.on_next_single(2)
        self.source.on_next_single(3)

        # state change
        o1.immediate_continue = 1           # needs immediate continue to loop
        o1.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        # validation
        self.assertEqual([1, 2, 3], o1.received)
        self.assertEqual(0, len(self.subject.shared_state.queue))

    def test_on_next_assynchronously_reenter_fast_loop(self):
        """
                        ack.on_next
        queue = [OnNext(3)] -> queue = []
        """

        # preparations
        o1 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.source.on_next_single(1)
        self.source.on_next_single(2)
        self.source.on_next_single(3)
        o1.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        # state change
        o1.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        # validation
        self.assertEqual([1, 2, 3], o1.received)
        self.assertEqual(0, len(self.subject.shared_state.queue))

    def test_on_next_two_subscribers_synchronously(self):
        """
                                     on_next
        inactive_subscriptions = [s1, s2] -> inactive_subscriptions = [s1, s2]
        """

        # preparation
        o1 = TObserver()
        o2 = TObserver()
        self.subject.observe(init_observer_info(o1))
        self.subject.observe(init_observer_info(o2))

        # state change
        ack = self.source.on_next_single(1)

        # verification
        self.assertIsInstance(ack, ContinueAck)
        self.assertEqual([1], o1.received)
        self.assertEqual([1], o2.received)
        self.assertEqual(0, len(self.subject.shared_state.queue))

    def test_on_next_multiple_elements_two_subscribers_asynchronously(self):
        """
                                       on_next
        inactive_subscriptions = [s1, s2] -> inactive_subscriptions = [s1, s2]
                               queue = [] -> queue = [OnNext(2)]
        """

        # preparation
        o1 = TObserver(immediate_continue=0)
        o2 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.subject.observe(init_observer_info(o2))
        self.source.on_next_single(1)

        # state change
        self.source.on_next_single(2)

        # validation
        self.assertEqual([1], o1.received)
        self.assertEqual([1], o2.received)
        self.assertEqual(1, len(self.subject.shared_state.queue))

    def test_on_next_enter_fast_loop_two_subscribers_asynchronously(self):
        o1 = TObserver(immediate_continue=0)
        o2 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.subject.observe(init_observer_info(o2))
        self.source.on_next_single(1)
        self.source.on_next_single(2)

        o1.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        self.assertEqual([1, 2], o1.received)
        self.assertEqual([1], o2.received)

    def test_on_next_enter_fast_loop_two_subscribers_asynchronously2(self):
        o1 = TObserver()
        o2 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.subject.observe(init_observer_info(o2))

        self.source.on_next_single(1)
        self.source.on_next_single(2)

        o2.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        o2.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        self.source.on_next_single(3)

        self.assertEqual([1, 2, 3], o1.received)
        self.assertEqual([1, 2, 3], o2.received)

    def test_on_error(self):
        """
               on_completed
        NormalState -> ErrorState
        """

        # preparation
        o1 = TObserver()
        self.subject.observe(init_observer_info(o1))

        # state change
        self.source.on_error(self.exc)

        # verification
        self.assertEqual(self.exc, o1.exception)
        self.assertIsInstance(self.subject.state,
                              CacheServeFirstObservableSubject.ExceptionState)

    def test_on_next_on_error_asynchronously(self):
        o1 = TObserver(immediate_continue=0)
        o2 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.subject.observe(init_observer_info(o2))

        ack = self.source.on_next_single(1)
        self.source.on_error(self.exc)

        # o2.ack.on_next(continue_ack)
        # self.scheduler.advance_by(1)

        # verification
        self.assertEqual(self.exc, o1.exception)
        self.assertEqual(self.exc, o2.exception)

    def test_on_error_two_subscribers_asynchronously(self):
        o1 = TObserver()
        o2 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.subject.observe(init_observer_info(o2))
        self.source.on_next_single(1)

        self.source.on_error(self.exc)

        self.assertEqual(self.exc, o1.exception)
        self.assertEqual(self.exc, o2.exception)

    def test_on_error_asynchronously(self):
        o1 = TObserver(immediate_continue=0)
        self.subject.observe(init_observer_info(o1))
        self.source.on_next_single(1)
        self.source.on_error(self.exc)

        o1.ack.on_next(continue_ack)
        self.scheduler.advance_by(1)

        self.assertEqual(self.exc, o1.exception)

    def test_on_disposed(self):
        sink = TObserver(immediate_continue=0)
        disposable = self.subject.observe(init_observer_info(sink))

        disposable.dispose()

        self.source.on_next_single(1)

        self.assertEqual([], sink.received)
