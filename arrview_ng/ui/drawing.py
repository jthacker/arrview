from PySide.QtCore import Qt, QRectF
from PySide.QtGui import (QGraphicsPixmapItem, QPixmap, QPainter,
        QGraphicsItem)

import skimage as ski
import skimage.draw

class PaintBrushItem(QGraphicsItem):
    '''PaintBrushItem is a QGraphicsItem that anchors to pixel locations.'''

    def __init__(self):
        super(PaintBrushItem, self).__init__()
        self._color = Qt.black
        self._points = []
        self._connect_points = True
        self.set_radius(0)

    def set_color(self, color):
        self._color = color
        self._update_cursor()

    def set_radius(self, r):
        self._radius = r

        if r == 0:
            pts = [(0,0)]
        else:
            pts = zip(*ski.draw.circle_perimeter(r,r,r))
            pts += zip(*ski.draw.circle(r,r,r))
        self._points = [QPointF(x,y) for x,y in pts]
        self._update_cursor()

    def _update_cursor(self):
        x = (2*self._radius+1)
        w,h = x,x
        pixmap = QPixmap(w,h)
        pixmap.fill(Qt.transparent)
        
        p = QPainter(pixmap)
        p.drawPoints(self._points)
        p.end()

        self._cursor_pixmap = pixmap.createMaskFromColor(Qt.transparent)

    def _paint_cursor(self, p):
        p.save()
        p.setPen(self._color)
        p.translate(-self._radius, -self._radius)
        w,h = self._cursor_pixmap.width(),self._cursor_pixmap.height()
        rect = QRectF(0,0,w,h)
        p.drawPixmap(rect, self._cursor_pixmap, rect)
        p.restore()

    def snap_pos(self, pos):
        f = lambda a: int(math.floor(a))
        return QPointF(f(pos.x()),f(pos.y()))

    def setPos(self, pos):
        super(PaintBrushItem, self).setPos(self.snap_pos(pos))
    
    def paint(self, p, option, widget):
        r = self._radius
        self._paint_cursor(p)
        p.drawEllipse(-r,-r,2*r+1,2*r+1)

    def boundingRect(self):
        r = self._radius
        return QRectF(0,0,2*r+1,2*r+1)

    def fill_pixmap(self, pixmap, origin):
        ox,oy = self.snap_pos(origin)
        pos = self.pos()
        snapped_pos = self.snap_pos(pos)
        cx,cy = snapped_pos.x(),snapped_pos.y()

        p = QPainter(pixmap)
        p.setCompositionMode(QPainter.CompositionMode_Source)

        if self._connect_points:
            ## This method of extending a line between points works quite well
            ## but it is very slow when the radius of the circle is large, which
            ## essential results in a lot of duplicate drawing.
            p.translate(ox,oy)
            px,py = 0,0
            for x,y in zip(*ski.draw.line(0,0,cx-ox,cy-oy)):
                p.translate(x-px,y-py)
                px,py = x,y
                self._paint_cursor(p)
        else:
            p.translate(cx, cy)
            self._paint_cursor(p)

        p.end()

