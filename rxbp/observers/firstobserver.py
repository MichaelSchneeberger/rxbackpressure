from dataclasses import dataclass
from traceback import FrameSummary
from typing import List

from rx.internal import SequenceContainsNoElementsError

from rxbp.acknowledgement.continueack import continue_ack
from rxbp.acknowledgement.stopack import stop_ack
from rxbp.observer import Observer
from rxbp.typing import ElementType
from rxbp.utils.tooperatorexception import to_operator_exception


@dataclass
class FirstObserver(Observer):
    observer: Observer
    stack: List[FrameSummary]
    is_first: bool

    def on_next(self, elem: ElementType):
        if isinstance(elem, list):
            elem_list = elem

        else:
            try:
                elem_list = list(elem)
            except Exception as exc:
                self.observer.on_error(exc)
                return stop_ack

        if 0 < len(elem_list):
            self.is_first = False
            self.observer.on_next([elem_list[0]])
            self.observer.on_completed()
            return stop_ack

        else:
            return continue_ack

    def on_error(self, exc):
        return self.observer.on_error(exc)

    def on_completed(self):
        if self.is_first:
            try:
                raise SequenceContainsNoElementsError(to_operator_exception(
                    message='',
                    stack=self.stack,
                ))

            except Exception as exc:
                self.observer.on_error(exc)