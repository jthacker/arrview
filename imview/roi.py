import skimage.draw
import numpy as np
from collections import namedtuple
import os
import h5py
from itertools import izip

from traits.api import (HasTraits, HasPrivateTraits, List, Instance, Property,
    Any, String, Int, Float, Event, Button, DelegatesTo, WeakRef, Array, File,
    on_trait_change, cached_property)
from traitsui.api import View, Item, HGroup, TableEditor
from traitsui.menu import OKCancelButtons
from traitsui.table_column import ObjectColumn

from .util import rep
from .slicer import Slicer, SliceTuple
from .ui.dimeditor import SlicerDims
from .file_dialog import save_file, open_file


def _dims_to_slice(shape, slc, rr, cc):
    rdim = slc.ydim
    cdim = slc.xdim
    mslc = list(slc)
    mslc[rdim] = rr
    mslc[cdim] = cc
    return mslc

def create_mask(shape, slc, poly):
    '''Convert the polygons to a binary mask according the specified array shape
    Args:
    shape -- a tuple with the size of each dimension in the mask
    poly  -- A numpy array of (x,y) point pairs describing a polygon
    slc   -- SliceTuple describing where to apply the polygon to

    Returns:
    binary mask with the region in poly set to true and everywhere else
    set to false
    '''
    mask = np.ones(shape, dtype=bool)

    if len(poly) > 0: 
        rr,cc = skimage.draw.polygon(poly[:,0], poly[:,1], shape=shape)
        polyslice = _dims_to_slice(shape, slc, rr, cc)
        mask[polyslice] = False
    return mask


class ROI(HasTraits):
    name = String
    slicer = Instance(Slicer)
    slc = Instance(SliceTuple)
    poly = Array

    mean = Property
    _mean = Float
    std = Property
    _std = Float
    count = Property
    _count = Int

    def __init__(self, **traits):
        super(ROI, self).__init__(**traits)
        self.on_trait_change(self.update_stats, ['slc', 'poly'])
        self.update_stats()

    def masked(self, arr):
        return np.ma.array(data=arr, mask=create_mask(arr.shape, self.slc, self.poly))

    def update_stats(self):
        view = self.slicer.arr[self.slc.arrayslice] # 2D Array
        slc2D = SliceTuple(self.slc[v] for v in sorted(self.slc.viewdims))
        masked_data = view[create_mask(view.shape, slc2D, self.poly) != True]

        self._mean = masked_data.mean()
        self._std = masked_data.std()
        self._count = masked_data.size

    def _get_mean(self):
        return self._mean

    def _get_std(self):
        return self._std

    def _get_count(self):
        return self._count

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
            slc = roi.slc
            if dim in slc.freedims:
                for i in set(range(dimMax)) - set([slc[dim]]):
                    slc = list(roi.slc)
                    slc[dim] = i
                    slc = SliceTuple(slc)
                    rois.append(self._new_roi(slc, roi.poly.copy()))
        self.rois.extend(rois)


class ROIPersistence(object):
    @staticmethod
    def filter_viewdims(slc):
        viewdims = slc.viewdims
        return [0 if d in viewdims else v for d,v in enumerate(slc)] 

    @staticmethod
    def save(rois, filename):
        with h5py.File(filename, 'w') as f:
            slices = [roi.slc for roi in rois]
            f['/rois/names'] = [roi.name for roi in rois]
            f['/rois/polys'] = [roi.poly for roi in rois]
            f['/rois/viewdims'] = [slc.viewdims for slc in slices]
            f['/rois/slices'] = [ROIPersistence.filter_viewdims(slc) for slc in slices]

    @staticmethod
    def load(filename, slicer):
        with h5py.File(filename, 'r') as f:
            names = [str(name) for name in f['/rois/names'].value]
            polys = f['/rois/polys'].value
            viewdims = f['/rois/viewdims'].value
            slices = f['/rois/slices'].value
            slcs = [SliceTuple.from_arrayslice(slc,vdims) for slc,vdims in izip(slices,viewdims)]
            return [ROI(name=name, slc=slc,
                poly=poly, slicer=slicer) for (name,slc,poly) in izip(names,slcs,polys)]
