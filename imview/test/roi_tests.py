import numpy as np
from numpy.testing import assert_array_equal
from traits.testing.unittest_tools import unittest
from traits.testing.api import UnittestTools

from ..roi import ROI, ROIManager, ROIInfo, SlicePoly
from ..slicer import Slicer

class TestROI(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.sqrPoly = np.array([(0,0),(0,1),(1,1),(1,0)])

    def test_mask(self):
        roi = ROI()
        arr = np.zeros((3,3,3))
        slicer = Slicer(arr)
        roi.set_poly(slicer.slc, self.sqrPoly)

        mask = np.ones(slicer.shape)
        mask[:1,:1,0] = 0
        expected = np.ma.array(arr, mask=mask)

        assert_array_equal(expected, roi.mask(arr))

    def test_maskdifferent_freedim(self):
        roi = ROI()
        arr = np.zeros((3,3,3))
        slicer = Slicer(arr)
        slicer.set_freedim(2,1)
        roi.set_poly(slicer.slc, self.sqrPoly)

        mask = np.ones(slicer.shape)
        mask[:1,:1,1] = 0
        expected = np.ma.array(arr, mask=mask)

        assert_array_equal(expected, roi.mask(arr))

    def test_coordinate_order(self):
        '''The specified coordinates should be (row1,col1), (row2,col2), ...
        '''
        roi = ROI()
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])
        arr = np.zeros((3,3))
        slicer = Slicer(arr)

        roi.set_poly(slicer.slc, poly)
        mask = np.ones(slicer.shape)
        mask[0,:] = 0
        expected = np.ma.array(arr, mask=mask)

        assert_array_equal(expected, roi.mask(arr))

    def test_poly_changed(self):
        roi = ROI()
        slicer = Slicer(np.zeros((2,2,2)))
        with self.assertTraitChanges(roi, 'slicepoly') as result:
            roi.set_poly(slicer.slc, self.sqrPoly)
       
        slicepoly = SlicePoly(slicer.slc, self.sqrPoly)
        expected = [(roi, 'slicepoly', None, slicepoly)]
        self.assertSequenceEqual(result.events, expected)

    def test_mask_transpose_when_swapping_view_dims(self):
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])
        arr = np.zeros((3,3))
        slicer = Slicer(arr)

        roi = ROI()
        roi.set_poly(slicer.slc, poly)
        mask = np.ones(slicer.shape)
        mask[0,:] = 0
        expected = np.ma.array(arr, mask=mask)
        assert_array_equal(expected, roi.mask(arr))
       
        # Swap the slicer dimensions, should transpose mask
        slicer.set_viewdims(slicer.slc.ydim, slicer.slc.xdim)
        roi = ROI()
        roi.set_poly(slicer.slc, poly)
        assert_array_equal(expected.T, roi.mask(arr))


class TestROIManager(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.sqrPoly = np.array([(0,0),(0,1),(1,1),(1,0)])

    def test_new(self):
        roimngr = ROIManager()
        slicer = Slicer(np.zeros((3,3)))

        with self.assertTraitChanges(roimngr, 'rois[]') as result:
            roimngr.new(slicer, self.sqrPoly)

        expected = [(roimngr, 'rois_items', [], [roimngr.rois[0]])]
        self.assertSequenceEqual(result.events, expected)


class TestROIInfo(unittest.TestCase, UnittestTools):
    def setUp(self):
        arr = np.arange(2*3*4).reshape(2,3,4)
        slicer = Slicer(arr)
        roi = ROI()
        poly = np.array([(0,0),(0,2),(2,2),(2,0)])
        roi.set_poly(slicer.slc, poly)
        self.stats = ROIInfo(arr=arr, roi=roi)

    def test_mean(self):
        self.assertAlmostEqual(self.stats.mean, 8.0)

    def test_std(self):
        self.assertAlmostEqual(self.stats.std, 6.324555320336759)

    def test_area(self):
        self.assertEqual(self.stats.count, 4)

