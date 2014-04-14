from __future__ import division

import numpy as np
from PySide.QtCore import QObject, Signal
from PySide.QtGui import QPixmap, QImage
from matplotlib.cm import gray, jet, spectral

from .util import rep, Scale


class ArrayPixmap(QPixmap):
    '''ArrayPixmap is a wrapper around QPixmap that holds onto a copy of
    the array it is created from'''
    def __init__(self, array, qpixmap):
        super(ArrayPixmap, self).__init__(qpixmap)
        self._array = array


def ndarray_to_pixdata(array, cmap, norm):
    '''Convert a 2D ndarray to a 1d ndarray of pixdata.
    Args:
    array -- 2D ndarray to convert
    cmap  -- Color mapping function
    norm  -- Normalization function

    Returns:
    A 1D array in RGB32 format representing the 2D input array
    that was colormapped using the cmap function and normalized
    with norm.
    '''
    assert array.ndim == 2, 'Only 2D arrays are supported'
    h,w = array.shape
    array = (255*cmap(norm(array).astype('float'))).astype('uint32')
    array = (255 << 24 | array[:,:,0] << 16 | array[:,:,1] << 8 | array[:,:,2])
    return array.flatten()


def ndarray_to_pixmap(array, cmap, norm):
    '''Convert a 2D ndarray to q Qt Pixmap
    @see ndarray_to_pixdata'''
    pixdata = ndarray_to_pixdata(array, cmap, norm)
    h,w = array.shape
    img = QImage(pixdata, w, h, QImage.Format_RGB32)
    pixmap = QPixmap.fromImage(img)
    return ArrayPixmap(pixdata, pixmap)


def autoscale(ndarray, lower=0.05, upper=0.95):
    '''Find the soft and hard scale limits using the CDF of the ndarray
    Args:
    ndarray -- array to find scaling for
    lower   -- (default: 0.05) lower bound of CDF
    upper   -- (default: 0.95) upper bound of CDF

    Returns:
    A tuple of soft and hard limits.
    Soft limits are set based on the CDF of the array. The low soft limit
    is set by computing the CDF and then finding the value closest to the
    lower parameter. The same procedure is down for the soft high limit but
    using the upper parameter instead.
    Hard limits are set to the min and max of the array.
    '''
    arr = ndarray[np.isfinite(ndarray)]
    pdf,bins = np.histogram(arr, bins=50)
    cdf = pdf.cumsum() / float(arr.size)
    soft = Scale(low=bins[np.argmax(cdf > lower)], high=bins[np.argmin(cdf < upper)])
    hard = Scale(low=float(arr.min()), high=float(arr.max()))
    return soft, hard


class LinearNorm(object):
    def __init__(self, soft, hard):
        assert soft.low >= hard.low
        assert soft.high <= hard.high
        self.soft = soft
        self.hard = hard

    def __call__(self, ndarray):
        vmin, vmax = self.soft
        if vmin == vmax:
            return np.zeros_like(ndarray)
        else:
            return np.clip((ndarray - vmin) / (vmax - vmin), 0, 1)

    def __repr__(self):
        return rep(self, ['soft','hard'])


class ColorMapper(QObject):
    updated = Signal()

    def __init__(self, cmap, norm):
        super(ColorMapper, self).__init__()
        self._cmap = cmap
        self._norm = norm
        self._default_scale = self._norm.soft

    @property
    def scale(self):
        return self._norm.soft

    @scale.setter
    def scale(self, scale):
        self._norm.soft = scale
        self.updated.emit()

    @property
    def limits(self):
        return self._norm.hard

    def reset(self):
        self.scale = self._default_scale

    def ndarray_to_pixmap(self, ndarray):
        return ndarray_to_pixmap(ndarray, self._cmap, self._norm)

