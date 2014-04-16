from PySide.QtCore import Qt, QEvent as QEV
from PySide.QtGui import QWidget, QVBoxLayout, QCheckBox, QGraphicsPixmapItem, QPixmap

from .drawing import PaintBrushItem
from ..events import MouseFilter


class PixelPainterTool(object):
    def __init__(self):
        self._origin = None

    def attach_event(self, graphics):
        self.paintbrush = PaintBrushItem(radius=5)
        self.roi_pixmapitem = QGraphicsPixmapItem()
        self.roi_pixmap = QPixmap(graphics._pixmap.size())
        graphics.scene().addItem(self.paintbrush)
        graphics.scene().addItem(self.roi_pixmapitem)

    def detach_event(self, graphics):
        graphics.scene().removeItem(self.paintbrush)
        graphics.scene().removeItem(self.roi_pixmapitem)

    def mouse_press_event(self, ev):
        self._origin = ev.mouse.pos

    def mouse_release_event(self, ev):
        self._origin = None

    def mouse_move_event(self, ev):
        self.paintbrush.setPos(ev.mouse.pos)
        
        if self._origin:
            self.paintbrush.fill_pixmap(self.roi_pixmap, self._origin)
            self.roi_pixmapitem.setPixmap(self.roi_pixmap)
            self._origin = ev.mouse.pos
        return True


class ROIPanel(object):
    def __init__(self, arrview):
        self.arrview = arrview

    def _state_changed(self, ev):
        self.arrview.add_tool(PixelPainterTool(), [
            MouseFilter(QEV.MouseMove), 
            MouseFilter([QEV.MouseMove, QEV.MouseButtonPress, QEV.MouseButtonRelease], 
                buttons=Qt.LeftButton)])

    def widget(self):
        drawbutton = QCheckBox('draw')
        drawbutton.stateChanged.connect(self._state_changed)
        panel = QWidget()
        panel.setLayout(QVBoxLayout())
        panel.layout().addWidget(drawbutton)
        return panel
