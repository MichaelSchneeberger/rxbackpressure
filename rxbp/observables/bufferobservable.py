from dataclasses import dataclass
from typing import Optional

from rxbp.observable import Observable
from rxbp.observerinfo import ObserverInfo
from rxbp.observers.bufferedobserver import BufferedObserver
from rxbp.scheduler import Scheduler


@dataclass
class BufferObservable(Observable):
    source: Observable
    scheduler: Scheduler
    subscribe_scheduler: Scheduler
    buffer_size: int

    def observe(self, observer_info: ObserverInfo):
        buffered_observer = BufferedObserver(
            underlying=observer_info.observer,
            scheduler=self.scheduler,
            subscribe_scheduler=self.subscribe_scheduler,
            buffer_size=self.buffer_size,
        )
        return self.source.observe(observer_info.copy(
            observer=buffered_observer,
        ))
