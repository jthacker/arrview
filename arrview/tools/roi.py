import math

import numpy as np

from PySide.QtGui import QGraphicsPolygonItem, QMatrix, QPolygonF
from PySide.QtCore import QPointF, Qt

from traits.api import Bool, Instance, on_trait_change

from arrview import settings
from arrview.roi import ROI, ROIManager
from arrview.tools.base import GraphicsTool, GraphicsToolFactory


def _close_polygon(start, end):
    """Given a start and end point, returns a set of integer points
    that will close the polygon with a straight line from start to end
    """
    x0,y0 = start.x(), start.y(),

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


class _ROIDrawTool(GraphicsTool):
    name = 'Draw ROI'
    roiManager = Instance(ROIManager)

    def init(self):
        self._origin = None
        self._points = []
        self._polyItem = self.graphics.scene().addPolygon(QPolygonF(),
                settings.default_roi_pen(), settings.default_roi_brush())
        self.roiManager = self.factory.roiManager

    def destroy(self):
        self.graphics.scene().removeItem(self._polyItem)

    def mouse_pressed(self):
        if self.mouse.buttons.left:
            x,y = self.mouse.coords
            if self._origin is None:
                self._origin = QPointF(round(x),round(y))
                self._points = [self._origin]
            else:
                self._origin = None
                closedPts = _close_polygon(self._points[-1], self._points[0])
                self._points.extend(closedPts)
                self._polyItem.setPolygon(QPolygonF())
                poly = np.array([(p.x(),p.y()) for p in self._points])
                self.roiManager.new(poly)

    def mouse_moved(self):
        x,y = self.mouse.coords
        if self._origin is not None:
            p = QPointF(x,y)
            v = p - self._origin
            vx,vy = abs(v.x()), abs(v.y())
            if vx > vy:
                v.setY(0)
            else:
                v.setX(0)
            pts = self._points + [self._origin + v]
            self._polyItem.setPolygon(QPolygonF(pts))

            if vx >= 0.8 or vy >= 0.8:
                p1 = self._origin + v
                p1 = QPointF(round(p1.x()), round(p1.y()))
                self._points.append(p1)
                self._origin = p1


class ROIDrawTool(GraphicsToolFactory):
    klass = _ROIDrawTool
    roiManager = Instance(ROIManager)


class PenBrushState(object):
    def __init__(self, pen, brush):
        self.pen = pen
        self.brush = brush

    def config_painter(self, painter):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        return painter


class HighlightingGraphicsPolygonItem(QGraphicsPolygonItem):
    _statedict =  {
        'normal'   : PenBrushState(settings.default_roi_pen(False),
                                   settings.default_roi_brush()),
        'highlight': PenBrushState(settings.default_roi_pen(True,color=Qt.red),
                                   settings.default_roi_brush(alpha=0)),
        'selected' : PenBrushState(settings.default_roi_pen(True),
                                   settings.default_roi_brush(alpha=50)),
        }
    def __init__(self, polygon, hover=False):
        super(HighlightingGraphicsPolygonItem, self).__init__(polygon)
        self.setAcceptHoverEvents(True)
        self._hover = hover
        self._state = 'normal'
        self._prevstate = 'normal'
        self.state = 'normal'

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._prevstate = self._state
        self._state = state
        self.update()

    def hoverEnterEvent(self, ev):
        if self._hover:
            self.state = 'highlight'

    def hoverLeaveEvent(self, ev):
        if self._hover:
            self.state = self._prevstate

    def paint(self, painter, option, widget):
        painter = self._statedict[self.state].config_painter(painter)
        painter.drawPolygon(self.polygon())


