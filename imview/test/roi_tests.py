import numpy as np
from numpy.testing import assert_array_equal
from traits.testing.unittest_tools import unittest
from traits.testing.api import UnittestTools

from ..roi import ROI, ROIManager, SlicePoly
from ..slicer import Slicer

class TestROI(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.sqrPoly = np.array([(0,0),(0,1),(1,1),(1,0)])

    def test_to_mask(self):
        roi = ROI(name='test')
        slicer = Slicer(np.zeros((3,3,3)))
        roi.set_poly(slicer, self.sqrPoly)

        expectedMask = np.zeros(slicer.shape)
        expectedMask[:1,:1,0] = 1

        assert_array_equal(expectedMask, roi.to_mask(slicer.shape))

    def test_to_mask_different_freedim(self):
        roi = ROI(name='test')
        slicer = Slicer(np.zeros((3,3,3)))
        slicer.set_freedim(2,1)
        roi.set_poly(slicer, self.sqrPoly)

        expectedMask = np.zeros(slicer.shape)
        expectedMask[:1,:1,1] = 1

        assert_array_equal(expectedMask, roi.to_mask(slicer.shape))

    def test_coordinate_order(self):
        '''The specified coordinates should be (row1,col1), (row2,col2), ...
        '''
        roi = ROI(name='test')
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])
        slicer = Slicer(np.zeros((3,3)))

        roi.set_poly(slicer, poly)
        expectedMask = np.zeros(slicer.shape)
        expectedMask[0,:] = 1

        assert_array_equal(expectedMask, roi.to_mask(slicer.shape))

    def test_poly_changed(self):
        roi = ROI(name='test')
        slicer = Slicer(np.zeros((2,2,2)))
        with self.assertTraitChanges(roi, 'slicepoly') as result:
            roi.set_poly(slicer, self.sqrPoly)
       
        slicepoly = SlicePoly(slicer.slc, self.sqrPoly)
        expected = [(roi, 'slicepoly', None, slicepoly)]
        self.assertSequenceEqual(result.events, expected)

    def test_mask_transpose_when_swapping_view_dims(self):
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])
        slicer = Slicer(np.zeros((3,3)))

        roi = ROI(name='test')
        roi.set_poly(slicer, poly)
        expectedMask = np.zeros(slicer.shape)
        expectedMask[0,:] = 1
        assert_array_equal(expectedMask, roi.to_mask(slicer.shape))
       
        # Swap the slicer dimensions, should transpose mask
        slicer.set_viewdims(slicer.slc.ydim, slicer.slc.xdim)
        roi = ROI(name='test')
        roi.set_poly(slicer, poly)
        assert_array_equal(expectedMask.T, roi.to_mask(slicer.shape))


class TestROIManager(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.sqrPoly = np.array([(0,0),(0,1),(1,1),(1,0)])

    def test_add(self):
        roimngr = ROIManager()
        roi = ROI(name='Test')

        with self.assertTraitChanges(roimngr, 'rois[]') as result:
            roimngr.add(roi)

        expected = [(roimngr, 'rois_items', [], [roi])]
        self.assertSequenceEqual(result.events, expected)
