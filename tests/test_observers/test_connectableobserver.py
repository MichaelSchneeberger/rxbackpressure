from rxbp.acknowledgement.stopack import StopAck
from rxbp.acknowledgement.continueack import ContinueAck
from rxbp.observers.connectableobserver import ConnectableObserver
from rxbp.testing.testcasebase import TestCaseBase
from rxbp.testing.tobserver import TObserver
from rxbp.testing.tscheduler import TScheduler


class TestConnectableObserver(TestCaseBase):

    def setUp(self):
        self.scheduler = TScheduler()
        self.exception = Exception('dummy')

    def test_initialize(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )

    def test_connect_empty(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )

        observer.connect()

        self.assertEqual(0, len(sink.received))

    def test_on_next(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )

        ack = observer.on_next([1])

        self.assertEqual(0, len(sink.received))

    def test_on_next_then_connect(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )
        ack = observer.on_next([1])

        observer.connect()

        self.assertEqual([1], sink.received)
        self.assertIsInstance(ack.value, ContinueAck)

    def test_on_error(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )

        observer.on_error(self.exception)

    def test_on_error_then_continue(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )
        observer.on_error(self.exception)

        observer.connect()

        self.assertEqual(self.exception, sink.exception)

    def test_on_next_on_error_then_connect(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )
        ack = observer.on_next([1])
        observer.on_error(self.exception)

        observer.connect()

        self.assertEqual([1], sink.received)
        self.assertEqual(self.exception, sink.exception)
        self.assertIsInstance(ack.value, ContinueAck)

    def test_on_next_on_error_then_connect_on_next(self):
        sink = TObserver()
        observer = ConnectableObserver(
            sink,
        )
        ack = observer.on_next([1])
        observer.on_error(self.exception)

        observer.connect()

        ack = observer.on_next([2])

        self.assertEqual([1], sink.received)
        self.assertEqual(self.exception, sink.exception)
        self.assertIsInstance(ack, StopAck)
