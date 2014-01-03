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

    cmap = Instance(ColorMapper, ColorMapper)
    
    colorMapTool = Instance(ColorMapTool)
    colorMapToolMsg = DelegatesTo('colorMapTool', prefix='msg')

    cursorInfo = Instance(CursorInfoTool)
    cursorInfoMsg = DelegatesTo('cursorInfo', prefix='msg')

    roiDrawTool = Instance(ROIDrawTool)
    roiManager = Instance(ROIManager, ROIManager)

    def __init__(self, arr):
        super(ImageViewer, self).__init__()
        self.slicer = Slicer(arr)
        self.cursorInfo = CursorInfoTool(slicer=self.slicer)
        self.roiDrawTool = ROIDrawTool(slicer=self.slicer, roiManager=self.roiManager)
        self.slicerDims = SlicerDims(self.slicer)
        self.colorMapTool = ColorMapTool(slicer=self.slicer, colorMapper=self.cmap)
        self.cmap.norm.set_scale(arr)
  
    def default_traits_view(self):
        tools = [self.cursorInfo, 
                 self.colorMapTool,
                 self.roiDrawTool,
                 ROIDisplayTool(slicer=self.slicer, roiManager=self.roiManager),
                 ZoomTool()]
        return View(
                HGroup(
                    Group(
                        Item('pixmap', 
                            editor=PixmapEditor(tools=tools),
                            show_label=False),
                        Item('slicerDims', style='custom', show_label=False),
                        Item('cmap', style='custom', show_label=False)),
                    Group(
                        Item('roiManager', style='custom', show_label=False))),
                statusbar = [StatusItem(name='cursorInfoMsg'),
                             StatusItem(name='colorMapToolMsg')],
                resizable=True)

    def _get_pixmap(self):
        return self.cmap.array_to_pixmap(self.slicer.view)

    @on_trait_change('slicerDims.freedim.val')
    def update_cursor_info(self):
        self.cursorInfo.update()


if __name__ == '__main__':
    import numpy as np
    from operator import mul

    s = np.linspace(-1,1,128)
    [X,Y,T] = np.meshgrid(s,s,s)
    arr = np.cos(2*np.pi*X)*np.sin(2*np.pi*Y)*np.exp(-1*T)
    iv = ImageViewer(arr)
    iv.configure_traits()
