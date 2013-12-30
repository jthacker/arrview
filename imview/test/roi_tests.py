import numpy as np
from numpy.testing import assert_array_equal
from traits.testing.unittest_tools import unittest
from traits.testing.api import UnittestTools

from ..roi import ROI,ROIManager

class TestROI(unittest.TestCase, UnittestTools):
    def setUp(self):
        self.sqrPoly = np.array([(0,0),(0,1),(1,1),(1,0)])

    def test_to_mask(self):
        roi = ROI(name='test')
        roi.add_poly((slice(None), slice(None), 0), self.sqrPoly)
        roi.add_poly((slice(None), slice(None), 1), self.sqrPoly)

        shape = (3,3,3)
        expectedMask = np.zeros(shape)
        expectedMask[:1,:1,:2] = 1

        assert_array_equal(expectedMask, roi.to_mask(shape))

    def test_coordinate_order(self):
        '''The specified coordinates should be (row1,col1), (row2,col2), ...
        '''
        roi = ROI(name='test')
        poly = np.array([(0,0),(0,3),(1,3),(1,0)])
        roi.add_poly((slice(None), slice(None)), poly)
        shape = (3,3)
        expectedMask = np.zeros(shape)
        expectedMask[0,:] = 1

        assert_array_equal(expectedMask, roi.to_mask(shape))

    def test_poly_changed(self):
        roi = ROI(name='test')
        dims = (slice(None), slice(None), 0)
        with self.assertTraitChanges(roi, 'polys[]') as result:
            roi.add_poly(dims, self.sqrPoly)
        
        expected = [(roi, 'polys_items', [], [(dims, self.sqrPoly)])]
        self.assertSequenceEqual(result.events, expected)


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
