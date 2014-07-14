#!/usr/bin/env python
import os

from traits.api import *
from traitsui.api import *
from traitsui.key_bindings import KeyBinding, KeyBindings

from .slicer import Slicer
from .roi import ROIManager, ROIPersistence 
from .colormapper import ColorMapper
from .file_dialog import open_file, save_file

from .ui.slicereditor import PixmapEditor
from .ui.dimeditor import SlicerDims
from .ui.tools import (ToolSet, CursorInfoTool, PanTool, ZoomTool, 
        ROIDrawTool, ROIDisplayTool, ROIEditTool, ColorMapTool)


bindings = KeyBindings(
    KeyBinding(binding1='Esc', 
        description='Escape Key',
        method_name='escape_pressed'))


class BottomPanel(HasTraits):
    slicerDims = Instance(SlicerDims)
    cmap = Instance(ColorMapper)

    view = View(
            Item('slicerDims', style='custom', show_label=False),
            Item('cmap', style='custom', show_label=False),
            )


class ArrayViewer(HasTraits):
    slicer = Instance(Slicer)
    pixmap = Property(depends_on=['bottomPanel.cmap.+',
        'bottomPanel.cmap.norm.+', 'slicer.view'])
    bottomPanel = Instance(BottomPanel)
    mode = Enum('pan','draw','move')
    roiManager = Instance(ROIManager)

    cursorInfo = Str
    colormapInfo = Str

    toolSet = Instance(ToolSet)

    def __init__(self, slicer, roi_filename=None):
        super(ArrayViewer, self).__init__()
        self.slicer = slicer
        slicerDims = SlicerDims(self.slicer)
        self.roiManager = ROIManager(
                slicer=self.slicer,
                slicerDims=slicerDims)
        self.bottomPanel = BottomPanel(
                slicerDims=slicerDims,
                cmap=ColorMapper(slicer=self.slicer))
        self.bottomPanel.cmap.norm.set_scale(slicer.arr)

        if roi_filename is None:
            self.roi_filename = os.path.join(os.path.abspath('.'))
        elif os.path.isdir(roi_filename):
            self.roi_filename = roi_filename
        else:
            rois = ROIPersistence.load(roi_filename)
            self.roiManager.rois.extend(rois)
            self.roi_filename = roi_filename

        self._defaultFactories = [
            CursorInfoTool(
                slicer=self.slicer,
                callback=self.update_cursorinfo),
            ColorMapTool(
                slicer=self.slicer,
                colorMapper=self.bottomPanel.cmap,
                callback=self.update_colormapinfo),
            PanTool(button='middle'),
            ZoomTool()]

        self._factoryMap = { 
            'pan' : [PanTool(button='left'), 
                        ROIDisplayTool(roiManager=self.roiManager)],
            'draw': [ROIDrawTool(roiManager=self.roiManager),
                        ROIDisplayTool(roiManager=self.roiManager)],
            'move': [ROIEditTool(roiManager=self.roiManager)],
            }

        self.toolSet = ToolSet()
        self.mode_changed()

    @on_trait_change('mode')
    def mode_changed(self):
        self.toolSet.factories = self._defaultFactories + self._factoryMap[self.mode]

    def update_cursorinfo(self, msg):
        self.cursorInfo = msg

    def update_colormapinfo(self, msg):
        self.colormapInfo = msg
  
    def default_traits_view(self):
        return View(
            VSplit(
                HSplit(
                    Item('pixmap', 
                        editor=PixmapEditor(toolSet=self.toolSet),
                        show_label=False,
                        width=0.9),
                    Group(
                        HGroup(
                            Item('mode', style='custom',springy=False),
                            Item(),
                            show_labels=False),
                        Item('roiManager', style='custom'),
                        show_labels=False)),
                Item('bottomPanel', style='custom', show_label=False,
                    height=1)),
            statusbar = [
                StatusItem(name='cursorInfo'),
                StatusItem(name='colormapInfo')],
            menubar = MenuBar(
                Menu(
                    Action(name='Save', action='_save_rois'),
                    Action(name='Load', action='_load_rois'),
                    name='File')),
            resizable=True,
            title='Array Viewer',
            key_bindings=bindings,
            handler=ArrayViewerHandler(loadSaveFile=self.roi_filename))

    @cached_property
    def _get_pixmap(self):
        return self.bottomPanel.cmap.array_to_pixmap(self.slicer.view)


class ArrayViewerHandler(Controller):
    loadSaveFile = File

    def _save_rois(self, info):
        filename = save_file(file_name=self.loadSaveFile)
        if filename:
            self.loadSaveFile = filename
            ROIPersistence.save(info.object.roiManager.rois, filename)

    def _load_rois(self, info):
        filename = open_file(file_name=self.loadSaveFile)
        if filename:
            self.loadSaveFile = filename
            rois = ROIPersistence.load(filename)
            info.object.roiManager.rois.extend(rois)
    
    def escape_pressed(self, info):
        '''Prevent escape key from closing the window'''
        pass


if __name__ == '__main__':
    import numpy as np
    from operator import mul
    from . import view

    arr = np.random.random(32*43*53*23).reshape(32,43,53,23)
    view(arr)
