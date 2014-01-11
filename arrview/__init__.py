import os
os.environ['ETS_TOOLKIT'] = 'qt4'

from .main import ArrayViewer
from .slicer import Slicer

def view(arr):
    slicer = Slicer(arr)
    viewer = ArrayViewer(slicer)
    viewer.configure_trait()
    return viewer
