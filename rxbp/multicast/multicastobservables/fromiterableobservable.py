from dataclasses import dataclass
from typing import Iterable, Any

from rx.disposable import Disposable

from rxbp.mixins.schedulermixin import SchedulerMixin
from rxbp.multicast.multicastobservable import MultiCastObservable
from rxbp.multicast.multicastobserverinfo import MultiCastObserverInfo


@dataclass
class FromIterableObservable(MultiCastObservable):
    values: Iterable[Any]
    subscribe_scheduler: SchedulerMixin

    def observe(self, info: MultiCastObserverInfo) -> Disposable:
        # first element has to be scheduled on dedicated scheduler. Unlike in rxbp,
        # this "subscribe scheduler" is not automatically provided in rx, that is
        # why it must be provided as the `scheduler` argument of the `return_flowable`
        # operator.

        def scheduler_action(_, __):
            try:
                info.observer.on_next(self.values)
                info.observer.on_completed()
            except Exception as exc:
                info.observer.on_error(exc)

        return self.subscribe_scheduler.schedule(scheduler_action)
