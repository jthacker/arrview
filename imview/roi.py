import skimage.draw
import numpy as np
from collections import namedtuple

from traits.api import (HasTraits, List, Instance, 
    String, Event, on_trait_change)


SlicePoly = namedtuple('SlicePoly', ('dims', 'poly'))


class ROI(HasTraits):
    name = String
    polys = List(SlicePoly)

    def __init__(self, name):
        self.name = name

    def add_poly(self, dims, poly):
        '''Add a polygon to the ROI
        Args:
        poly -- (ndarray) 2D points array that describes the polygon
                in array coordinates: [(r1,c1), (r2,c2), ..., (rN,cN)]
        dims -- a tuple selecting which dims this roi is on
        '''
        assert poly.ndim == 2
        assert len(dims) >= 2
        self.polys.append(SlicePoly(dims,poly))

    def _dims_to_slice(self, dims, rr, cc):
        dims = list(dims)
        rrIdx = dims.index(slice(None))
        ccIdx = dims.index(slice(None), rrIdx+1)
        assert 0 <= rrIdx < len(dims)
        assert rrIdx < ccIdx < len(dims)
        dims[rrIdx] = rr
        dims[ccIdx] = cc
        return dims

    def to_mask(self, shape):
        '''Convert the polygons to a binary mask according the specified array shape
        Args:
        shape -- a tuple with the size of each dimension in the mask

        Returns:
        binary mask with the regions in polys set to true and everywhere else
        set to false
        '''
        mask = np.zeros(shape)
        for dims,poly in self.polys:
            rr,cc = skimage.draw.polygon(poly[:,0], poly[:,1])
            slc = self._dims_to_slice(dims, rr, cc)
            mask[slc] = 1
        return mask


class ROIManager(HasTraits):
    rois = List(ROI)

    def add(self, roi):
        self.rois.append(roi)

    def remove(self, roi):
        self.rois.remove(roi)