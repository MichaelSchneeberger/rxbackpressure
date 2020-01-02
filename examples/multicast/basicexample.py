"""
This example demonstrates a use-case of sharing a Flowable, inside
the MultiCast object.

The MultiCast object can be thought of a container of Flowables. A Flowable
is sharable if it becomes hot once it is subscribed for the first time.
Sharable Flowables only life in the MultiCast object.

Examples:
- `from_flowable` creates a MultiCast containing one of more sharable Flowables
  inside.
- `empty` creates an empty MultiCast. Non-sharable Flowables can be added to a
  MultiCast by using the `map` operator.
- Sharable Flowables can also be defined by using the MultiCastContext. A
  MultiCastContext is obtained by using the `map_with_context` operator.

"""

from typing import Dict

import rxbp
from rxbp.flowable import Flowable
from rxbp.multicast.flowabledict import FlowableDict
from rxbp.multicastcontext import MultiCastContext

base = FlowableDict({'input': rxbp.range(10)})


def mod_by_2_and_add_100(fdict: Dict[str, Flowable], context: MultiCastContext):

    mod2 = fdict['input'].pipe(
        rxbp.op.filter(lambda v: v % 2 == 0),
    ).share(bind_to=context)

    add100 = fdict['input'].pipe(
        rxbp.op.map(lambda v: v + 100),
    ).share(bind_to=context)

    return {'mod2': mod2, 'add100': add100, **fdict}


result = rxbp.multicast.from_flowable(base).pipe(               # start the multicast from a Flowable
    rxbp.multicast.op.map_with_context(mod_by_2_and_add_100),   # create more Flowables from the initial Flowable
    rxbp.multicast.op.map(lambda fdict: fdict['mod2']),         # select single Flowable for output
).to_flowable().run()                                           # convert multi-cast to a (single) flowable

print(result)