class _ROIDisplayTool(GraphicsTool):
    name = 'ROI Display'
    roiManager = Instance(ROIManager)
    movable = Bool(False)
    
    def init(self):
        self._polys = {}
        self._polyItems = {}
        self._matrix = QMatrix(0,1,1,0,0,0)
        self.roiManager = self.factory.roiManager
        self.add_new_rois(self.roiManager.rois)

    def destroy(self):
        self._polys = {}
        self._update_display()

    @on_trait_change('roiManager.slicer.slc')
    def view_changed(self):
        self._update_display()

    def add_new_rois(self, rois):
        for roi in rois:
            self._polys[roi] = QPolygonF([QPointF(x,y) for x,y in roi.poly])
        self._update_display()

    @on_trait_change('roiManager:rois[]')
    def rois_changed(self, name, trait, prev, curr):
        prev = set(prev if prev else [])
        curr = set(curr if curr else [])
        newRois = curr - prev
        oldRois = prev - curr

        for roi in oldRois:
            del self._polys[roi]
        self.add_new_rois(newRois)

    @on_trait_change('roiManager:selected[]')
    def roi_selection_changed(self):
        self._update_display()

    def roi_under_mouse(self):
        for roi,polyItem in self._polyItems.iteritems():
            if polyItem.state == 'highlight':
                return (roi, polyItem)
        return (None,None)
   
    def _isvisible(self, rslc):
        slc = self.roiManager.slicer.slc
        return rslc == slc or \
            rslc.is_transposed_view_of(slc)

    def _create_polyitem(self, poly):
        return HighlightingGraphicsPolygonItem(poly,hover=False)

    def _map_poly(self, roi, poly):
        if roi.slc.is_transposed_view_of(self.roiManager.slicer.slc):
            poly = self._matrix.map(poly)
        return poly

    def _update_display(self):
        scene = self.graphics.scene()
        for polyitem in self._polyItems.itervalues():
            scene.removeItem(polyitem)
        self._polyItems = {}
        for roi,poly in self._polys.items():
            if self._isvisible(roi.slc):
                polyitem = self._create_polyitem(self._map_poly(roi, poly))
                if roi in self.roiManager.selected:
                    polyitem.state = 'selected'
                scene.addItem(polyitem)
                self._polyItems[roi] = polyitem


class ROIDisplayTool(GraphicsToolFactory):
    klass = _ROIDisplayTool
    roiManager = Instance(ROIManager)


class _ROIEditTool(_ROIDisplayTool):
    def init(self):
        super(_ROIEditTool, self).init()
        self._selectedROI = None
        self._origin = None
        self._translation = (0,0)
        self._movingPolyItem = None

    def destroy(self):
        super(_ROIEditTool, self).destroy()
        if self._movingPolyItem:
            self.graphics.scene().removeItem(self._movingPolyItem)
            self._movingPolyItem = None

    def _create_polyitem(self, poly):
        return HighlightingGraphicsPolygonItem(poly,hover=True)

    def mouse_pressed(self):
        if self.mouse.buttons.left:
            roi,polyItem = self.roi_under_mouse()
            if roi is not None:
                self._selectedROI = roi
                self._origin = self.mouse.coords
                poly = self._map_poly(roi, self._polys[roi])
                self._movingPolyItem = self.graphics.scene().addPolygon(poly,
                    settings.default_roi_pen(True, Qt.red))
                self._snappingPolyItem = polyItem

    def mouse_moved(self):
        if self.mouse.buttons.left and self._selectedROI:
            x,y = self.mouse.coords
            ox,oy = self._origin
            dx,dy = x-ox,y-oy
            self._movingPolyItem.setPos(dx,dy)
            dx,dy = round(dx),round(dy)
            self._snappingPolyItem.setPos(dx,dy)
            self._translation = (dx,dy)

    def mouse_released(self):
        if self._selectedROI:
            self.graphics.scene().removeItem(self._movingPolyItem)
            self._movingPolyItem = None
            slc,poly = self._selectedROI.slc, self._selectedROI.poly
            
            translation = self._translation
            if self._selectedROI.slc.is_transposed_view_of(self.roiManager.slicer.slc):
                translation = self._translation[::-1]

            poly += np.array(translation)
            self.roiManager.update_roi(self._selectedROI, slc, poly)
        self._origin = None
        self._selectedROI = None
        self._translation = (0,0)


class ROIEditTool(GraphicsToolFactory):
    klass = _ROIEditTool
    roiManager = Instance(ROIManager)
