import skimage.draw
import numpy as np
from collections import namedtuple

from traits.api import (HasTraits, HasPrivateTraits, List, Instance, Property,
    Any, String, Int, Event, Button, DelegatesTo, WeakRef, Array,
    on_trait_change, cached_property)
from traitsui.api import View, Item, HGroup, TableEditor
from traitsui.table_column import ObjectColumn

from .util import rep
from .slicer import Slicer, SliceTuple
from .ui.dimeditor import SlicerDims


def _dims_to_slice(shape, slc, rr, cc):
    rdim = slc.ydim
    cdim = slc.xdim
    mslc = list(slc)
    ridx = np.logical_and(rr >=0, rr < shape[rdim])
    cidx = np.logical_and(cc >=0, cc < shape[cdim])
    filtered_indicies = np.logical_and(ridx, cidx)
    mslc[rdim] = rr[filtered_indicies]
    mslc[cdim] = cc[filtered_indicies]
    return mslc

def create_mask(arr, slc, poly):
    '''Convert the polygons to a binary mask according the specified array shape
    Args:
    shape -- a tuple with the size of each dimension in the mask

    Returns:
    binary mask with the regions in polys set to true and everywhere else
    set to false
    '''
    shape = arr.shape
    mask = np.ones(shape)
    rr,cc = skimage.draw.polygon(poly[:,0], poly[:,1])
    polyslice = _dims_to_slice(shape, slc, rr, cc)
    mask[polyslice] = False
    return mask


class ROI(HasTraits):
    name = String
    slicer = Instance(Slicer)
    
    slc = Instance(SliceTuple)
    poly = Array

    masked = Property(depends_on='[slc,poly]')
    mean = Property(depends_on='[slc,poly]')
    std = Property(depends_on='[slc,poly]')
    count = Property(depends_on='[slc,poly]')

    def mask(self, arr):
        return np.ma.array(data=arr, mask=create_mask(arr, self.slc, self.poly))

    def _get_masked(self):
        view = self.slicer.arr[self.slc.arrayslice] # 2D Array
        slc2D = SliceTuple(self.slc[v] for v in sorted(self.slc.viewdims))
        return view[create_mask(view, slc2D, self.poly) != True]

    @cached_property
    def _get_mean(self):
        return self.masked.mean()

    @cached_property
    def _get_std(self):
        return self.masked.std()

    @cached_property
    def _get_count(self):
        return self.masked.size

    def __repr__(self):
        return rep(self, ['name','slc','poly','count','mean','std'])


roi_editor = TableEditor(
    sortable = False,
    configurable = False,
    selection_mode = 'rows',
    selected = 'selected',
    columns = [ 
        ObjectColumn(name='name'),
        ObjectColumn(name='slc', editable=False),
        ObjectColumn(name='mean', format='%0.3g', editable=False),
        ObjectColumn(name='std', format='%0.3g', editable=False),
        ObjectColumn(name='count', format='%d', editable=False)])


class ROIManager(HasTraits):
    slicer = Instance(Slicer)
    rois = List(ROI, [])
    nextID = Int(0)
    selected = List(ROI, [])
    slicerDims = Instance(SlicerDims)
    freedim = DelegatesTo('slicerDims')

    replicate = Button
    copy = Button
    delete = Button

    view = View(
        HGroup(
            Item('delete',
                enabled_when='len(selected) > 0',
                show_label=False),
            Item('copy',
                enabled_when='len(selected) > 0',
                show_label=False),
            Item('replicate',
                enabled_when='len(selected) > 0',
                show_label=False)),
        Item('rois', 
            editor=roi_editor, 
            show_label=False))
    
    def new(self, poly):
        self.rois.append(self._new_roi(self.slicer.slc, poly))

    def _new_roi(self, slc, poly):
        roi = ROI(
            name='roi_%02d' % self.nextID,
            slicer=self.slicer,
            slc=slc,
            poly=poly)
        self.nextID += 1
        return roi

    def update_roi(self, roi, slc, poly):
        idx = self.rois.index(roi)
        newROI = ROI(
            name=roi.name,
            slicer=self.slicer,
            slc=slc,
            poly=poly)
        self.rois[idx] = newROI

    def _delete_fired(self):
        self.rois = [i for i in self.rois if i not in self.selected]
        self.selected = []

    def _copy_fired(self):
        self.rois.extend([self._new_roi(roi.slc, roi.poly.copy()) for roi in self.selected])

    def _replicate_fired(self):
        '''Copy the currently selected ROIs to each place in the 
        currently selected free dimension'''
        rois = []
        dim,dimVal = self.freedim.dim, self.freedim.val
        dimMax = self.slicer.shape[dim]
        for roi in self.selected:
            if dim in roi.slc.freedims:
                for i in set(range(dimMax)) - set([dimVal]):
                    slc = list(roi.slc)
                    slc[dim] = i
                    slc = SliceTuple(slc)
                    rois.append(self._new_roi(slc, roi.poly.copy()))
        self.rois.extend(rois)
