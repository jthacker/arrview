from PySide.QtCore import Qt, Signal, QRectF
from PySide.QtGui import (QGraphicsView, QGraphicsPixmapItem,
        QGraphicsScene, QBrush)

from traits.api import (Instance, HasTraits, Int, WeakRef,
        on_trait_change, List)
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory

from .tools import ToolSet, MouseState, MouseButtons

class ArrayGraphicsView(QGraphicsView):
    '''ArrayGraphicsView is used for viewing a numpy array.

    TODO:
    * When image is loaded it should be zoomed to fit the window
    * Maximum zoom should be based on pixel size
    '''
    mousemoved = Signal(object)
    mousewheeled = Signal(object)
    mousedoubleclicked = Signal(object)
    mousepressed = Signal(object)
    mousereleased = Signal(object)
    
    def __init__(self):
        super(ArrayGraphicsView, self).__init__()
        self.setViewportUpdateMode(self.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.pixmapItem = QGraphicsPixmapItem()
        self.setScene(QGraphicsScene())
        self.scene().addItem(self.pixmapItem)
        self.setBackgroundBrush(QBrush(Qt.black))
        self.setMouseTracking(True)

    def mouseevent_to_item_coords(self, ev):
        sp = self.mapToScene(ev.pos())
        p = self.pixmapItem.mapFromScene(sp)
        return (p.x(), p.y())
  
    def mouseReleaseEvent(self, ev):
        super(ArrayGraphicsView, self).mouseReleaseEvent(ev)
        self.mousereleased.emit(ev)

    def mousePressEvent(self, ev):
        super(ArrayGraphicsView, self).mousePressEvent(ev)
        self.mousepressed.emit(ev)

    def mouseMoveEvent(self, ev):
        super(ArrayGraphicsView, self).mouseMoveEvent(ev)
        self.mousemoved.emit(ev)

    def mouseDoubleClickEvent(self, ev):
        super(ArrayGraphicsView, self).mouseDoubleClickEvent(ev)
        self.mousedoubleclicked.emit(ev)

    def wheelEvent(self, ev):
        self.mousewheeled.emit(ev)
        
    def setPixmap(self, pixmap):
        '''Set the array to be viewed.
        Args:
        array (numpy array): the array to be viewed

        This will remove the previous array but maintain the previous scaling 
        as well as the panned position.
        '''
        self.pixmap = pixmap
        self.pixmapItem.setPixmap(self.pixmap)

        # Constrain scene to be the boundary of the pixmap
        pad = 5
        r = self.pixmapItem.boundingRect()
        r = QRectF(r.left()-pad,r.top()-pad,r.width()+2*pad,r.height()+2*pad)
        self.setSceneRect(r)

    def fitView(self):
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)


class _PixmapEditor(Editor):
    mouse = Instance(MouseState, MouseState)
    toolSet = Instance(ToolSet)

    def init(self, parent):
        self.control = ArrayGraphicsView()
        self.control.mousemoved.connect(self._mouse_moved)
        self.control.mousepressed.connect(self._mouse_pressed)
        self.control.mousewheeled.connect(self._mouse_wheel_moved)
        self.control.mousereleased.connect(self._mouse_released)
        self.control.mousedoubleclicked.connect(self._mouse_double_clicked)
        self.control.setPixmap(self.value)
        self.control.fitView()
        self._tools = []
        self.toolSet = self.factory.toolSet

    @on_trait_change('toolSet.factories')
    def factories_changed(self):
        for tool in self._tools:
            tool.destroy()
        self.mouse = MouseState()
        self._tools = self.toolSet.init_tools(self.control, self.mouse)

    def update_editor(self):
        self.control.setPixmap(self.value)

    def _config_mouse(self, ev):
        self.mouse.coords = self.control.mouseevent_to_item_coords(ev)
        self.mouse.screenCoords = (ev.pos().x(), ev.pos().y())
        buttons = MouseButtons(
            left    = ev.buttons() & Qt.LeftButton,
            middle  = ev.buttons() & Qt.MiddleButton,
            right   = ev.buttons() & Qt.RightButton)
        self.mouse.buttons = buttons

    def _mouse_moved(self, ev):
        self._config_mouse(ev)
        self.mouse.moved = True

    def _mouse_pressed(self, ev):
        self._config_mouse(ev)
        self.mouse.pressed = True

    def _mouse_wheel_moved(self, ev):
        self._config_mouse(ev)
        self.mouse.delta = ev.delta()
        self.mouse.wheeled = True

    def _mouse_released(self, ev):
        self._config_mouse(ev)
        self.mouse.released = True

    def _mouse_double_clicked(self, ev):
        self._config_mouse(ev)
        self.mouse.doubleclicked = True


class PixmapEditor(BasicEditorFactory):
    klass = _PixmapEditor
    toolSet = Instance(ToolSet)
