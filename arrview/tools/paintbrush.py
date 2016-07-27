from PySide.QtCore import Qt, QRectF, QPoint, QPointF
from PySide.QtGui import (QGraphicsItem, QGraphicsPixmapItem, QPixmap, QPainter)

import logging
import math
import skimage as ski
import skimage.draw


log = logging.getLogger(__name__)


class PaintBrushItem(QGraphicsItem):
    """PaintBrushItem is a QGraphicsItem that anchors to pixel locations."""

    def __init__(self, radius=0, color=Qt.black):
        super(PaintBrushItem, self).__init__()
        self._color = color
        self._points = []
        self._connect_points = True
        self.set_radius(radius)

    def set_color(self, color):
        self._color = color
        self._update_cursor()

    @property
    def diameter(self):
        return 2 * self._radius + 1

    def set_radius(self, r):
        self.prepareGeometryChange()
        self._radius = r
        if r == 0:
            pts = [(0, 0)]
        else:
            pts = zip(*ski.draw.circle_perimeter(r, r, r))
            pts += zip(*ski.draw.circle(r, r, r))
        self._points = [QPointF(x, y) for x, y in pts]
        self._update_cursor()

    def _update_cursor(self):
        x = self.diameter
        w, h = x, x
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.drawPoints(self._points)
        p.end()
        self._cursor_pixmap = pixmap.createMaskFromColor(Qt.transparent)

    def _paint_cursor(self, p):
        p.save()
        p.setPen(self._color)
        p.translate(-self._radius, -self._radius)
        w, h = self._cursor_pixmap.width(), self._cursor_pixmap.height()
        rect = QRectF(0, 0, w, h)
        p.drawPixmap(rect, self._cursor_pixmap, rect)
        p.restore()
        self.update()

    def snap_pos(self, pos):
        f = lambda a: int(math.floor(a))
        return QPoint(f(pos.x()), f(pos.y()))

    def setPos(self, pos):
        super(PaintBrushItem, self).setPos(self.snap_pos(pos))

    def paint(self, p, option, widget):
        r = self._radius
        self._paint_cursor(p)
        p.drawEllipse(-r, -r, self.diameter, self.diameter)

    def boundingRect(self):
        r = self._radius
        return QRectF(0, 0, self.diameter, self.diameter)

    def fill_pixmap(self, pixmap, origin, position):
        origin = self.snap_pos(origin)
        pos = self.snap_pos(position)
        ox, oy = origin.x(), origin.y()
        cx, cy = pos.x(), pos.y()
        p = QPainter(pixmap)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        if self._connect_points:
            ## This method of extending a line between points works quite well
            ## but it is very slow when the radius of the circle is large, which
            ## essential results in a lot of duplicate drawing.
            p.translate(ox, oy)
            px, py = 0, 0
            for x, y in zip(*ski.draw.line(0, 0, cx-ox, cy-oy)):
                p.translate(x-px, y-py)
                px, py = x, y
                self._paint_cursor(p)
        else:
            p.translate(cx, cy)
            self._paint_cursor(p)
        p.end()
