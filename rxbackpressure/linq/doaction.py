from rx import Observable
from rx.internal import extensionmethod

from rxbackpressure.core.anonymousbackpressureobservable import \
    AnonymousBackpressureObservable
from rxbackpressure.core.backpressureobservable import BackpressureObservable


@extensionmethod(BackpressureObservable)
def do_action(self, on_next=None, on_completed=None):

    def subscribe_func(observer, scheduler=None):

        def on_next2(value):
            if on_next:
                on_next(value)
            observer.on_next(value)

        def on_completed2():
            # print(on_next)
            if on_completed:
                on_completed()
            observer.on_completed()

        def subscribe_bp(backpressure, scheduler=None):
            return observer.subscribe_backpressure(backpressure, scheduler)

        return self.subscribe(on_next2, observer.on_error, on_completed=on_completed2, subscribe_bp=subscribe_bp,
                              scheduler=scheduler)

    return AnonymousBackpressureObservable(subscribe_func=subscribe_func)