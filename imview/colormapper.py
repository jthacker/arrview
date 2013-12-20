import numpy as np

from matplotlib.cm import jet,gray
from matplotlib.colors import Normalize

from PySide.QtGui import QPixmap, QImage

def ndarray_to_pixdata(array, cmap=jet, norm=lambda a: Normalize()(a)):
    '''Convert an array to a QPixmap using the given color map
    and scaling. Returns an array and the pixmap, the array must
    be held onto as long as the pixmap is around.

    TODO:
    * Add support for scaling
    * Add support for colormaps
    '''
    assert array.ndim == 2, 'Only 2D arrays are allowed'
    h,w = array.shape
    array = (255*cmap(norm(array))).astype('uint32')
    array = (255 << 24 | array[:,:,0] << 16 | array[:,:,1] << 8 | array[:,:,2]).flatten()
    return array


def pixdata_to_ndarray(pixmap,h,w):
    assert pixmap.ndim == 1
    array = np.zeros((h,w,3))
    shape = lambda d: ((0xff << d & pixmap) >> d).reshape(h,w)
    array[:,:,0] = shape(16)
    array[:,:,1] = shape(8)
    array[:,:,2] = shape(0)
    return array


class ArrayPixmap(QPixmap):
    '''ArrayPixmap is a wrapper around QPixmap that holds onto a copy of
    the array it is created from'''
    def __init__(self, array, qpixmap):
        super(ArrayPixmap, self).__init__(qpixmap)
        self._array = array


def ndarray_to_arraypixmap(array, cmap=gray, norm=lambda a: Normalize()(a)):
    data = ndarray_to_pixdata(array, cmap, norm)
    h,w = array.shape
    img = QImage(data, w, h, QImage.Format_RGB32)
    pixmap = QPixmap.fromImage(img)
    return ArrayPixmap(data, pixmap)
