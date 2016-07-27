from __future__ import absolute_import

from traits.api import Callable, Instance, on_trait_change

from arrview.slicer import Slicer
from arrview.tools.base import GraphicsTool, GraphicsToolFactory


class _CursorInfoTool(GraphicsTool):
    name = 'CursorInfo'
    slicer = Instance(Slicer)
    callback = Callable

    def init(self):
        self.slicer = self.factory.slicer
        self.callback = self.factory.callback

    def mouse_moved(self):
        self.update()

    @on_trait_change('slicer:view')
    def update(self):
        x, y = map(int, self.mouse.coords)
        slc = list(self.slicer.slc)
        xDim,yDim = self.slicer.slc.viewdims
        slc[xDim], slc[yDim] = x, y
        
        view = self.slicer.view
        shape = view.shape
        xMax, yMax = shape[1], shape[0]

        msg = '(%s) ' % ','.join(['%03d' % p for p in slc])
        if 0 <= x < xMax and 0 <= y < yMax:
            msg += "%0.2f" % view[y, x]
        else:
            msg += "  "
        self.callback(msg)


class CursorInfoTool(GraphicsToolFactory):
    klass = _CursorInfoTool
    slicer = Instance(Slicer)
    callback = Callable
