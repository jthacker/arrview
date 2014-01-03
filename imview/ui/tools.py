from PySide.QtGui import QGraphicsView, QPolygonF
from PySide.QtCore import QPointF

from collections import namedtuple
from traits.api import (HasTraits, Instance, Float, Str,
        Int, Tuple, Event, Property, on_trait_change)

import numpy as np
import math

from .. import settings
from ..util import rep, clamp
from ..roi import ROI, ROIManager
from ..slicer import Slicer
from ..colormapper import ColorMapper


class MouseButtons(object):
    def __init__(self, left=False, middle=False, right=False):
        self.left = left
        self.middle = middle
        self.right = right

    def all(self):
        return self.left and self.middle and self.right

    def none(self):
        return not (self.left or self.middle or self.right)

    def __repr__(self):
        return rep(self, ['left','middle','right'])


class MouseState(HasTraits):
    coords = Tuple
    screenCoords = Tuple
    delta = Int
    buttons = Instance(MouseButtons, MouseButtons)

    wheeled = Event
    pressed = Event
    released = Event
    moved = Event
    doubleclicked = Event

    def __repr__(self): 
        return rep(self, ['coords','screenCoords', 'delta', 'buttons'])


class GraphicsTool(HasTraits):
    name = Str('DEFAULT_NAME')
    mouse = Instance(MouseState)
    graphics = None

    def init(self, graphics, mouse):
        self.graphics = graphics
        self.mouse = mouse
        mouse.on_trait_event(self.mouse_moved, 'moved')
        mouse.on_trait_event(self.mouse_pressed, 'pressed')
        mouse.on_trait_event(self.mouse_wheeled, 'wheeled')
        mouse.on_trait_event(self.mouse_released, 'released')
        mouse.on_trait_event(self.mouse_double_clicked, 'doubleclicked')
        self._init()

    def _init(self):
        pass

    def destroy(self):
        self._destroy()

    def _destroy(self):
        pass

    def mouse_pressed(self):
        pass

    def mouse_moved(self):
        pass

    def mouse_wheeled(self):
        pass

    def mouse_released(self):
        pass

    def mouse_double_clicked(self):
        pass

    def __repr__(self):
        return rep(self, ['name'])


def _close_polygon(start, end):
    '''Given a start and end point, returns a set of integer points
    that will close the polygon with a straight line from start to
    end'''
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


class ROIDrawTool(GraphicsTool):
    name = 'Draw ROI'
    slicer = Instance(Slicer)
    roiManager = Instance(ROIManager)

    def _init(self):
        self._initialPoint = None
        self._points = []
        self._polyItem = self.graphics.scene().addPolygon(QPolygonF(),
                settings.default_roi_pen(), settings.default_roi_brush())

    def mouse_pressed(self):
        if self.mouse.buttons.left:
            x,y = self.mouse.coords
            if self._initialPoint is None:
                self._initialPoint = QPointF(round(x),round(y))
                self._points = [self._initialPoint]
            else:
                self._initialPoint = None
                closedPts = _close_polygon(self._points[-1], self._points[0])
                self._points.extend(closedPts)
                self._polyItem.setPolygon(QPolygonF(self._points))
                roi = ROI(name='new roi')
                roi.set_poly(self.slicer, 
                    np.array([(p.y(),p.x()) for p in self._points]))
                self.roiManager.add(roi)
                self._polyItem.setPolygon(QPolygonF())

    def mouse_moved(self):
        x,y = self.mouse.coords
        if self._initialPoint is not None:
            p = QPointF(x,y)
            v = p - self._initialPoint
            vx,vy = abs(v.x()), abs(v.y())
            if vx > vy:
                v.setY(0)
            else:
                v.setX(0)
            pts = self._points + [self._initialPoint + v]
            self._polyItem.setPolygon(QPolygonF(pts))

            if vx >= 0.8 or vy >= 0.8:
                p1 = self._initialPoint + v
                p1 = QPointF(round(p1.x()), round(p1.y()))
                self._points.append(p1)
                self._initialPoint = p1


