import skimage.draw
import numpy as np
from collections import namedtuple

from traits.api import (HasTraits, List, Instance, 
    String, Event, on_trait_change)
from traitsui.api import View, Item, ListEditor

from .util import rep


ROISlice = namedtuple('ROISlice', ('xdim', 'ydim', 'slc', 'poly'))


class ROI(HasTraits):
    name = String
    poly = Instance(ROISlice)

    def set_poly(self, slicer, poly):
        '''Add a polygon to the ROI
        Args:
        slicer -- slicer object from which the poly was created
        poly   -- (ndarray) 2D points array that describes the polygon
                  in array coordinates: [(r1,c1), (r2,c2), ..., (rN,cN)]
        '''
        assert poly.ndim == 2
        assert len(slicer.slc) >= 2
        self.poly = ROISlice(slicer.xdim, slicer.ydim, slicer.slc, poly)

    def _dims_to_slice(self, xdim, ydim, slc, rr, cc):
        slc = list(slc)
        rrIdx = ydim
        ccIdx = xdim
        slc[rrIdx] = rr
        slc[ccIdx] = cc
        return slc

    def to_mask(self, shape):
        '''Convert the polygons to a binary mask according the specified array shape
        Args:
        shape -- a tuple with the size of each dimension in the mask

        Returns:
        binary mask with the regions in polys set to true and everywhere else
        set to false
        '''
        mask = np.zeros(shape)
        xdim,ydim,slc,poly = self.poly
        rr,cc = skimage.draw.polygon(poly[:,0], poly[:,1])
        polyslice = self._dims_to_slice(xdim, ydim, slc, rr, cc)
        mask[polyslice] = 1
        return mask

    def __repr__(self):
        return rep(self, ['name','poly'])


class ROIManager(HasTraits):
    rois = List(ROI, [])

    view = View(Item('rois', editor=ListEditor(), show_label=False))

    def add(self, roi):
        self.rois.append(roi)
