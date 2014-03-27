from __future__ import division
from PySide.QtCore import Qt, QRectF, QEvent
from PySide.QtGui import (QGraphicsView, QGraphicsScene,
        QGraphicsPixmapItem, QBrush, QPixmap)

class PixmapGraphicsView(QGraphicsView):
    '''ArrayGraphicsView is used for viewing a numpy array.
    '''
    
    def __init__(self, pixmap):
        super(PixmapGraphicsView, self).__init__()
        self.setViewportUpdateMode(self.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._pixmapItem = QGraphicsPixmapItem()
        self.setScene(QGraphicsScene())
        self.scene().addItem(self._pixmapItem)
        self.setBackgroundBrush(QBrush(Qt.black))
        self.setMouseTracking(True)
        self.setPixmap(pixmap)
        self.fitView()

    def screen_pos_to_pixmap_pos(self, pos):
        sp = self.mapToScene(pos)
        return self._pixmapItem.mapFromScene(sp)

    def mouseMoveEvent(self, ev):
        super(PixmapGraphicsView, self).mouseMoveEvent(ev)
        # Allow events to propagate to eventfilter
        ev.ignore()

    def mousePressEvent(self, ev):
        ev.ignore()

    def mouseReleaseEvent(self, ev):
        ev.ignore()

    def wheelEvent(self, ev):
        ev.ignore()

    def setPixmap(self, pixmap):
        '''Set the array to be viewed.
        Args:
        pixmap -- ndarray to be viewed

        Updates the pixmap array without changing the transformation matrix
        '''
        self._pixmap = pixmap
        self._pixmapItem.setPixmap(pixmap)

        # Constrain scene to be the boundary of the pixmap
        pad = 5
        r = self._pixmapItem.boundingRect()
        r = QRectF(r.left()-pad,r.top()-pad,r.width()+2*pad,r.height()+2*pad)
        self.setSceneRect(r)

    def fitView(self):
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
