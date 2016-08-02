from collections import namedtuple, OrderedDict
from itertools import izip
import logging
import os
import time

import numpy as np

from traits.api import (HasTraits, HasPrivateTraits, List, Instance, Property,
    Any, Str, Int, Bool, Float, Button, DelegatesTo, WeakRef, Array, File,
    on_trait_change, cached_property, TraitError, Event, Color)

from traitsui.api import View, Item, HGroup, TableEditor, ColorEditor
from traitsui.extras.checkbox_column import CheckboxColumn
from traitsui.menu import OKCancelButtons
from traitsui.table_column import ObjectColumn, NumericColumn

from arrview.color import color_generator
from arrview.util import rep
from arrview.slicer import Slicer, SliceTuple
from arrview.ui.dimeditor import SlicerDims


log = logging.getLogger(__name__)


class ROI(HasPrivateTraits):
    name = Str
    color = Color
    visible = Bool(True)
    mask = Array
    updated = Event

    def set_mask(self, mask, slc):
        mask_view = self.mask[slc.view_slice]
        if slc.is_transposed:
            mask = mask.T
        self.mask[slc.view_slice] = mask
        self.updated = True

    def mask_arr(self, arr):
        return np.ma.array(arr, mask=~self.mask)

    def __repr__(self):
        return rep(self, ['name', 'color'])


class ROIView(HasTraits):
    roi = Instance(ROI)
    arr = Any
    name = DelegatesTo('roi')
    color = DelegatesTo('roi')
    visible = DelegatesTo('roi')
    index = Int()

    mean = Property
    _mean = Float
    std = Property
    _std = Float
    size = Property
    _size = Int

    def __init__(self, **traits):
        super(ROIView, self).__init__(**traits)
        self.update_stats()

    @on_trait_change('roi:updated')
    def update_stats(self):
        masked_data = self.arr[self.roi.mask]
        self._size = masked_data.size
        if len(masked_data) == 0:
            self._mean = float('nan')
            self._std = float('nan')
        else:
            self._mean = masked_data.mean()
            self._std = masked_data.std()

    def _get_mean(self):
        return self._mean

    def _get_std(self):
        return self._std

    def _get_size(self):
        return self._size

    def __repr__(self):
        return rep(self, ['name','size','mean','std', 'color'])


class CustomColorColumn(ObjectColumn):
    def _get_color(self, object):
        color = getattr(object, self.name).toTuple()
        rgb = tuple(int(x) for x in color[:3])
        return rgb

    def get_cell_color(self, object):
        return self._get_color(object)

    def set_value(self, object, row, value):
        print("set_value", args, kwargs)
        return super(CustomColorColumn, self).set_value(object, row, value)

    def get_text_color(self, object):
        return self._get_color(object)

    def get_value(self, object):
        return ""


roi_editor = TableEditor(
    sortable = False,
    configurable = False,
    auto_size = True,
    show_toolbar = False,
    selection_mode = 'rows',
    selected = 'selection',
    columns = [
        NumericColumn(name='index', label='#', editable=False),
        CheckboxColumn(name='visible', label='', editable=True),
        CustomColorColumn(name='color', label='', editable=False),
        ObjectColumn(name='name', label='Name', editable=True),
        NumericColumn(name='mean', label='Mean', editable=False, format='%0.2f'),
        ObjectColumn(name='std', label='STD', editable=False, format='%0.2f'),
        ObjectColumn(name='size', label='Size', editable=False)])


class ROIManager(HasTraits):
    slicer = Instance(Slicer)
    rois = List(ROI, [])
    roiviews = List(ROIView, [])
    selection = List(ROIView, [])
    next_id = Int(0)
    slicerDims = Instance(SlicerDims)
    freedim = DelegatesTo('slicerDims')

    new = Button
    delete = Button

    view = View(
            Item('roiviews',
                editor=roi_editor,
                show_label=False),
            HGroup(
                Item('new', show_label=False),
                Item('delete',
                    enabled_when='len(selection) > 0',
                    show_label=False)))

    def __init__(self, **traits):
        self._statsmap = OrderedDict()
        self._color_gen = color_generator()
        super(ROIManager, self).__init__(**traits)

    @on_trait_change('rois[]')
    def rois_updated(self, obj, trait, old, new):
        for roi in old:
            del self._statsmap[roi]
        for roi in new:
            self._statsmap[roi] = ROIView(roi=roi, arr=self.slicer.arr)
        roiviews = self._statsmap.values()
        for i, rv in enumerate(roiviews, start=1):
            rv.index = i
        self.roiviews = self._statsmap.values()
        # reset next_id and color_gen if rois is empty
        if len(self.rois) == 0:
            self.next_id = 0
            self._color_gen = color_generator()

    def _next_roi_color(self):
        return tuple(255 * ch for ch in self._color_gen.next())

    def new_roi(self):
        roi = ROI(name='roi_%02d' % self.next_id,
                  color=self._next_roi_color(),
                  mask=np.zeros(self.slicer.shape, dtype=bool))
        self.rois.append(roi)
        self.next_id += 1
        self.selection = [self._statsmap[roi]]
        return roi

    def add_rois(self, rois):
        """Add ROIs to ROIManager, increments next ROI ID and color"""
        for roi in rois:
            roi.color = self._next_roi_color()
            self.rois.append(roi)
            self.next_id += 1

    def update_mask(self, roi, mask):
        roi.set_mask(mask, self.slicer.slc)

    def select_roi_by_index(self, index):
        if 1 <= index <= len(self.roiviews):
            self.selection = [self.roiviews[index - 1]]
        else:
            log.debug('index %s is invalid for current roi list', index)

    def by_name(self, name):
        return [roi for roi in self.rois if roi.name==name]

    def names(self):
        return set(roi.name for roi in self.rois)

    def _new_fired(self):
        self.new_roi()

    def _delete_fired(self):
        selected_rois = set(rv.roi for rv in self.selection)
        self.rois = [r for r in self.rois if r not in selected_rois]
        self.selection = []
