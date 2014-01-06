import skimage.draw
import numpy as np
from collections import namedtuple

from traits.api import (HasTraits, List, Instance, Property,
    Array, String, Int, Event, DelegatesTo,
    on_trait_change, cached_property)
from traitsui.api import View, Item, ListEditor, TableEditor
from traitsui.table_column import ObjectColumn

from .util import rep
from .slicer import Slicer


SlicePoly = namedtuple('SlicePoly', ('slc', 'poly'))


class ROI(HasTraits):
    name = String
    slicepoly = Instance(SlicePoly)

    view = View(Item('name', show_label=False))

    def set_poly(self, slc, poly):
        '''Add a polygon to the ROI
        Args:
        slc    -- SliceTuple describing the location of the polygon
        poly   -- (ndarray) 2D points array that describes the polygon
                  in array coordinates: [(r1,c1), (r2,c2), ..., (rN,cN)]
        '''
        assert poly.ndim == 2
        assert len(slc) >= 2
        self.slicepoly = SlicePoly(slc, poly)

    def _dims_to_slice(self, slc, rr, cc):
        mslc = list(slc)
        mslc[slc.ydim] = rr
        mslc[slc.xdim] = cc
        return mslc

    def mask(self, arr):
        '''Convert the polygons to a binary mask according the specified array shape
        Args:
        shape -- a tuple with the size of each dimension in the mask

        Returns:
        binary mask with the regions in polys set to true and everywhere else
        set to false
        '''
        shape = arr.shape
        mask = np.ones(shape)
        slc,poly = self.slicepoly
        rr,cc = skimage.draw.polygon(poly[:,0], poly[:,1])
        polyslice = self._dims_to_slice(slc, rr, cc)
        mask[polyslice] = False
        return np.ma.array(arr, mask=mask)

    def __repr__(self):
        return rep(self, ['name','slicepoly'])


class ROIInfo(HasTraits):
    roi = Instance(ROI)

    name = DelegatesTo('roi')
    masked = Property()
    mean = Property()
    std = Property()
    count = Property()
    
    def __init__(self, arr, roi):
        super(ROIInfo, self).__init__(roi=roi)
        self._masked = roi.mask(arr)

    @cached_property
    def _get_masked(self):
        return self._masked

    @cached_property
    def _get_mean(self):
        return self.masked.mean()

    @cached_property
    def _get_std(self):
        # HACKish: self.masked.std() is stragely slow.
        # This technique appears to be on par with unmasked arrays
        return self.masked.data[np.logical_not(self.masked.mask)].std()

    @cached_property
    def _get_count(self):
        return self.masked.count()

    def __repr__(self):
        return rep(self, ['roi','count','mean','std'])


roi_editor = TableEditor(
    sortable = False,
    configurable = False,
    columns = [ 
        ObjectColumn(name='name'),
        ObjectColumn(name='mean', format='%0.3g', editable=False),
        ObjectColumn(name='std', format='%0.3g', editable=False),
        ObjectColumn(name='count', format='%d', editable=False)])


class ROIManager(HasTraits):
    rois = List(ROI, [])
    infos = List(ROIInfo, [])
    nextID = Int(1)

    view = View(
        Item('infos', 
            editor=roi_editor, 
            show_label=False))
    
    def new(self, slicer, poly):
        roi = ROI(name='roi_%02d' % self.nextID)
        roi.set_poly(slicer.slc, poly)
        self.nextID += 1
        self.rois.append(roi)
        self.infos.append(ROIInfo(arr=slicer.arr, roi=roi))
