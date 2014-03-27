from collections import namedtuple
import numpy as np
from .util import unique, rep


class SliceTuple(tuple):
    def __init__(self, *args, **kwargs):
        super(SliceTuple, self).__init__(*args, **kwargs)
        self._xdim = self.index('x')
        self._ydim = self.index('y')

    @property
    def xdim(self):
        return self._xdim

    @property
    def ydim(self):
        return self._ydim
   
    @property
    def viewdims(self):
        return (self.xdim, self.ydim)

    @property
    def is_transposed(self):
        return self.ydim > self.xdim

    def viewarray(self, arr):
        '''Transforms arr from Array coordinates to Screen coordinates
        using the transformation described by this object'''
        assert arr.ndim == len(self), 'dimensions of arr must equal the length of this object'
        viewdims = self.viewdims
        arrayslice = [slice(None) if d in viewdims else x for d,x in enumerate(self)]
        a = arr[arrayslice]
        return a.transpose() if self.is_transposed else a

    def screen_coords_to_array_coords(self, x, y):
        '''Transforms arr of Screen coordinates to Array indicies'''
        r,c = (y,x) if self.is_transposed else (x,y)
        return r,c

    def slice_from_screen_coords(self, x, y, arr):
        slc = list(self)
        rdim,cdim = self.screen_coords_to_array_coords(*self.viewdims)
        slc[rdim],slc[cdim] = self.screen_coords_to_array_coords(x,y)
        return slc

    #TODO: deprecate
    def is_transposed_view_of(self, slc):
        '''Test if slc is equal to this object but with swapped x and y dims swapped
        Args:
        slc -- (SliceTuple)

        Returns:
        True if slc equals this object with swapped view dimensions, otherwise False.

        Examples:
        >>> a = SliceTuple(('x','y',0,1))
        >>> b = SliceTuple(('y','x',0,1))
        >>> c = SliceTuple(('y','x',0,20))
        >>> a.is_transposed_view_of(b)
        True
        >>> b.is_transposed_view_of(a)
        True
        >>> a.is_transposed_view_of(c)
        False
        '''
        s = list(self)
        # Swap the axes
        s[self.xdim],s[self.ydim] = s[self.ydim],s[self.xdim]
        return s == list(slc)

    @property
    def freedims(self):
        return tuple(i for i,x in enumerate(self) if i not in self.viewdims)

    #TODO: @deprecated: Get rid of this method
    @staticmethod
    def from_arrayslice(arrslice, viewdims):
        '''Replace the dims from viedims in arrslice.
        Args:
        arrslice -- a tuple used for slicing a numpy array. The method arrayslice
                    returns examples of this type of array
        viewdims -- a len 2 tuple with the first position holding the dimension
                    number that corresponds to the x dimension and the second is
                    the y dimension.
        Returns:
        arrslice with each dim in viewdims replaced by 'x' or 'y'

        For example:
        >>> arrslice = (0,0,0,0)
        >>> viewdims = (1,0)
        >>> from_arrayslice(arrslice, viewdims)
        ('y','x',0,0)
        '''
        slc = list(arrslice)
        xdim,ydim = viewdims
        slc[xdim],slc[ydim] = 'x','y'
        return SliceTuple(slc)


class Slicer(object):
    def __init__(self, arr, xdim=1, ydim=0):
        '''Wraps a numpy array to keep track of a 2D slice.
        The viewing dimension default to x=1 and y=0'''
        assert arr.ndim >= 2, 'arr must be at least 2 dimensions'
        assert xdim != ydim, 'diminsion x must be different from y'
        self._arr = arr
        self._set_dims([0]*self.ndim, xdim, ydim)

    def _set_dims(self, slc, xdim, ydim):
        slc[xdim] = 'x'
        slc[ydim] = 'y'
        self.slc = SliceTuple(slc)

    @property
    def ndim(self):
        return self.arr.ndim
   
    @property
    def shape(self):
        return self.arr.shape

    @property
    def arr(self):
        return self._arr

    @property
    def view(self):
        '''Get the current view of the array'''
        return self.slc.viewarray(self.arr)

    def set_viewdims(self, xdim, ydim):
        '''Select a 2D view from the higher dimension array.
        View dims are swapped if xDim > yDim'''
        assert 0 <= xdim < self.ndim
        assert 0 <= ydim < self.ndim
        
        slc = list(self.slc)
        slc[self.slc.xdim] = 0
        slc[self.slc.ydim] = 0
        self._set_dims(slc, xdim, ydim)

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

        xdim,ydim = self.slc.viewdims
        if dim != xdim and dim != ydim:
            dMax = self.shape[dim]
            if val >= dMax:
                val = dMax - 1
            if val < 0:
                val = 0
            slc = list(self.slc)
            slc[dim] = val
            self.slc = SliceTuple(slc)

    def __repr__(self):
        return rep(self, ['arr','slc'])
