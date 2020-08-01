from typing import Optional, Callable, Any

from rxbp.ack.continueack import ContinueAck
from rxbp.ack.mixins.ackmixin import AckMixin
from rxbp.ack.single import Single
from rxbp.ack.stopack import StopAck, stop_ack
from rxbp.observable import Observable
from rxbp.observer import Observer
from rxbp.observerinfo import ObserverInfo
from rxbp.typing import ElementType


class DebugObservable(Observable):
    def __init__(
            self,
            source: Observable,
            name: Optional[str],
            on_next: Callable[[Any], None] = None,
            on_completed: Callable[[], None] = None,
            on_error: Callable[[Exception], None] = None,
            on_ack: Callable[[AckMixin], None] = None,
            on_subscribe: Callable[[ObserverInfo], None] = None,
            on_raw_ack: Callable[[AckMixin], None] = None,
    ):
        self.source = source
        self.name = name

        all_none = not any([on_next, on_completed, on_error, on_ack, on_subscribe, on_raw_ack])

        if all_none:
            self.on_next_func = on_next or (lambda v: print('{}.on_next {}'.format(name, v)))
            self.on_error_func = on_error or (lambda exc: print('{}.on_error {}'.format(name, exc)))
            self.on_completed_func = on_completed or (lambda: print('{}.on_completed'.format(name)))
            self.on_subscribe_func = on_subscribe or (lambda v: print('{}.on_observe {}'.format(name, v.observer)))
            self.on_sync_ack = on_ack or (lambda v: print('{}.on_sync_ack {}'.format(name, v)))
            self.on_async_ack = on_ack or (lambda v: print('{}.on_async_ack {}'.format(name, v)))
            self.on_raw_ack = on_raw_ack or (lambda v: print('{}.on_raw_ack {}'.format(name, v)))

        else:
            def empty_func0():
                return None

            def empty_func1(v):
                return None

            self.on_next_func = on_next or empty_func1
            self.on_error_func = on_error or empty_func1
            self.on_completed_func = on_completed or empty_func0
            self.on_subscribe_func = on_subscribe or empty_func1
            self.on_sync_ack = on_ack or empty_func1
            self.on_async_ack = on_ack or empty_func1
            self.on_raw_ack = on_raw_ack or empty_func1

    def observe(self, observer_info: ObserverInfo):
        observer_info = observer_info.observer
        self.on_subscribe_func(observer_info)

        source = self

        class DebugObserver(Observer):
            def on_next(self, elem: ElementType):
                try:
                    materialized = list(elem)
                except Exception as exc:
                    source.on_error_func(exc)
                    observer_info.on_error(exc)
                    return stop_ack

                source.on_next_func(materialized)

                ack = observer_info.on_next(materialized)

                if isinstance(ack, ContinueAck) or isinstance(ack, StopAck):
                    source.on_sync_ack(ack)
                else:
                    source.on_raw_ack(ack)

                    class ResultSingle(Single):
                        def on_next(_, elem):
                            source.on_async_ack(elem)

                        def on_error(self, exc: Exception):
                            pass

                    ack.subscribe(ResultSingle())
                return ack

            def on_error(self, exc):
                source.on_error_func(exc)
                observer_info.on_error(exc)

            def on_completed(self):
                source.on_completed_func()
                return observer_info.on_completed()

        debug_observer = DebugObserver()
        debug_subscription = init_observer_info(debug_observer, is_volatile=observer_info.is_volatile)
        return self.source.observe(debug_subscription)
