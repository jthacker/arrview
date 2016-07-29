import numpy as np

from traits.testing.unittest_tools import unittest
from traits.testing.api import UnittestTools

from arrview.roi import ROIManager
from arrview.slicer import Slicer


class TestROIManager(unittest.TestCase, UnittestTools):
    def test_new(self):
        slicer = Slicer(np.zeros((3, 3)))
        roimngr = ROIManager(slicer=slicer)

        with self.assertTraitChanges(roimngr, 'rois[]') as result:
            roimngr.new_roi()

        expected = [(roimngr, 'rois_items', [], [roimngr.rois[0]])]
        self.assertSequenceEqual(result.events, expected)

    def test_delete_selected(self):
        slicer = Slicer(np.zeros((3,3)))
        roimngr = ROIManager(slicer=slicer)
        roimngr.new_roi()
        prevROIs = roimngr.rois
        with self.assertTraitChanges(roimngr, 'rois[]', count=1) as result:
            roimngr.selected = roimngr.rois
            roimngr.delete = True

        expected = [(roimngr, 'rois', prevROIs, [])]
        self.assertSequenceEqual(result.events, expected)
