import skimage.draw
import numpy as np
from collections import namedtuple
import os
import h5py
from itertools import izip

from traits.api import (HasTraits, HasPrivateTraits, List, Instance, Property,
    Any, Str, Int, Float, Event, Button, DelegatesTo, WeakRef, Array, File,
    on_trait_change, cached_property)
from traitsui.api import View, Item, HGroup, TabularEditor
from traitsui.tabular_adapter import TabularAdapter
from traitsui.menu import OKCancelButtons
from traitsui.table_column import ObjectColumn

from .util import rep
from .slicer import Slicer, SliceTuple
from .ui.dimeditor import SlicerDims
from .file_dialog import save_file, open_file


def create_mask(shape, slc, poly):
    '''Convert the polygons to a binary mask according the specified array shape
    Args:
    shape -- a tuple with the size of each dimension in the mask
    slc   -- SliceTuple describing where to apply the polygon to
    poly  -- A numpy array of (x,y) point pairs describing a polygon

    Returns:
    binary mask with the region in poly set to true and everywhere else
    set to false
    '''
    mask = np.ones(shape, dtype=bool)
    if len(poly) > 0:
        viewShape = shape[slc.ydim],shape[slc.xdim]
        y,x = skimage.draw.polygon(y=poly[:,1], x=poly[:,0], shape=viewShape)
        mask[slc.slice_from_screen_coords(x, y, mask)] = False
    return mask


class ROI(HasTraits):
    name = Str
    slicer = Instance(Slicer)
    slc = Instance(SliceTuple)
    poly = Array

    mean = Property
    _mean = Float
    std = Property
    _std = Float
    size = Property
    _size = Int

    def __init__(self, **traits):
        super(ROI, self).__init__(**traits)
        self.on_trait_change(self.update_stats, ['slc', 'poly'])
        self.update_stats()

    def mask_arr(self, arr):
        return np.ma.array(data=arr, mask=create_mask(arr.shape, self.slc, self.poly))

    def update_stats(self):
        shape = self.slicer.shape
        masked_data = self.slicer.arr[create_mask(shape, self.slc, self.poly) != True]
        self._mean = masked_data.mean()
        self._std = masked_data.std()
        self._size = masked_data.size

    def update_stats_fast(self):
        view = self.slc.viewarray(self.slicer.arr)
        # create a 2D SliceTuple
        slc2D = SliceTuple(self.slc[v] for v in sorted(self.slc.viewdims))
        masked_data = view[create_mask(view.shape, slc2D, self.poly) != True]

        self._mean = masked_data.mean()
        self._std = masked_data.std()
        self._size = masked_data.size

    def _get_mean(self):
        return self._mean

    def _get_std(self):
        return self._std

    def _get_size(self):
        return self._size

    def __repr__(self):
        return rep(self, ['name','slc','poly','size','mean','std'])


class ROIAdapter(TabularAdapter):
    columns = [ ('Name', 'name'),
                ('Slice', 'slc'),
                ('Mean', 'mean'),
                ('Std', 'std'),
                ('Size', 'size')]

    slc_text = Property

    def _get_slc_text(self):
        return '[%s]' % ','.join(str(x) for x in self.item.slc)


roi_editor = TabularEditor(
        adapter = ROIAdapter(),
        operations = ['edit'],
        multi_select = True,
        auto_update = True,
        selected = 'selected')

    
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
    dump = Button
    
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
                show_label=False),
            Item('dump',
                show_label=False)),
        Item('rois', 
            editor=roi_editor,
            style='readonly',
            show_label=False))
    
    def new(self, poly):
        self.rois.append(self._new_roi(self.slicer.slc, poly))

    def by_name(self, name):
        return [roi for roi in self.rois if roi.name==name]

    def _dump_fired(self):
        print(self.rois)
        import ipdb; ipdb.set_trace()

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
        indicies = set(range(dimMax))
        for roi in self.selected:
            slc = roi.slc
            if dim in slc.freedims:
                for i in indicies - set([slc[dim]]):
                    slc = list(roi.slc)
                    slc[dim] = i
                    slc = SliceTuple(slc)
                    rois.append(
                        ROI(name=roi.name, slicer=self.slicer,
                            slc=slc, poly=roi.poly.copy()))
        self.rois.extend(rois)


class ROIPersistence(object):
    @staticmethod
    def filter_viewdims(slc):
        viewdims = slc.viewdims
        return [0 if d in viewdims else v for d,v in enumerate(slc)] 

    @staticmethod
    def save(rois, filename):
        with h5py.File(filename, 'w') as f:
            root = f.create_group('rois')
            for i,roi in enumerate(rois):
                roigrp = root.create_group('%d' % i)
                # h5py only support utf8 strings at the moment, need to coerce data to
                # this representation
                roigrp.attrs['name'] = roi.name
                roigrp.attrs['viewdims'] = roi.slc.viewdims
                roigrp.attrs['arrslc'] = ROIPersistence.filter_viewdims(roi.slc)
                roigrp['poly'] = roi.poly

    @staticmethod
    def load(filename, slicer):
        rois = []
        with h5py.File(filename, 'r') as f:
            for roigrp in f['/rois'].itervalues():
                viewdims = roigrp.attrs['viewdims']
                arrslc = roigrp.attrs['arrslc']
                rois.append(
                    ROI(name=roigrp.attrs['name'],
                        poly=roigrp['poly'].value,
                        slc=SliceTuple.from_arrayslice(arrslc, viewdims),
                        slicer=slicer))
        return rois
