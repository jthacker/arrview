import os
import tempfile

import numpy as np
from numpy.testing import assert_array_equal

from arrview.roi import ROI
from arrview.roi_persistence import load_rois, store_rois


def test_save_and_load():
    roi = ROI(name='name', mask=np.ones((15, 15), dtype=bool))
    _, filename = tempfile.mkstemp()
    store_rois([roi], filename)
    lrois = load_rois(filename)
    assert len(lrois) == 1
    lroi = lrois[0]
    assert roi.name == lroi.name
    assert_array_equal(roi.mask, lroi.mask)


def test_load_old_format():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, 'data/old_roi_format.h5')
    rois = load_rois(filename, shape=(128, 128, 5, 5))
    #TODO: validate
