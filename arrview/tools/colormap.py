from traits.api import Callable, Instance, on_trait_change

from arrview.colormapper import ColorMapper
from arrview.slicer import Slicer
from arrview.tools.base import GraphicsTool, GraphicsToolFactory
from arrview.util import clamp


class _ColorMapTool(GraphicsTool):
    name = 'ColorMapTool'
    colorMapper = Instance(ColorMapper)
    slicer = Instance(Slicer)
    callback = Callable
    
    def init(self):
        self.origin = None
        self.slicer = self.factory.slicer
        self.callback = self.factory.callback
        self.colorMapper = self.factory.colorMapper

    def mouse_pressed(self):
        if self.mouse.buttons.right:
            self.origin = self.mouse.screenCoords
            norm = self.colorMapper.norm
            vmin,vmax = norm.vmin,norm.vmax
            self.iwidth = vmax - vmin
            self.icenter = (vmax - vmin) / 2.0 + vmin

    def mouse_moved(self):
        if self.mouse.buttons.right and self.origin:
            origin = self.origin
            coords = self.mouse.screenCoords
            norm = self.colorMapper.norm
            low,high = norm.low,norm.high

            scale = lambda dw: 0.001 * (high - low) * dw
            center = self.icenter + scale(coords[0] - origin[0])
            halfwidth = (self.iwidth - scale(coords[1] - origin[1])) / 2.0
            norm.vmin = clamp(center - halfwidth, low, high)
            norm.vmax = clamp(center + halfwidth, low, high)

    def mouse_double_clicked(self):
        if self.mouse.buttons.right:
            self.colorMapper.norm.set_scale(self.slicer.view)

    @on_trait_change('colorMapper.norm.+')
    def update_callback(self):
        norm = self.colorMapper.norm
        self.callback('cmap: [%0.2f, %0.2f]' % (norm.vmin, norm.vmax))


class ColorMapTool(GraphicsToolFactory):
    klass = _ColorMapTool
    slicer = Instance(Slicer)
    colorMapper = Instance(ColorMapper)
    callback = Callable


