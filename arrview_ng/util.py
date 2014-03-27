from collections import namedtuple
from PySide.QtCore import QPointF, QPoint

from collections import Iterable
from itertools import chain

Scale = namedtuple('Scale', ['low','high'])


class QPointFTuple(QPointF):
    def __iter__(self):
        return iter((self.x(), self.y()))


class QPointTuple(QPoint):
    def __iter__(self):
        return iter((self.x(), self.y()))



def unique(iterable):
    '''Returns true or false if the items in the iterable are unique'''
    return len(iterable) == len(set(iterable))


def weave(item, iterable):
    '''Put item inbetween each element of iterable.
    Args:
    item     -- an object to weave in between the elements of iterable
    iterable -- any iterable object. If elements are callable then they
                are called before being returned
    Returns:
    A generator with item woven between elements of iterable.'''
    for i,elem in enumerate(iterable):
        yield elem
        if i < len(iterable) - 1:
            if hasattr(item, '__call__'):
                yield item()
            else:
                yield item


def rep(obj, props):
    '''A quick way to build a repr for a class
    Args:
    obj   -- object to make repr for
    props -- list of property names in object
    
    Returns:
    A string representation of the class and the specified properties
    '''
    s = obj.__class__.__name__
    s += '(%s)' % ','.join(['%s=%r' % (prop,getattr(obj,prop)) for prop in props])
    return s


def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)


def toiterable(*objs):
    def convert(obj):
        if isinstance(obj, Iterable):
            return obj
        else:
            return tuple([obj])
    return chain(*map(convert, objs))
