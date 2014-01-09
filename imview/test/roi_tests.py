import numpy as np
import tempfile
from numpy.testing import assert_array_equal
from traits.testing.unittest_tools import unittest
from traits.testing.api import UnittestTools

from ..roi import ROI, ROIManager, ROIPersistence
from ..slicer import Slicer

class TestROI(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.sqrPoly = np.array([(0,0),(0,1),(1,1),(1,0)])

    def test_mask(self):
        arr = np.zeros((3,3,3))
        slicer = Slicer(arr)
        roi = ROI(slc=slicer.slc, poly=self.sqrPoly, slicer=slicer)

        mask = np.ones(slicer.shape)
        mask[:1,:1,0] = 0
        expected = np.ma.array(arr, mask=mask)

        assert_array_equal(expected, roi.masked(arr))

    def test_maskdifferent_freedim(self):
        arr = np.zeros((3,3,3))
        slicer = Slicer(arr)
        slicer.set_freedim(2,1)
        roi = ROI(slc=slicer.slc, poly=self.sqrPoly, slicer=slicer)

        mask = np.ones(slicer.shape)
        mask[:1,:1,1] = 0
        expected = np.ma.array(arr, mask=mask)

        assert_array_equal(expected, roi.masked(arr))

    def test_coordinate_order(self):
        '''The specified coordinates should be (row1,col1), (row2,col2), ...
        '''
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])
        arr = np.zeros((3,3))
        slicer = Slicer(arr)

        roi = ROI(slc=slicer.slc, poly=poly, slicer=slicer)
        mask = np.ones(slicer.shape)
        mask[0,:] = 0
        expected = np.ma.array(arr, mask=mask)

        assert_array_equal(expected, roi.masked(arr))

    def test_poly_changed(self):
        slicer = Slicer(np.zeros((2,2,2)))
        # An invalid division results when calculating std-dev for an
        with np.errstate(invalid='ignore'):
            roi = ROI(slicer=slicer, slc=slicer.slc, poly=np.array([]))
            with self.assertTraitChanges(roi, 'poly') as result:
                roi.set(slc=slicer.slc, poly=self.sqrPoly)
            assert_array_equal(self.sqrPoly, result.event[3])

    def test_mask_transpose_when_swapping_view_dims(self):
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])
        arr = np.zeros((3,3))
        slicer = Slicer(arr)

        roi = ROI(slc=slicer.slc, poly=poly, slicer=slicer)
        mask = np.ones(slicer.shape)
        mask[0,:] = 0
        expected = np.ma.array(arr, mask=mask)
        assert_array_equal(expected, roi.masked(arr))
       
        # Swap the slicer dimensions, should transpose mask
        slicer.set_viewdims(slicer.slc.ydim, slicer.slc.xdim)
        roi = ROI(slc=slicer.slc, poly=poly, slicer=slicer)
        assert_array_equal(expected.T, roi.masked(arr))

    def test_save_and_load(self):
        arr = np.zeros((3,3))
        slicer = Slicer(arr)
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])

        roi = ROI(slc=slicer.slc, poly=poly, slicer=slicer, name='name')
        _,filename = tempfile.mkstemp()

        ROIPersistence.save([roi], filename)
        lrois = ROIPersistence.load(filename, slicer)

        self.assertEquals(len(lrois), 1)
        lroi = lrois[0]

        self.assertEquals(roi.name, lroi.name)
        self.assertEquals(roi.slc, lroi.slc)
        assert_array_equal(roi.poly, lroi.poly)


class TestROIManager(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.sqrPoly = np.array([(0,0),(0,1),(1,1),(1,0)])

    def test_new(self):
        slicer = Slicer(np.zeros((3,3)))
        roimngr = ROIManager(slicer=slicer)

        with self.assertTraitChanges(roimngr, 'rois[]') as result:
            roimngr.new(self.sqrPoly)

        expected = [(roimngr, 'rois_items', [], [roimngr.rois[0]])]
        self.assertSequenceEqual(result.events, expected)

    def test_delete_selected(self):
        slicer = Slicer(np.zeros((3,3)))
        roimngr = ROIManager(slicer=slicer)
        roimngr.new(self.sqrPoly)
        prevROIs = roimngr.rois
        with self.assertTraitChanges(roimngr, 'rois[]', count=1) as result:
            roimngr.selected = roimngr.rois
            roimngr.delete = True

        expected = [(roimngr, 'rois', prevROIs, [])]
        self.assertSequenceEqual(result.events, expected)


class Test_ROI_Stats(unittest.TestCase, UnittestTools):
    def setUp(self):
        arr = np.arange(2*3*4).reshape(2,3,4)
        self.slicer = Slicer(arr)
        poly = np.array([(0,0),(0,2),(2,2),(2,0)])
        self.roi = ROI(slc=self.slicer.slc, poly=poly, slicer=self.slicer)

    def test_mean(self):
        self.assertAlmostEqual(self.roi.mean, 8.0)

    def test_std(self):
        self.assertAlmostEqual(self.roi.std, 6.324555320336759)

    def test_size(self):
        self.assertEqual(self.roi.size, 4)

    def _mean_updated(self):
        newPoly = np.array([(0,0), (0,3), (3,3), (3,0)])
        with self.assertTraitChanges(self.roi, 'mean') as result:
            self.roi.poly = newPoly

        expected = (self.roi, 'mean', 8.0, 0.25)
        self.assertSequenceEqual(result.events, expected)
            
