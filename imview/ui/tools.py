from PySide.QtGui import (QGraphicsView, QPolygonF, QBrush, 
        QColor, QMatrix, QGraphicsItem, QGraphicsPolygonItem)
from PySide.QtCore import QPointF, Qt

from collections import namedtuple
from traits.api import (HasTraits, Instance, Float, Str, WeakRef,
    Any, Int, Tuple, List, Bool, Event, Enum,
    Property, Callable, on_trait_change)

import numpy as np
import math
import weakref
import datetime

from .. import settings
from ..util import rep, clamp
from ..roi import ROI, ROIManager
from ..slicer import Slicer
from ..colormapper import ColorMapper


class MouseButtons(object):
    def __init__(self, left=False, middle=False, right=False):
        self._left = left
        self._middle = middle
        self._right = right

    @property 
    def left(self):
        return self._left and not(self._right or self._middle)

    @property
    def right(self):
        return self._right and not(self._left or self._middle)

    @property
    def middle(self):
        return self._middle and not(self._left or self._right)

    def all(self):
        return self._left and self._middle and self._right

    def none(self):
        return not (self._left or self._middle or self._right)

    def __repr__(self):
        return rep(self, ['left','middle','right'])


class MouseState(HasTraits):
    coords = Tuple(Float, Float, default=(0,0))
    screenCoords = Tuple(Float, Float, default=(0,0))
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
    '''Only use dynamic notifications in the _init method when setting
    up listeners. This has to be done because the class isn't fully
    initialized until it is passed to the graphics view and init is called.
    This can lead to null pointer exceptions.'''

    name = Str('DEFAULT_NAME')
    mouse = Instance(MouseState)
    factory = WeakRef('GraphicsToolFactory')

    def __init__(self, factory, graphics, mouse):
        super(GraphicsTool, self).__init__(mouse=mouse, factory=factory)
        self.graphics = weakref.proxy(graphics)
        mouse.on_trait_event(self.mouse_moved, 'moved')
        mouse.on_trait_event(self.mouse_pressed, 'pressed')
        mouse.on_trait_event(self.mouse_wheeled, 'wheeled')
        mouse.on_trait_event(self.mouse_released, 'released')
        mouse.on_trait_event(self.mouse_double_clicked, 'doubleclicked')
        self.init()

    def init(self):
        pass

    def destroy(self):
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

    def __del__(self):
        print(self)


class GraphicsToolFactory(HasTraits):
    klass = Instance(GraphicsTool)

    def init_tool(self, graphics, mouse):
        return self.klass(factory=self, graphics=graphics, mouse=mouse)


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
                poly = np.array([(p.y(),p.x()) for p in self._points])
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
                                   settings.default_roi_brush()),
        'selected' : PenBrushState(settings.default_roi_pen(True),
                                   settings.default_roi_brush(alpha=100)),
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
        self.roiManager = self.factory.roiManager
        self._matrix = QMatrix(0,1,1,0,0,0)

    def destroy(self):
        self._polys = {}
        self._update_display()

    @on_trait_change('roiManager.slicer.slc')
    def view_changed(self):
        self._update_display()

    @on_trait_change('roiManager')
    def roimanager_updated(self):
        self.add_new_rois(self.roiManager.rois)

    def add_new_rois(self, rois):
        for roi in rois:
            self._polys[roi] = QPolygonF([QPointF(y,x) for x,y in roi.poly])
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
            if polyItem.isUnderMouse():
                return (roi, polyItem)
        return (None,None)
   
    def _isvisible(self, rslc):
        slc = self.roiManager.slicer.slc
        return rslc == slc or \
            rslc.is_transposed_view_of(slc)

    def _create_polyitem(self, poly):
        return HighlightingGraphicsPolygonItem(poly,hover=False)

    def _update_display(self):
        scene = self.graphics.scene()
        for polyitem in self._polyItems.itervalues():
            scene.removeItem(polyitem)
        self._polyItems = {}
        for roi,poly in self._polys.items():
            if self._isvisible(roi.slc):
                if roi.slc.is_transposed_view_of(self.roiManager.slicer.slc):
                    poly = self._matrix.map(poly)
                polyitem = self._create_polyitem(poly)
                if roi in self.roiManager.selected:
                    polyitem.state = 'selected'
                scene.addItem(polyitem)
                self._polyItems[roi] = polyitem


class ROIDisplayTool(GraphicsToolFactory):
    klass = _ROIDisplayTool
    roiManager = Instance(ROIManager)

