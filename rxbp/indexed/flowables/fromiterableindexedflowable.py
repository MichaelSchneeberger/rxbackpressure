from dataclasses import dataclass
from typing import Iterable

from rxbp.indexed.init.initindexedsubscription import init_indexed_subscription
from rxbp.indexed.mixins.indexedflowablemixin import IndexedFlowableMixin
from rxbp.observables.fromiteratorobservable import FromIteratorObservable
from rxbp.selectors.base import Base
from rxbp.selectors.baseandselectors import BaseAndSelectors
from rxbp.subscriber import Subscriber
from rxbp.subscription import Subscription
from rxbp.typing import ValueType


@dataclass
class FromIterableIndexedFlowable(IndexedFlowableMixin):
    iterable: Iterable[ValueType]
    base: Base

    def unsafe_subscribe(self, subscriber: Subscriber) -> Subscription:
        iterator = iter(self.iterable)

        return init_indexed_subscription(
            index=BaseAndSelectors(
                base=self.base,
            ),
            observable=FromIteratorObservable(
                iterator=iterator,
                subscribe_scheduler=subscriber.subscribe_scheduler,
                scheduler=subscriber.scheduler,
            ),
        )
