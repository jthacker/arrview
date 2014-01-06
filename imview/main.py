#!/usr/bin/env python
from traits.api import *
from traitsui.api import *

from .slicer import Slicer
from .roi import ROIManager 
from .colormapper import ColorMapper

from .ui.slicereditor import PixmapEditor
from .ui.dimeditor import SlicerDims
from .ui.tools import (CursorInfoTool, PanTool, ZoomTool, 
        ROIDrawTool, ROIDisplayTool, ColorMapTool)


class ImageViewer(HasTraits):
    slicer = Instance(Slicer)
    pixmap = Property(depends_on=['cmap.+','cmap.norm.+', 'slicer.view'])
    slicerDims = Instance(SlicerDims)

    cmap = Instance(ColorMapper)
    roiManager = Instance(ROIManager, ROIManager)

    cursorInfo = Str
    colormapInfo = Str

    def __init__(self, arr):
        super(ImageViewer, self).__init__()
        self.slicer = Slicer(arr)
        self.slicerDims = SlicerDims(self.slicer)
        self.cmap = ColorMapper(slicer=self.slicer)
        self.cmap.norm.set_scale(arr)

    def update_cursorinfo(self, msg):
        self.cursorInfo = msg

    def update_colormapinfo(self, msg):
        self.colormapInfo = msg
  
    def default_traits_view(self):
        tools = [
                CursorInfoTool(
                    slicer=self.slicer,
                    callback=self.update_cursorinfo),
                ColorMapTool(
                    slicer=self.slicer,
                    colorMapper=self.cmap,
                    callback=self.update_colormapinfo),
                ROIDrawTool(
                    slicer=self.slicer, 
                    roiManager=self.roiManager),
                ROIDisplayTool(
                    slicer=self.slicer, 
                    roiManager=self.roiManager),
                ZoomTool()]

        return View(
                VSplit(
                    HSplit(
                        Item('pixmap', 
                            editor=PixmapEditor(tools=tools),
                            show_label=False),
                        Item('roiManager', style='custom', show_label=False,
                            width=150)),
                    Group(
                        Item('slicerDims', style='custom', show_label=False),
                        Item('cmap', style='custom', show_label=False))),
                statusbar = [
                    StatusItem(name='cursorInfo'),
                    StatusItem(name='colormapInfo')],
                resizable=True)

    def _get_pixmap(self):
        return self.cmap.array_to_pixmap(self.slicer.view)


if __name__ == '__main__':
    import numpy as np
    from operator import mul

    s = np.linspace(-1,1,64)
    z = np.linspace(-1,1,23)
    [X,Y,T,Z] = np.meshgrid(s,s,s,z)
    arr = np.cos(2*np.pi*X)*np.sin(2*np.pi*Y)*np.exp(-1*T)+10*Z
    iv = ImageViewer(arr)
    iv.configure_traits()
