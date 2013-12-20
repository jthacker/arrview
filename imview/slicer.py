from collections import namedtuple
import numpy as np
from traits.api import (HasTraits,
        Instance, Int, List, Property, cached_property)
from .tools import unique

ArrayDims = namedtuple('ArrayDims', ('x','y','free'))

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
    dims = Instance(ArrayDims)
    slc  = Instance(SliceTuple)
    view = Property(depends_on='[dims,slc]')

    def __init__(self, arr, xdim=1, ydim=0):
        '''Wraps a numpy array to keep track of a 2D slice.
        The viewing dimension default to x=1 and y=0'''
        assert arr.ndim >= 2, 'Arr must have at least 2 dimensions'
        assert xdim != ydim, 'xDim and yDim must be different'
        super(Slicer, self).__init__()

        self._arr = arr
        self.slc = SliceTuple([0]*arr.ndim)
        self.dims = ArrayDims(xdim, ydim, self._get_freedims(xdim,ydim))
        self.set_viewdims(xdim,ydim)

    def _get_freedims(self, xdim, ydim):
        return set(range(self._arr.ndim)) - set((xdim,ydim))
       
    def set_viewdims(self, xdim, ydim):
        '''Select a 2D view from the higher dimension array.
        View dims are swapped if xDim > yDim'''
        assert 0 <= xdim < self._arr.ndim
        assert 0 <= ydim < self._arr.ndim
        
        cxdim,cydim,_ = self.dims
        slc = list(self.slc)
        slc[cxdim] = 0
        slc[cydim] = 0
        slc[xdim] = slice(None)
        slc[ydim] = slice(None)
        self.slc = SliceTuple(slc)
        self.dims = ArrayDims(xdim,ydim,self._get_freedims(xdim,ydim))

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
        assert 0 <= dim < self._arr.ndim, 'Dim [%d] must be in [0,%d)' % (dim, self._arr.ndim)

        xdim,ydim,_ = self.dims
        if dim != xdim and dim != ydim:
            dMax = self._arr.shape[dim]
            if val >= dMax:
                val = dMax - 1
            if val < 0:
                val = 0
            slc = list(self.slc)
            slc[dim] = val
            self.slc = SliceTuple(slc)

    def dim_size(self, dim):
        '''Get the size of a specific dim'''
        assert 0 <= dim <= self._arr.ndim, '0<=d<=%d but was d=%d' % (self._arr.ndim, dim)
        return self._arr.shape[dim]

    @cached_property
    def _get_view(self):
        '''Get the current view of the array'''
        a = self._arr[self.slc]
        xdim,ydim,_ = self.dims
        return a.transpose() if ydim > xdim else a

    def __repr__(self):
        return "Slicer(arr=%r, slice=%r, dims=%r)" % (self._arr, self.slc, self.dims)

