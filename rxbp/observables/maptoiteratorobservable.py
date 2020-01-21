from typing import Callable, Any, Iterator

from rxbp.observable import Observable
from rxbp.observer import Observer
from rxbp.observerinfo import ObserverInfo
from rxbp.typing import ElementType


class MapToIteratorObservable(Observable):
    def __init__(
            self,
            source: Observable,
            func: Callable[[Any], Iterator[Any]],
    ):
        super().__init__()

        self.source = source
        self.func = func

    def observe(self, observer_info: ObserverInfo):
        observer = observer_info.observer
        func = self.func

        class MapToIteratorObserver(Observer):
            def on_next(self, elem: ElementType):
                # `map` does not consume elements from the iterator/list
                # it is not its responsibility to catch an exception
                def map_gen():
                    for v in elem:
                        yield from func(v)

                return observer.on_next(list(map_gen()))

            def on_error(self, exc):
                return observer.on_error(exc)

            def on_completed(self):
                return observer.on_completed()

        map_subscription = observer_info.copy(MapToIteratorObserver())
        return self.source.observe(map_subscription)