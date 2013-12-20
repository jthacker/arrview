from PySide.QtCore import *
from PySide.QtGui import *

import numpy as np
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory

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

    def setArray(self, array):
        '''Set the array to be viewed.
        Args:
        array (numpy array): the array to be viewed

        This will remove the previous array but maintain the previous scaling 
        as well as the panned position.
        '''
        def cm_ident(a):
            return np.dstack((a,a,a))

        def norm(a):
            min = a.min()
            max = a.max()
            return (a - min) / (max - min)

        self.pixmap = cm.ndarray_to_arraypixmap(array, cmap=cm_ident, norm=norm)
        #self.scene.removeItem(self.pixmapItem)
        #self.pixmapItem = QGraphicsPixmapItem(self.pixmap)
        #self.scene.addItem(self.pixmapItem)
        self.pixmapItem.setPixmap(self.pixmap)

        # Constrain scene to be the boundary of the pixmap
        pad = 5
        r = self.pixmapItem.boundingRect()
        r = QRectF(r.left()-pad,r.top()-pad,r.width()+2*pad,r.height()+2*pad)
        self.scene.setSceneRect(r)

    def fitArray(self):
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)


class _SlicerEditor(Editor):
    def init(self, parent):
        self._scene = QGraphicsScene()
        self.control = ArrayGraphicsView(self._scene)
        self.control.setArray(self.value)
        self.control.fitArray()

    def update_editor(self):
        print('update_editor')


class SlicerEditor(BasicEditorFactory):
    klass = _SlicerEditor

