from collections import Mapping, Set, Sequence 

# dual python 2/3 compatability, inspired by the "six" library
string_types = (str, unicode) if str is bytes else (str, bytes)
iteritems = lambda mapping: getattr(mapping, 'iteritems', mapping.items)()

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

def objwalk(obj, path=(), memo=None):
    if memo is None:
        memo = set()
    iterator = None
    if isinstance(obj, Mapping):
        iterator = iteritems
    elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, string_types):
        iterator = enumerate
    if iterator:
        if id(obj) not in memo:
            memo.add(id(obj))
            for path_component, value in iterator(obj):
                for result in objwalk(value, path + (path_component,), memo):
                    yield result
            memo.remove(id(obj))
    else:
        yield path, obj
