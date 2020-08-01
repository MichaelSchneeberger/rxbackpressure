from dataclasses import dataclass
from typing import Optional

import rx
from rx.core.typing import Disposable, Scheduler

from rxbp.observable import Observable
from rxbp.observerinfo import ObserverInfo
from rxbp.observers.bufferedobserver import BufferedObserver
from rxbp.observers.evictingbufferedobserver import EvictingBufferedObserver
from rxbp.overflowstrategy import OverflowStrategy


@dataclass
class FromRxBufferingObservable(Observable):
    batched_source: rx.typing.Observable
    scheduler: Scheduler
    subscribe_scheduler: Scheduler
    overflow_strategy: OverflowStrategy
    buffer_size: int

    def observe(self, observer_info: ObserverInfo) -> Disposable:
        observer = BufferedObserver(
            underlying=observer_info.observer,
            scheduler=self.scheduler,
            subscribe_scheduler=self.subscribe_scheduler,
            buffer_size=self.buffer_size,
        )

        return self.batched_source.subscribe(
            on_next=observer.on_next,
            on_error=observer.on_error,
            on_completed=observer.on_completed,
            scheduler=self.scheduler,
        )
