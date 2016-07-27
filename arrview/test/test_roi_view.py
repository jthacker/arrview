import numpy as np

from traits.testing.unittest_tools import unittest
from traits.testing.api import UnittestTools

from arrview.roi import ROI, ROIView


class Test_ROIView(unittest.TestCase, UnittestTools):
    def setUp(self):
        arr = np.arange(2*3*4).reshape(2,3,4)
        mask = np.zeros_like(arr, dtype=bool)
        mask[:2, :2, 0] = True
        roi = ROI(mask=mask)
        self.mask = mask
        self.view = ROIView(roi=roi, arr=arr)

    def test_mean(self):
        self.assertAlmostEqual(self.view.mean, 8.0)

    def test_std(self):
        self.assertAlmostEqual(self.view.std, 6.324555320336759)

    def test_size(self):
        self.assertEqual(self.view.size, 4)

    def _mean_updated(self):
        new_mask = np.zeros(self.mask.shape, dtype=bool)
        new_mask[:3, :3, 0] = True
        with self.assertTraitChanges(self.view, 'mean') as result:
            self.roi.mask = new_mask
        expected = (self.view, 'mean', 8.0, 0.25)
        self.assertSequenceEqual(result.events, expected)
