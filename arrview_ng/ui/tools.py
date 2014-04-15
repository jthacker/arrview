from PySide.QtCore import Qt, Signal, QObject, QPointF
from PySide.QtGui import QGraphicsView, QTransform

from ..util import Scale, rep, clamp

class PanTool(object):
    def __init__(self):
        self.origin = None
        self.prev_cursor = None

    def mouse_press_event(self, graphics, mouse):
        self.origin = mouse.screen_pos
        self.prev_cursor = graphics.cursor()
        graphics.setCursor(Qt.ClosedHandCursor)
    
    def mouse_move_event(self, graphics, mouse):
        if self.origin:
            vBar = graphics.verticalScrollBar()
            hBar = graphics.horizontalScrollBar()
            ox,oy = self.origin.x(), self.origin.y()
            x,y = mouse.screen_pos.x(), mouse.screen_pos.y()
            dx,dy = x-ox,y-oy
            hBar.setValue(hBar.value() - dx)
            vBar.setValue(vBar.value() - dy)
            self.origin = mouse.screen_pos

    def mouse_release_event(self, graphics, mouse):
        if self.origin:
            self.origin = None
            graphics.setCursor(self.prev_cursor)


class ZoomTool(object):
    def __init__(self, zoom_limits=Scale(0.1,50)):
        self.limits = zoom_limits
        self._scale = 1

    def attach_event(self, graphics):
        graphics.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def mouse_wheel_event(self, graphics, mouse):
        scale = graphics.transform().m11()
        zoomin = mouse.wheel_delta < 0
        zoomout = not zoomin
        above_min = scale >= self.limits.low
        below_max = scale < self.limits.high
        if (zoomout and above_min) or (zoomin and below_max):
            s = 1.2 if zoomin else 1/1.2
            graphics.scale(s,s)
            self._scale *= s

    def mouse_double_click_event(self, graphics, mouse):
        self._scale = 1
        graphics.fitView()


class ArrayValueFromCursorTool(QObject):
    status = Signal(dict)

    def __init__(self, slicer):
        super(ArrayValueFromCursorTool, self).__init__()
        self.slicer = slicer

    def mouse_move_event(self, graphics, mouse):
        x,y = mouse.pos.x(), mouse.pos.y()
        slc = list(self.slicer.slc)
        xDim,yDim = self.slicer.slc.viewdims
        slc[xDim], slc[yDim] = x,y
        
        view = self.slicer.view
        shape = view.shape
        xMax,yMax = shape[1],shape[0]

        val = None
        if 0 <= x < xMax and 0 <= y < yMax:
            val = view[y,x]

        self.status.emit({'slc': slc, 'val': val})

        return False


class ColorMapTool(object):
    def __init__(self, arrview):
        self.origin = None
        self.arrview = arrview

    def mouse_press_event(self, graphics, mouse):
        self.origin = mouse.screen_pos
        vmin,vmax = self.arrview.cmap.scale
        self.iwidth = vmax - vmin
        self.icenter = (vmax - vmin) / 2.0 + vmin

    def mouse_move_event(self, graphics, mouse):
        if self.origin is not None:
            pos = mouse.screen_pos
            low,high = self.arrview.cmap.limits

            scale = lambda dw: 0.001 * (high - low) * dw
            center = self.icenter + scale(pos.x() - self.origin.x())
            halfwidth = (self.iwidth - scale(pos.y() - self.origin.y())) / 2.0
            vmin = clamp(center - halfwidth, low, high)
            vmax = clamp(center + halfwidth, low, high)
            self.arrview.cmap.scale = Scale(vmin, vmax)

    def mouse_double_click_event(self, graphics, mouse):
        self.origin = None
        self.arrview.cmap.reset()
