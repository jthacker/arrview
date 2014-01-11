from collections import Mapping, Set, Sequence 

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
    s = obj.__class__.__name__
    s += '(%s)' % ','.join(['%s=%r' % (prop,getattr(obj,prop)) for prop in props])
    return s


def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)
