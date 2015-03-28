import os
os.environ['ETS_TOOLKIT'] = 'qt4'

from .main import ArrayViewer
from .slicer import Slicer

def view(arr, roi_filename=None, rois_updated=None):
    viewer = ArrayViewer(Slicer(arr), roi_filename, rois_updated)
    viewer.configure_traits()
    return viewer
