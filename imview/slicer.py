from collections import namedtuple
import numpy as np
from traits.api import (HasTraits,
        Instance, Int, List, Property, cached_property)
from .util import unique, rep

class SliceTuple(tuple):
    def _repr(self, s):
        if isinstance(s, slice):
            attrs = (s.start, s.stop, s.stop)
            attrs = [a if a != None else '' for a in attrs]
            rep = ':'.join(attrs)
            return ':' if rep == '::' else rep
        else:
            return repr(s)

    def __repr__(self):
        return 'ArraySlice(%s)' % ','.join(map(self._repr, self))


class Slicer(HasTraits):
    xdim = Int
    ydim = Int
    slc = Instance(SliceTuple)
    freedims = Property()
    shape = Property()
    ndim = Property()
    view = Property(depends_on='[slc,xdim,ydim]')

    def __init__(self, arr, xdim=1, ydim=0):
        '''Wraps a numpy array to keep track of a 2D slice.
        The viewing dimension default to x=1 and y=0'''
        assert arr.ndim >= 2, 'arr must be at least 2 dimensions'
        assert xdim != ydim, 'diminsion x must be different from y'
        super(Slicer, self).__init__()

        self._arr = arr
        self._set_dims([0]*self.ndim, xdim, ydim)

    def _get_ndim(self):
        return self._arr.ndim
    
    def _get_shape(self):
        return self._arr.shape

    def _get_freedims(self):
        return [i for i,x in enumerate(self.slc) if x != slice(None)]

    def set_viewdims(self, xdim, ydim):
        '''Select a 2D view from the higher dimension array.
        View dims are swapped if xDim > yDim'''
        assert 0 <= xdim < self.ndim
        assert 0 <= ydim < self.ndim
        
        slc = list(self.slc)
        slc[self.xdim] = 0
        slc[self.ydim] = 0
        self._set_dims(slc, xdim, ydim)

    def _set_dims(self, slc, xdim, ydim):
        slc[xdim] = slice(None)
        slc[ydim] = slice(None)
        self.xdim = xdim
        self.ydim = ydim
        self.slc = SliceTuple(slc)

    def set_freedim(self, dim, val):
        '''Set the dimension dim to the value val.
        This method allows for easy updating of the 2D view on one of the
        free dimensions. It also verifies that dim is not bigger than
        the dimension of the array and that val is within the range of the
        dimension selected by dim.

        If val is outside the bounds of the dimension selected by dim, then it will
        be anchored autmatically to either 0 or max of the dimension range depending
        on which one it is closer to.
        '''
        assert 0 <= dim < self.ndim, 'Dim [%d] must be in [0,%d)' % (dim, self.ndim)

        xdim,ydim = self.xdim,self.ydim
        if dim != xdim and dim != ydim:
            dMax = self.shape[dim]
            if val >= dMax:
                val = dMax - 1
            if val < 0:
                val = 0
            slc = list(self.slc)
            slc[dim] = val
            self.slc = SliceTuple(slc)

    def dim_size(self, dim):
        '''Get the size of a specific dim'''
        assert 0 <= dim <= self.ndim, '0<=d<=%d but was d=%d' % (self.ndim, dim)
        return self.shape[dim]

    @cached_property
    def _get_view(self):
        '''Get the current view of the array'''
        a = self._arr[self.slc]
        return a.transpose() if self.ydim > self.xdim else a

    def __repr__(self):
        return rep(self, ['_arr','xdim','ydim','slc'])
