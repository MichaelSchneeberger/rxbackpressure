import threading
import types
from dataclasses import dataclass
from itertools import chain
from traceback import FrameSummary
from typing import List

import rx
from rx.disposable import CompositeDisposable, RefCountDisposable, SingleAssignmentDisposable

from rxbp.flowables.refcountflowable import RefCountFlowable
from rxbp.init.initflowable import init_flowable
from rxbp.mixins.flowablemixin import FlowableMixin
from rxbp.multicast.flowables.connectableflowable import ConnectableFlowable
from rxbp.multicast.flowables.flatconcatnobackpressureflowable import \
    FlatConcatNoBackpressureFlowable
from rxbp.multicast.flowables.flatmergenobackpressureflowable import \
    FlatMergeNoBackpressureFlowable
from rxbp.multicast.mixins.flowablestatemixin import FlowableStateMixin
from rxbp.multicast.mixins.multicastmixin import MultiCastMixin
from rxbp.multicast.multicastobservable import MultiCastObservable
from rxbp.multicast.multicastobserver import MultiCastObserver
from rxbp.multicast.multicastobserverinfo import MultiCastObserverInfo
from rxbp.multicast.multicastsubscriber import MultiCastSubscriber
from rxbp.multicast.multicastsubscription import MultiCastSubscription
from rxbp.multicast.typing import MultiCastItem
from rxbp.observer import Observer
from rxbp.typing import ElementType


