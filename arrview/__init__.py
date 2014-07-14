import os
os.environ['ETS_TOOLKIT'] = 'qt4'

from .main import ArrayViewer
from .slicer import Slicer

def view(arr, roi_filename=None):
    viewer = ArrayViewer(Slicer(arr), roi_filename)
    viewer.configure_traits()
    return viewer
