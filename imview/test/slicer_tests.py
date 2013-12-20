import numpy as np
from numpy.testing import assert_array_equal
from ..slicer import Slicer,ArrayDims,SliceTuple
from traits.testing.unittest_tools import unittest
from traits.testing.api import UnittestTools

class TestSlicer(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.arr = np.arange(10).reshape([5,2])

    def test_view(self):
        slicer = Slicer(self.arr)
        assert_array_equal(self.arr, slicer.view)

    def test_set_viewdims_transpose(self):
        slicer = Slicer(self.arr)
        slicer.set_viewdims(0,1)
        assert_array_equal(self.arr.T, slicer.view)

    def test_viewdims_default(self):
        slicer = Slicer(self.arr)
        xDim,yDim,_ = slicer.dims
        assert xDim == 1, 'xDim is %d, but should be 1' % xDim
        assert yDim == 0, 'yDim is %d, but should be 0' % yDim

    def test_set_viewdims(self):
        slicer = Slicer(self.arr)
        slicer.set_viewdims(0,1)
        xDim,yDim,_ = slicer.dims
        assert xDim == 0, 'xDim is %d, but should be 0' % xDim
        assert yDim == 1, 'yDim is %d, but should be 1' % yDim

    def test_freedims_default(self):
        arr = np.arange(100).reshape([5,2,5,2])
        slicer = Slicer(arr)
        _,_,freedims = slicer.dims
        assert set((2,3)) == freedims

    def test_freedims_change_when_viewdims_set(self):
        arr = np.arange(100).reshape([5,2,5,2])
        slicer = Slicer(arr)
        slicer.set_viewdims(1,3)
        _,_,freedims = slicer.dims
        assert set((0,2)) == freedims

    def test_swap_dims(self):
        slicer = Slicer(self.arr)
        assert_array_equal(self.arr, slicer.view)
        # Swap the dimensions
        xDimOrig,yDimOrig,_ = slicer.dims
        slicer.set_viewdims(yDimOrig, xDimOrig)
        xDim,yDim,_ = slicer.dims
        assert xDim == yDimOrig
        assert yDim == xDimOrig
        assert_array_equal(self.arr.T, slicer.view)

    def test_dims_changed_event(self):
        slicer = Slicer(self.arr)
        with self.assertTraitChanges(slicer, 'dims') as result:
            slicer.set_viewdims(0,1)
        expected = [(slicer, 'dims', ArrayDims(1,0,set()), ArrayDims(0,1,set()))]
        self.assertSequenceEqual(result.events, expected)

    def test_slc_changed_event(self):
        arr = np.arange(30).reshape(5,3,2)
        slicer = Slicer(arr)
        with self.assertTraitChanges(slicer, 'slc') as result:
            slicer.set_freedim(2,1)
        expected = [(slicer, 'slc', 
            SliceTuple((slice(None),slice(None),0)),
            SliceTuple((slice(None),slice(None),1)))]
        self.assertSequenceEqual(result.events, expected)

    def test_viewdims_changed_view_should_update(self):
        slicer = Slicer(self.arr)
        with self.assertTraitChanges(slicer, 'view') as result:
            slicer.set_viewdims(0,1)
        assert_array_equal(self.arr.T, slicer.view)

    def test_freedim_changed_view_should_update(self):
        arr = np.arange(30).reshape(5,3,2)
        slicer = Slicer(arr)
        with self.assertTraitChanges(slicer, 'view') as result:
            slicer.set_freedim(2,1)
        assert_array_equal(arr[:,:,1], slicer.view)