@dataclass
class CollectFlowablesMultiCast(MultiCastMixin):
    """
    On next and completed
    ---------------------

    Before first element received
    O----->O----->O
    1      2      3

    After first element received
    O----->O----->o----->o----->o----->o
    1      2      4      5      6      7

    1. previous multicast observer
    2. CollectFlowablesMultiCastObserver
    3. next multicast observer
    4. ConnectableObserver
    5. RefCountObserver
    6. FlatNoBackpressureObserver
    7. next flowable observer

    On error
    --------

    Before first element received
    O----->O----->O
    1      2      3

    After first element received
             *--->o
            /     3
    O----->O----->o----->o----->o----->o
    1      2      4      5      6      7


    """

    source: MultiCastMixin
    maintain_order: bool
    stack: List[FrameSummary]

    def unsafe_subscribe(self, subscriber: MultiCastSubscriber) -> MultiCastSubscription:
        subscription = self.source.unsafe_subscribe(subscriber=subscriber)

        @dataclass
        class CollectFlowablesMultiCastObserver(MultiCastObserver):
            next_observer: MultiCastObserver
            ref_count_disposable: RefCountDisposable
            maintain_order: bool
            stack: List[FrameSummary]

            def __post_init__(self):
                self.is_first = True
                self.inner_observer: Observer = None

            def on_next(self, item: MultiCastItem) -> None:
                if isinstance(item, list):
                    if len(item) == 0:
                        return

                    first_flowable_state = item[0]
                    flowable_states = item

                else:
                    try:
                        first_flowable_state = next(item)
                        flowable_states = chain([first_flowable_state], item)
                    except StopIteration:
                        return

                if isinstance(first_flowable_state, dict):
                    to_state = lambda s: s
                    from_state = lambda s: s

                elif isinstance(first_flowable_state, FlowableStateMixin):
                    to_state = lambda s: s.get_flowable_state()
                    from_state = lambda s: s.set_flowable_state(s)

                elif isinstance(first_flowable_state, list):
                    to_state = lambda l: {idx: elem for idx, elem in enumerate(l)}
                    from_state = lambda s: list(s[idx] for idx in range(len(s)))

                elif isinstance(first_flowable_state, FlowableMixin):
                    to_state = lambda s: {0: s}
                    from_state = lambda s: s[0]

                else:
                    to_state = lambda s: s
                    from_state = lambda s: s

                first_state = to_state(first_flowable_state)

                # UpstreamObserver --> ConnectableObserver --> RefCountObserver --> FlatNoBackpressureObserver

                @dataclass
                class ConnectableObserver(Observer):
                    underlying: Observer
                    outer_observer: MultiCastObserver

                    def connect(self):
                        pass

                    def on_next(self, elem: ElementType):
                        return self.underlying.on_next(elem)

                    def on_error(self, err):
                        self.outer_observer.on_error(err)
                        self.underlying.on_error(err)

                    def on_completed(self):
                        self.underlying.on_completed()

                conn_observer = ConnectableObserver(
                    underlying=None,
                    outer_observer=self.next_observer,
                )

                # buffered_observer = BufferedObserver(
                #     underlying=conn_observer,
                #     scheduler=subscriber.multicast_scheduler,
                #     subscribe_scheduler=subscriber.multicast_scheduler,
                #     buffer_size=1000,
                # )

                self.inner_observer = conn_observer

                inner_disposable = self.ref_count_disposable.disposable
                conn_flowable = ConnectableFlowable(
                    conn_observer=conn_observer,
                    disposable=inner_disposable,
                )

                if 1 < len(first_state):
                    shared_flowable = RefCountFlowable(conn_flowable, stack=self.stack)
                else:
                    shared_flowable = conn_flowable

                def gen_flowables():
                    for key in first_state.keys():
                        def selector(v: FlowableStateMixin, key=key):
                            flowable = to_state(v)[key]
                            return flowable

                        if self.maintain_order:
                            flattened_flowable = FlatConcatNoBackpressureFlowable(
                                source=shared_flowable,
                                selector=selector,
                                subscribe_scheduler=subscriber.source_scheduler,
                            )
                        else:
                            flattened_flowable = FlatMergeNoBackpressureFlowable(
                                source=shared_flowable,
                                selector=selector,
                                subscribe_scheduler=subscriber.source_scheduler,
                            )

                        flowable = init_flowable(RefCountFlowable(flattened_flowable, stack=self.stack))
                        yield key, flowable

                flowable_imitations = from_state(dict(gen_flowables()))
                self.next_observer.on_next([flowable_imitations])
                self.next_observer.on_completed()

                # observable didn't get subscribed
                if conn_observer.underlying is None:
                    def on_next_if_not_subscribed(self, val):
                        pass

                    self.on_next = types.MethodType(on_next_if_not_subscribed, self)

                    # if there is no inner subscriber, dispose the source
                    inner_disposable.dispose()
                    return

                self.is_first = False

                _ = self.inner_observer.on_next(flowable_states)

                def on_next_after_first(self, elem: MultiCastItem):
                    _ = self.inner_observer.on_next(elem)

                self.on_next = types.MethodType(on_next_after_first, self)  # type: ignore

            def on_error(self, exc: Exception) -> None:
                if self.is_first:
                    self.next_observer.on_error(exc)
                else:
                    self.inner_observer.on_error(exc)

            def on_completed(self) -> None:
                if self.is_first:
                    self.next_observer.on_completed()
                else:
                    self.inner_observer.on_completed()

        @dataclass
        class CollectFlowablesMultiCastObservable(MultiCastObservable):
            source: MultiCastObservable
            maintain_order: bool
            stack: List[FrameSummary]

            def observe(self, observer_info: MultiCastObserverInfo) -> rx.typing.Disposable:
                disposable = SingleAssignmentDisposable()

                # dispose source if MultiCast sink gets disposed and all inner Flowable sinks
                # are disposed
                ref_count_disposable = RefCountDisposable(disposable)

                disposable.disposable = self.source.observe(observer_info.copy(
                    observer=CollectFlowablesMultiCastObserver(
                        next_observer=observer_info.observer,
                        ref_count_disposable=ref_count_disposable,
                        maintain_order=self.maintain_order,
                        stack=self.stack,
                    ),
                ))

                return ref_count_disposable

        return subscription.copy(
            observable=CollectFlowablesMultiCastObservable(
                source=subscription.observable,
                maintain_order=self.maintain_order,
                stack=self.stack,
            )
        )

        # def func(lifted_obs: MultiCastObservable, first: Any):
        #     if isinstance(first, dict):
        #         to_state = lambda s: s
        #         from_state = lambda s: s
        #
        #     elif isinstance(first, FlowableStateMixin):
        #         to_state = lambda s: s.get_flowable_state()
        #         from_state = lambda s: s.set_flowable_state(s)
        #
        #     elif isinstance(first, list):
        #         to_state = lambda l: {idx: elem for idx, elem in enumerate(l)}
        #         from_state = lambda s: list(s[idx] for idx in range(len(s)))
        #
        #     elif isinstance(first, FlowableMixin):
        #         to_state = lambda s: {0: s}
        #         from_state = lambda s: s[0]
        #
        #     else:
        #         to_state = lambda s: s
        #         from_state = lambda s: s
        #
        #     first_state = to_state(first)
        #
        #     conn_observer = ConnectableObserver(
        #         underlying=None,
        #         scheduler=subscriber.multicast_scheduler,
        #         # subscribe_scheduler=multicast_scheduler,
        #     )
        #
        #     observer = BufferedObserver(
        #         underlying=conn_observer,
        #         scheduler=subscriber.multicast_scheduler,
        #         subscribe_scheduler=subscriber.multicast_scheduler,
        #         buffer_size=1000,
        #     )
        #
        #     # def action(_, __):
        #     disposable = lifted_obs.observe(MultiCastObserverInfo(observer=observer))
        #
        #     conn_flowable = ConnectableFlowable(
        #         conn_observer=conn_observer,
        #         disposable=disposable,
        #     )
        #
        #     # multicast_scheduler.schedule(action)
        #
        #     # # subscribe to source MultiCast immediately
        #     # source_flowable = FromMultiCastToFlowable(lifted_obs, buffer_size=1000)
        #     # subscription = source_flowable.unsafe_subscribe(subscriber=init_subscriber(
        #     #     scheduler=multicast_scheduler,
        #     #     subscribe_scheduler=multicast_scheduler,
        #     # ))
        #     # subscription.observable.observe(init_observer_info(
        #     #     observer=conn_observer,
        #     # ))
        #
        #     if 1 < len(first_state):
        #         shared_flowable = RefCountFlowable(conn_flowable, stack=self.stack)
        #     else:
        #         shared_flowable = conn_flowable
        #
        #     def gen_flowables():
        #         for key in first_state.keys():
        #             def selector(v: FlowableStateMixin, key=key):
        #                 flowable = to_state(v)[key]
        #                 return flowable
        #
        #             if self.maintain_order:
        #                 flattened_flowable = FlatConcatNoBackpressureFlowable(
        #                     source=shared_flowable,
        #                     selector=selector,
        #                     subscribe_scheduler=subscriber.source_scheduler,
        #                 )
        #             else:
        #                 flattened_flowable = FlatMergeNoBackpressureFlowable(
        #                     source=shared_flowable,
        #                     selector=selector,
        #                     subscribe_scheduler=subscriber.source_scheduler,
        #                 )
        #
        #             flowable = init_flowable(RefCountFlowable(flattened_flowable, stack=self.stack))
        #             yield key, flowable
        #
        #     return from_state(dict(gen_flowables()))

        # return subscription.copy(observable=LiftedMultiCastObservable(
        #     source=subscription.observable,
        #     func=func,
        #     scheduler=subscriber.multicast_scheduler,
        # ))
