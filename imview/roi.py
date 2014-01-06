import skimage.draw
import numpy as np
from collections import namedtuple

from traits.api import (HasTraits, List, Instance, 
    String, Int, Event, on_trait_change)
from traitsui.api import View, Item, ListEditor

from .util import rep


SlicePoly = namedtuple('SlicePoly', ('slc', 'poly'))


class ROI(HasTraits):
    name = String
    slicepoly = Instance(SlicePoly)

    view = View(Item('name', show_label=False))

    def set_poly(self, slicer, poly):
        '''Add a polygon to the ROI
        Args:
        slicer -- slicer object from which the poly was created
        poly   -- (ndarray) 2D points array that describes the polygon
                  in array coordinates: [(r1,c1), (r2,c2), ..., (rN,cN)]
        '''
        assert poly.ndim == 2
        assert len(slicer.slc) >= 2
        self.slicepoly = SlicePoly(slicer.slc, poly)

    def _dims_to_slice(self, slc, rr, cc):
        mslc = list(slc)
        mslc[slc.ydim] = rr
        mslc[slc.xdim] = cc
        return mslc

    def to_mask(self, shape):
        '''Convert the polygons to a binary mask according the specified array shape
        Args:
        shape -- a tuple with the size of each dimension in the mask

        Returns:
        binary mask with the regions in polys set to true and everywhere else
        set to false
        '''
        mask = np.zeros(shape)
        slc,poly = self.slicepoly
        rr,cc = skimage.draw.polygon(poly[:,0], poly[:,1])
        polyslice = self._dims_to_slice(slc, rr, cc)
        mask[polyslice] = 1
        return mask

    def __repr__(self):
        return rep(self, ['name','slicepoly'])


class ROIManager(HasTraits):
    rois = List(ROI, [])
    nextID = Int(1)

    view = View(Item('rois', 
        editor=ListEditor(style='custom'), 
        show_label=False))
    
    def add(self, roi):
        self.nextID += 1
        self.rois.append(roi)

    def new_roi(self, slicer, poly):
        roi = ROI(name='roi_%02d' % self.nextID)
        roi.set_poly(slicer, poly)
        self.add(roi)
