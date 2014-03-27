from PySide.QtCore import Qt
from PySide.QtGui import QGraphicsView, QTransform

from ..util import Scale, rep

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
            ox,oy = self.origin
            x,y = mouse.screen_pos
            dx,dy = x-ox,y-oy
            hBar.setValue(hBar.value() - dx)
            vBar.setValue(vBar.value() - dy)
            self.origin = (x,y)

    def mouse_release_event(self, graphics, mouse):
        if self.origin:
            self.origin = None
            graphics.setCursor(self.prev_cursor)


class ZoomTool(object):
    def __init__(self, zoom_limits=Scale(0.1,20)):
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
        s = 1.0 / self._scale
        graphics.scale(s,s)
        self._scale = 1
