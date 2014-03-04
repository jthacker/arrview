import os
os.environ['ETS_TOOLKIT'] = 'qt4'

from .main import ArrayViewer
from .slicer import Slicer


def create_viewer(arr, default_directory=None):
    return ArrayViewer(Slicer(arr), default_directory)

def view(arr):
    viewer = create_viewer(arr)
    viewer.configure_traits()
    return viewer
