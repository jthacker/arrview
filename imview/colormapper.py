import numpy as np
from matplotlib.cm import gray, jet, spectral
from collections import namedtuple

from PySide.QtGui import QPixmap, QImage

from traits.api import (HasTraits, HasPrivateTraits, Any, Instance, 
        Property, Range, Float, on_trait_change, cached_property,
        Button, Bool)
from traitsui.api import View, HGroup, Item, EnumEditor, RangeEditor, Group

from .slicer import Slicer

def ndarray_to_pixdata(array, cmap, norm):
    '''Convert an array to a QPixmap using the given color map
    and scaling. Returns an array and the pixmap, the array must
    be held onto as long as the pixmap is around.
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


class Norm(HasTraits):
    name = 'Linear'
    vmin = Float
    vmax = Float
    low = Float
    high = Float
    
    view = View(
            Item('vmin', 
                label='vmin',
                editor=RangeEditor(
                    low_name='low',
                    high_name='high',
                    format='%0.2f')),
            Item('vmax', 
                label='vmax',
                editor=RangeEditor(
                    low_name='low',
                    high_name='high',
                    format='%0.2f')))

    def __init__(self):
        super(Norm, self).__init__()
        self._scaled = False

    def set_scale(self, ndarray):
        vmin,vmax = ndarray.min(),ndarray.max()
        self.vmin = vmin
        self.vmax = vmax
        self.low = vmin
        self.high = vmax
        self._scaled = True

    def normalize(self, ndarray):
        if not self._scaled:
            self.set_scale(ndarray)
        
        vmin, vmax = self.vmin, self.vmax
        if vmin == vmax:
            return np.zeros_like(ndarray)
        else:
            return np.clip((ndarray - vmin) / (vmax - vmin), 0, 1)

    def __repr__(self):
        return 'Norm(name=%s, vmin=%f, vmax=%f)' % (self.name, self.vmin, self.vmax)


_cmaps = [jet,gray,spectral]

class ColorMapper(HasPrivateTraits):
    cmap = Any(_cmaps[0])
    norm = Instance(Norm, Norm)
    slicer = Instance(Slicer)
    rescale = Button
    autoscale = Bool(False)

    view = View(
            HGroup(
                Item('cmap', show_label=False,
                    editor=EnumEditor(values={c:c.name for c in _cmaps})),
                Item('rescale', show_label=False),
                Item('autoscale')))

    def array_to_pixmap(self, array):
        if self.autoscale:
            self.norm.set_scale(array)
        return ndarray_to_arraypixmap(array, self.cmap, self.norm.normalize)

    def _rescale_fired(self):
        self.norm.set_scale(self.slicer._arr)