class ROIDisplayTool(GraphicsTool):
    name = 'ROI Display'
    slicer = Instance(Slicer)
    roiManager = Instance(ROIManager)

    def _init(self):
        self._polys = {}
        self._polyitems = []

    @on_trait_change('slicer:slc')
    def view_changed(self):
        self._update_display()

    @on_trait_change('roiManager:rois[]')
    def rois_changed(self, name, trait, prev, curr):
        prev = set(prev if prev else [])
        curr = set(curr if curr else [])
        newRois = curr - prev
        oldRois = prev - curr
        for roi in newRois:
            x,y,slc,arr = roi.poly
            self._polys[roi] = QPolygonF([QPointF(a[1],a[0]) for a in arr])

        for roi in oldRois:
            del self._polys[roi]

        self._update_display()

    def _isvisible(self, roi):
        viewslc = self.slicer.slc
        roislc = roi.poly.slc
        return viewslc == roislc

    def _update_display(self):
        for polyitem in self._polyitems:
            self.graphics.scene().removeItem(polyitem)
        self._polyitems = []

        for roislice,poly in self._polys.items(): 
            if self._isvisible(roislice):
                polyitem = self.graphics.scene().addPolygon(poly,
                    settings.default_roi_pen(), settings.default_roi_brush())
                self._polyitems.append(polyitem)



class CursorInfoTool(GraphicsTool):
    name = 'CursorInfo'
    slicer = Instance(Slicer)
    msg = Str
    
    def mouse_moved(self):
        self.update()

    def update(self):
        x,y = self.mouse.coords if self.mouse else (0,0)
        slc = list(self.slicer.slc)
        xDim,yDim = self.slicer.xdim,self.slicer.ydim
        slc[xDim], slc[yDim] = x,y
        
        view = self.slicer.view
        shape = view.shape
        xMax,yMax = shape[1],shape[0]

        msg = '(%s) ' % ','.join(['%03d' % p for p in slc])
        if 0 <= x < xMax and 0 <= y < yMax:
            msg += "%0.2f" % view[y,x]
        else:
            msg += "  "
        self.msg = msg


class PanTool(GraphicsTool):
    name = 'Pan'

    def _init(self):
        self.graphics.setDragMode(QGraphicsView.ScrollHandDrag)

    def _destroy(self):
        self.graphics.setDragMode(QGraphicsView.NoDrag)


class ZoomTool(GraphicsTool):
    name = 'Zoom'

    def _init(self):
        self.graphics.setTransformationAnchor(
                QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.currentScale = 1

    def mouse_wheeled(self):
        zoomIn = self.mouse.delta < 0
        s = 1.2 if zoomIn else 1/1.2
        lessThanMax = zoomIn and self.currentScale < 20
        greaterThanMin = not zoomIn and self.currentScale > 0.1
        if lessThanMax or greaterThanMin:
            self.graphics.scale(s,s)
            self.currentScale *= s 


class ColorMapTool(GraphicsTool):
    name = 'ColorMapTool'
    colorMapper = Instance(ColorMapper)
    slicer = Instance(Slicer)
    msg = Property(depends_on='colorMapper.norm.+')
    
    def _init(self):
        self.origin = None

    def mouse_pressed(self):
        if self.mouse.buttons.middle:
            self.origin = self.mouse.screenCoords
            norm = self.colorMapper.norm
            vmin,vmax = norm.vmin,norm.vmax
            self.iwidth = vmax - vmin
            self.icenter = (vmax - vmin) / 2.0 + vmin

    def mouse_moved(self):
        if self.mouse.buttons.middle and self.origin:
            origin = self.origin
            coords = self.mouse.screenCoords
            norm = self.colorMapper.norm
            low,high = norm.low,norm.high

            a = 0.01 * (high - low)
            center = self.icenter + a * (coords[0] - origin[0])
            halfwidth = (self.iwidth + -a * (coords[1] - origin[1])) / 2.0
            norm.vmin = clamp(center - halfwidth, low, high)
            norm.vmax = clamp(center + halfwidth, low, high)

    def mouse_double_clicked(self):
        if self.mouse.buttons.middle:
            self.colorMapper.norm.set_scale(self.slicer.view)

    def _get_msg(self):
        norm = self.colorMapper.norm
        width = norm.vmax - norm.vmin
        center = width / 2.0 + norm.vmin
        return 'width:%0.2f center:%0.2f' % (width, center)
