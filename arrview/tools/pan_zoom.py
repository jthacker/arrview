from PySide.QtCore import Qt
from PySide.QtGui import QGraphicsView

from traits.api import Enum

from arrview.tools.base import GraphicsTool, GraphicsToolFactory


class _PanTool(GraphicsTool):
    name = 'Pan'

    def init(self):
        self.origin = None
        self.prevCursor = None
        button = self.factory.button
        self.buttonTest = lambda mouse: getattr(mouse.buttons, button)

    def mouse_pressed(self):
        if self.buttonTest(self.mouse):
            self.origin = self.mouse.screenCoords
            self.prevCursor = self.graphics.cursor()
            self.graphics.setCursor(Qt.ClosedHandCursor)

    def mouse_moved(self):
        if self.buttonTest(self.mouse) and self.origin:
            vBar = self.graphics.verticalScrollBar()
            hBar = self.graphics.horizontalScrollBar();
            ox,oy = self.origin
            x,y = self.mouse.screenCoords
            dx,dy = x-ox,y-oy
            hBar.setValue(hBar.value() - dx)
            vBar.setValue(vBar.value() - dy)
            self.origin = (x,y)

    def mouse_released(self):
        if self.origin:
            self.graphics.setCursor(self.prevCursor)
            self.origin = None


class PanTool(GraphicsToolFactory):
    klass = _PanTool
    button = Enum('left','middle','right')


class _ZoomTool(GraphicsTool):
    name = 'Zoom'

    def init(self):
        self.graphics.setTransformationAnchor(
                QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._default_scale = self.graphics.transform().m11()

    def mouse_wheeled(self):
        currentScale = self.graphics.transform().m11()
        zoomIn = self.mouse.delta < 0
        s = 1.2 if zoomIn else 1/1.2
        lessThanMax = zoomIn and currentScale < 20
        greaterThanMin = not zoomIn and currentScale > 0.1
        if lessThanMax or greaterThanMin:
            self.graphics.scale(s,s)

    def mouse_double_clicked(self):
        if self.mouse.buttons.middle:
            s = self._default_scale
            self.graphics.scale(s,s)


class ZoomTool(GraphicsToolFactory):
    klass = _ZoomTool