class _ROISelectionTool(GraphicsTool):
    def mouse_pressed(self):
        if self.mouse.buttons.left:
            roi,poly = self.roi_under_mouse()
            if roi is not None:
                self.roiManager.selected += roi


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
                poly = self._polys[roi]
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
            # Translation is used on the polygon stored in the roi
            # which has transposed axes relative to the graphics
            self._translation = (dy,dx)
        elif self.mouse.buttons.none:
            roi,polyItem = self.roi_under_mouse()

    def mouse_released(self):
        if self._selectedROI:
            self.graphics.scene().removeItem(self._movingPolyItem)
            self._movingPolyItem = None
            slc,poly = self._selectedROI.slc, self._selectedROI.poly
            poly += np.array(self._translation)
            self.roiManager.update_roi(self._selectedROI, slc, poly)
        self._origin = None
        self._selectedROI = None
        self._translation = (0,0)


class ROIEditTool(GraphicsToolFactory):
    klass = _ROIEditTool
    roiManager = Instance(ROIManager)


class _CursorInfoTool(GraphicsTool):
    name = 'CursorInfo'
    slicer = Instance(Slicer)
    callback = Callable

    def init(self):
        self.slicer = self.factory.slicer
        self.callback = self.factory.callback

    def mouse_moved(self):
        self.update()

    @on_trait_change('slicer:view')
    def update(self):
        x,y = self.mouse.coords
        slc = list(self.slicer.slc)
        xDim,yDim = self.slicer.slc.viewdims
        slc[xDim], slc[yDim] = x,y
        
        view = self.slicer.view
        shape = view.shape
        xMax,yMax = shape[1],shape[0]

        msg = '(%s) ' % ','.join(['%03d' % p for p in slc])
        if 0 <= x < xMax and 0 <= y < yMax:
            msg += "%0.2f" % view[y,x]
        else:
            msg += "  "
        self.callback(msg)


class CursorInfoTool(GraphicsToolFactory):
    klass = _CursorInfoTool
    slicer = Instance(Slicer)
    callback = Callable


class _PanTool(GraphicsTool):
    name = 'Pan'

    def init(self):
        self.origin = None
        self.prevCursor = None
        button = self.factory.button
        self.buttonTest = lambda mouse: getattr(mouse.buttons, button)

    def mouse_pressed(self):
        if self.buttonTest(self.mouse):
            self.origin = self.mouse.screenCoords
            self.prevCursor = self.graphics.cursor()
            self.graphics.setCursor(Qt.ClosedHandCursor)
    
    def mouse_moved(self):
        if self.buttonTest(self.mouse) and self.origin:
            vBar = self.graphics.verticalScrollBar()
            hBar = self.graphics.horizontalScrollBar();
            ox,oy = self.origin
            x,y = self.mouse.screenCoords
            dx,dy = x-ox,y-oy
            hBar.setValue(hBar.value() - dx)
            vBar.setValue(vBar.value() - dy)
            self.origin = (x,y)

    def mouse_released(self):
        if self.origin:
            self.graphics.setCursor(self.prevCursor)
            self.origin = None


class PanTool(GraphicsToolFactory):
    klass = _PanTool
    button = Enum('left','middle','right')


class _ZoomTool(GraphicsTool):
    name = 'Zoom'

    def init(self):
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

    def mouse_double_clicked(self):
        if self.mouse.buttons.middle:
            s = 1.0 / self.currentScale
            self.graphics.scale(s,s)
            self.currentScale = 1


class ZoomTool(GraphicsToolFactory):
    klass = _ZoomTool


class _ColorMapTool(GraphicsTool):
    name = 'ColorMapTool'
    colorMapper = Instance(ColorMapper)
    slicer = Instance(Slicer)
    callback = Callable
    
    def init(self):
        self.origin = None
        self.slicer = self.factory.slicer
        self.callback = self.factory.callback
        self.colorMapper = self.factory.colorMapper

    def mouse_pressed(self):
        if self.mouse.buttons.right:
            self.origin = self.mouse.screenCoords
            norm = self.colorMapper.norm
            vmin,vmax = norm.vmin,norm.vmax
            self.iwidth = vmax - vmin
            self.icenter = (vmax - vmin) / 2.0 + vmin

    def mouse_moved(self):
        if self.mouse.buttons.right and self.origin:
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
        if self.mouse.buttons.right:
            self.colorMapper.norm.set_scale(self.slicer.view)

    @on_trait_change('colorMapper.norm.+')
    def update_callback(self):
        norm = self.colorMapper.norm
        self.callback('cmap: [%0.2f, %0.2f]' % (norm.vmin, norm.vmax))


class ColorMapTool(GraphicsToolFactory):
    klass = _ColorMapTool
    slicer = Instance(Slicer)
    colorMapper = Instance(ColorMapper)
    callback = Callable


class ToolSet(HasTraits):
    factories = List(GraphicsToolFactory)

    def __init__(self, **traits):
        super(ToolSet, self).__init__(**traits)
        self._tools = []

    @property
    def tools(self):
        return self._tools

    def init_tools(self, graphics, mouse):
        return [t.init_tool(graphics, mouse) for t in self.factories]

