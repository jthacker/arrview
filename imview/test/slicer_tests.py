import numpy as np
from numpy.testing import assert_array_equal
from ..slicer import Slicer,SliceTuple
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
        xdim,ydim = slicer.xdim,slicer.ydim
        assert xdim == 1, 'xdim is %d, but should be 1' % xdim
        assert ydim == 0, 'ydim is %d, but should be 0' % ydim

    def test_set_viewdims(self):
        slicer = Slicer(self.arr)
        slicer.set_viewdims(0,1)
        xdim,ydim = slicer.xdim,slicer.ydim
        assert xdim == 0, 'xdim is %d, but should be 0' % xDim
        assert ydim == 1, 'ydim is %d, but should be 1' % yDim

    def test_freedims_change_when_viewdims_set(self):
        arr = np.arange(100).reshape([5,2,5,2])
        slicer = Slicer(arr)
        slicer.set_viewdims(1,3)
        assert SliceTuple([0,slice(None),0,slice(None)]) == slicer.slc
        assert slicer.freedims == [0,2]

    def test_swap_dims(self):
        slicer = Slicer(self.arr)
        assert_array_equal(self.arr, slicer.view)
        # Swap the dimensions
        xDimOrig,yDimOrig = slicer.xdim, slicer.ydim
        slicer.set_viewdims(yDimOrig, xDimOrig)
        xDim,yDim = slicer.xdim, slicer.ydim
        assert xDim == yDimOrig
        assert yDim == xDimOrig
        assert_array_equal(self.arr.T, slicer.view)

    def test_dims_changed_event(self):
        slicer = Slicer(self.arr)
        with self.assertTraitChanges(slicer, '[xdim,ydim]') as result:
            slicer.set_viewdims(0,1)
        slc = SliceTuple([slice(None),slice(None)])
        expected = [(slicer, 'xdim', 1, 0),
                    (slicer, 'ydim', 0, 1)]
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
