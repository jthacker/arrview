import numpy as np
from matplotlib.cm import gray, jet, spectral
from matplotlib.colors import Normalize,LogNorm
from collections import namedtuple

from PySide.QtGui import QPixmap, QImage
from traits.api import (HasPrivateTraits, Any, Instance, Property, Range, Float,
        on_trait_change, cached_property)
from traitsui.api import View, Item, EnumEditor


def ndarray_to_pixdata(array, cmap, norm):
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


Norm = namedtuple('Norm', ('name', 'init'))
_cmaps = [jet,gray,spectral]
_norms = [Norm('MinMax', Normalize), Norm('Log', LogNorm)]

class ColorMapper(HasPrivateTraits):
    cmap = Any(_cmaps[0])
    _norm = Any(_norms[0])
    norm = Property(depends_on='[_norm]')

    view = View(
            Item('cmap', label='cmap',
                editor=EnumEditor(values={c:c.name for c in _cmaps})),
            Item('_norm', label='norm',
                editor=EnumEditor(values={n:n.name for n in _norms})))

    @cached_property
    def _get_norm(self):
        return self._norm.init()
        

