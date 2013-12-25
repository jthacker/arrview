from PySide.QtCore import *
from PySide.QtGui import *

import numpy as np

from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory
from traits.api import Instance, HasTraits, Tuple

from .. import colormapper as cm

class ArrayGraphicsView(QGraphicsView):
    '''ArrayGraphicsView is used for viewing a numpy array.
    Features:
    * Panning around with left click
    * Zooming with mouse wheel

    FIXME
    * Default cursor should be the pointer not a hand
    * When image is loaded it should be zoomed to fit the window
    * Maximum zoom should be based on pixel size
    '''
    mousemoved = Signal(float, float)
    mousepressed = Signal(float, float)
    mousereleased = Signal(float, float)
    
    def __init__(self, scene):
        super(ArrayGraphicsView,self).__init__(scene)
        self.setViewportUpdateMode(self.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.pixmapItem = QGraphicsPixmapItem()
        self.setDragMode(QGraphicsView.ScrollHandDrag)
 
        self.scene = scene
        self.scene.addItem(self.pixmapItem)
        self.setBackgroundBrush(QBrush(Qt.black))
        self.currentScale = 1

    def _to_item_coords(self, ev):
        sp = self.mapToScene(ev.pos())
        p = self.pixmapItem.mapFromScene(sp)
        return (p.x(), p.y())
  
    def mouseReleaseEvent(self, ev):
        super(ArrayGraphicsView, self).mouseReleaseEvent(ev)
        self.mousereleased.emit(*self._to_item_coords(ev))

    def mousePressEvent(self, ev):
        super(ArrayGraphicsView, self).mousePressEvent(ev)
        self.mousepressed.emit(*self._to_item_coords(ev))

    def mouseMoveEvent(self, ev):
        super(ArrayGraphicsView,self).mouseMoveEvent(ev)
        self.mousemoved.emit(*self._to_item_coords(ev))

    def wheelEvent(self, ev):
        zoomIn = ev.delta() < 0
        s = 1.2 if zoomIn else 1/1.2
        lessThanMax = zoomIn and self.currentScale < 20
        greaterThanMin = not zoomIn and self.currentScale > 0.1
        if lessThanMax or greaterThanMin:
            self.scale(s,s)
            self.currentScale *= s 

    def setPixmap(self, pixmap):
        '''Set the array to be viewed.
        Args:
        array (numpy array): the array to be viewed

        This will remove the previous array but maintain the previous scaling 
        as well as the panned position.
        '''
        self.pixmap = pixmap
        #self.scene.removeItem(self.pixmapItem)
        #self.pixmapItem = QGraphicsPixmapItem(self.pixmap)
        #self.scene.addItem(self.pixmapItem)
        self.pixmapItem.setPixmap(self.pixmap)

        # Constrain scene to be the boundary of the pixmap
        pad = 5
        r = self.pixmapItem.boundingRect()
        r = QRectF(r.left()-pad,r.top()-pad,r.width()+2*pad,r.height()+2*pad)
        self.scene.setSceneRect(r)

    def fitView(self):
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)


class MouseInput(HasTraits):
    pos = Tuple()


class _SlicerEditor(Editor):
    mouse = Instance(MouseInput)

    def init(self, parent):
        self._scene = QGraphicsScene()
        self.mouse = self.factory.mouse
        self.control = ArrayGraphicsView(self._scene)
        self.control.setPixmap(self.value)
        self.control.fitView()
        self.control.mousemoved.connect(self._mouse_moved)

    def update_editor(self):
        self.control.setPixmap(self.value)

    def _mouse_moved(self, x, y):
        self.mouse.pos = (x,y)


class SlicerEditor(BasicEditorFactory):
    klass = _SlicerEditor

    mouse = Instance(MouseInput)

