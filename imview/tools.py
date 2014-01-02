from PySide.QtGui import QGraphicsView, QPolygonF
from PySide.QtCore import QPointF

import numpy as np
import math

from . import settings
from .roi import ROI

class ImageTool(object):
    name = 'None'

    def __init__(self, view):
        self.view = view

    def init(self):
        pass

    def destroy(self):
        pass

    def mouse_pressed(self, mouse):
        pass

    def mouse_moved(self, mouse):
        pass

    def mouse_wheeled(self, mouse):
        pass


def _close_polygon(start, end):
    '''Given a start and end point, returns a set of integer points
    that will close the polygon with a straight line from start to
    end'''
    x0,y0 = start.x(), start.y()
    xrng = end.x() - x0
    yrng = end.y() - y0
    if xrng == 0 or yrng == 0:
        return []

    dx = math.copysign(1, xrng)
    dy = math.copysign(1, yrng)

    err = 0
    yerr = abs(yrng / xrng)
    pts = []
    y = y0
    x = x0
    for _ in range(1, int(abs(xrng))+1):
        x = x + dx
        pts.append(QPointF(x, y))
        err = err + yerr
        for e in range(int(err + 0.5)):
            y = y + dy
            err = err - 1
            pts.append(QPointF(x, y))
    return pts


class DrawROITool(ImageTool):
    name = 'Draw ROI'

    def init(self):
        self._initialPoint = None
        self._points = []
        self._activePoints = []

    def mouse_pressed(self, mouse):
        x,y = mouse.pos
        if self._initialPoint is None:
            self._initialPoint = QPointF(round(x),round(y))
            self._points = [self._initialPoint]

        else:
            self._initialPoint = None
            closedPts = _close_polygon(self._points[-1], self._points[0])
            self._points.extend(closedPts)
            roi = ROI(name='new roi')
            roi.add_poly(self.view.slicer.slc, np.array([(p.y(),p.x()) for p in self._points]))
            self.view.roiManager.add(roi)

    def mouse_moved(self, mouse):
        x,y = mouse.pos
        if self._initialPoint is not None:
            p = QPointF(x,y)
            v = p - self._initialPoint
            vx,vy = abs(v.x()), abs(v.y())
            if vx > vy:
                v.setY(0)
            else:
                v.setX(0)
            self._activePoints = self._points + [self._initialPoint + v]

            if vx >= 0.8 or vy >= 0.8:
                p1 = self._initialPoint + v
                p1 = QPointF(round(p1.x()), round(p1.y()))
                self._points.append(p1)
                self._initialPoint = p1

    def active_points(self):
        return self._activePoints


class ROISelectTool(ImageTool):
    name = 'ROI Select'

    def init(self):
        pass

    def mouse_pressed(self, mouse):
        pass


class PanAndZoomTool(ImageTool):
    name = 'Pan/Zoom'

    def init(self):
        self.view.graphics.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.graphics.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.currentScale = 1

    def destroy(self):
        self.view.graphics.setDragMode(QGraphicsView.NoDrag)

    def mouse_wheeled(self, mouse):
        zoomIn = mouse.delta < 0
        s = 1.2 if zoomIn else 1/1.2
        lessThanMax = zoomIn and self.currentScale < 20
        greaterThanMin = not zoomIn and self.currentScale > 0.1
        if lessThanMax or greaterThanMin:
            self.view.graphics.scale(s,s)
            self.currentScale *= s 

tools = [PanAndZoomTool, DrawROITool, ROISelectTool]
