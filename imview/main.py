#!/usr/bin/env python
from traits.api import *
from traitsui.api import *
from traitsui.menu import Menu, Action, MenuBar


from .slicer import Slicer
from .roi import ROIManager, ROIPersistence 
from .colormapper import ColorMapper
from .file_dialog import open_file, save_file

from .ui.slicereditor import PixmapEditor
from .ui.dimeditor import SlicerDims
from .ui.tools import (ToolSet, CursorInfoTool, PanTool, ZoomTool, 
        ROIDrawTool, ROIDisplayTool, ROIEditTool, ColorMapTool)

class BottomPanel(HasTraits):
    slicerDims = Instance(SlicerDims)
    cmap = Instance(ColorMapper)

    view = View(
            Item('slicerDims', style='custom', show_label=False),
            #Item('cmap', style='custom', show_label=False),
            )

class ImageViewer(HasTraits):
    slicer = Instance(Slicer)
    pixmap = Property(depends_on=['bottomPanel.cmap.+',
        'bottomPanel.cmap.norm.+', 'slicer.view'])
    bottomPanel = Instance(BottomPanel)
    mode = Enum('pan','draw','move')
    roiManager = Instance(ROIManager)

    cursorInfo = Str
    colormapInfo = Str

    toolSet = Instance(ToolSet)

    def __init__(self, arr):
        super(ImageViewer, self).__init__()
        self.slicer = Slicer(arr)
        slicerDims = SlicerDims(self.slicer)
        self.roiManager = ROIManager(
                slicer=self.slicer,
                slicerDims=slicerDims)
        self.bottomPanel = BottomPanel(
                slicerDims=slicerDims,
                cmap=ColorMapper(slicer=self.slicer))
        self.bottomPanel.cmap.norm.set_scale(arr)

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
            handler=ImageViewerHandler())

    def _get_pixmap(self):
        return self.bottomPanel.cmap.array_to_pixmap(self.slicer.view)


class ImageViewerHandler(Controller):
    loadSaveFile = File

    def _loadSaveFile_default(self):
        return os.path.join(os.path.abspath('.'))

    def _save_rois(self, info):
        filename = save_file(file_name=self.loadSaveFile)
        if filename:
            self.loadSaveFile = filename
            ROIPersistence.save(info.object.roiManager.rois, filename)

    def _load_rois(self, info):
        filename = open_file(file_name=self.loadSaveFile)
        if filename:
            self.loadSaveFile = filename
            rois = ROIPersistence.load(filename, info.object.slicer)
            info.object.roiManager.rois.extend(rois)



if __name__ == '__main__':
    import numpy as np
    from operator import mul

    s = np.linspace(-1,1,64)
    z = np.linspace(-1,1,23)
    [X,Y,T,Z] = np.meshgrid(s,s,s,z)
    arr = np.cos(2*np.pi*X)*np.sin(2*np.pi*Y)*np.exp(-2*T)+10*Z
    iv = ImageViewer(arr)
    iv.configure_traits()
