from traits.api import (HasTraits, Instance, Property, cached_property,
        Range, Color, Bool, Button)
from traitsui.api import View, Group, Item

from .slicer import Slicer
from .colormapper import ColorMapper

from .ui.tools import ToolSet, PanTool, ZoomTool

import math

from PySide.QtCore import Qt, Signal, QRectF, Qt, QPointF
from PySide.QtGui import (QGraphicsView, QGraphicsPixmapItem,
        QGraphicsScene, QBrush, QPen, QPainter, QPixmap, QColor,
        QGraphicsItem, QImage)

from traits.api import (Instance, HasTraits, Int, WeakRef,
        on_trait_change, List)
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory

from .ui.tools import ToolSet, MouseState, MouseButtons, GraphicsTool, GraphicsToolFactory

import skimage as ski
import skimage.draw

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
        self.roiLayer = QGraphicsPixmapItem()
        self.setScene(QGraphicsScene())
        self.scene().addItem(self.pixmapItem)
        self.scene().addItem(self.roiLayer)
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

    def keyPressEvent(self, ev):
        pass

    def setPixmap(self, pixmap):
        '''Set the array to be viewed.
        Args:
        array (numpy array): the array to be viewed

        This will remove the previous array but maintain the previous scaling 
        as well as the panned position.
        '''
        self.pixmap = pixmap
        self.pixmapItem.setPixmap(self.pixmap)
        
        self.roiPixmap = QPixmap(pixmap.size())
        self.roiPixmap.fill(Qt.transparent)
        self.roiLayer.setPixmap(self.roiPixmap)

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
        self.control.destroyed.connect(self._control_destroyed)
        self._tools = []
        self.toolSet = self.factory.toolSet

    def _control_destroyed(self):
        self._tools = []

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


class PaintBrushItem(QGraphicsItem):
    def __init__(self):
        super(PaintBrushItem, self).__init__()
        self._color = Qt.black
        self._connect_points = True
        self._points = []
        self.setRadius(0)
       
    def setConnectPoints(self, connect):
        self._connect_points = connect

    def setColor(self, color):
        self._color = color
        self._update_cursor()

    def setRadius(self, r):
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

    def snapPos(self, x, y):
        f = lambda a: int(math.floor(a))
        return f(x),f(y)

    def setPos(self, x, y):
        super(PaintBrushItem, self).setPos(*self.snapPos(x,y))
       
    def paint(self, p, option, widget):
        r = self._radius
        self._paint_cursor(p)
        p.drawEllipse(-r,-r,2*r+1,2*r+1)

    def boundingRect(self):
        r = self._radius
        return QRectF(0,0,2*r+1,2*r+1)

    def fill_pixmap(self, pixmap, origin):
        ox,oy = self.snapPos(*origin)
        pos = self.pos()
        cx,cy = self.snapPos(pos.x(), pos.y())

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


class _PixelPainterTool(GraphicsTool):
    def init(self):
        self.factory.params.on_trait_change(self.color_changed, 'alpha')
        self.factory.params.on_trait_change(self.color_changed, 'color')
        self.factory.params.on_trait_change(self.size_changed, 'size')
        self.factory.params.on_trait_change(self.erase_changed, 'erase')
        self.factory.params.on_trait_change(self.connect_points_changed, 'connectPoints')
        self.factory.params.on_trait_change(self.findROI, 'findROI')
        self.factory.params.on_trait_change(self.debug, 'debug')
        self.paintbrush = PaintBrushItem()
        self.graphics.scene().addItem(self.paintbrush)
        self._origin = None
        self.color_changed()
        self.size_changed()
        self.erase_changed()

    def debug(self):
        import ipdb; ipdb.set_trace()

    def findROI(self):
        self.graphics.fitInView(self.graphics.roiLayer, Qt.KeepAspectRatio)

    def connect_points_changed(self):
        self.paintbrush.setConnectPoints(self.factory.params.connectPoints)

    def color_changed(self):
        color = self.factory.params.color
        alpha = self.factory.params.alpha
        pix = self.graphics.roiPixmap

        mask = pix.createMaskFromColor(Qt.transparent)
        color.setAlpha(alpha)

        p = QPainter(pix)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.setPen(color)
        p.drawPixmap(pix.rect(), mask, mask.rect())
        p.end()

        self._color = color
        self.graphics.roiLayer.setPixmap(pix)
        self.paintbrush.setColor(color)

    def size_changed(self):
        self.paintbrush.setRadius(self.factory.params.size)

    def erase_changed(self):
        self.paintbrush.setColor(Qt.transparent if self.factory.params.erase else self._color)

    def mouse_pressed(self):
        self._origin = self.mouse.coords
        self.mouse_moved()

    def pixmap_to_ndarray(self, pixmap):
        img = pixmap.toImage()
        w,h = img.width(),img.height()
        ptr = img.constBits()
        return np.frombuffer(ptr, dtype='uint8').reshape(w,h,4)
    
    def mouse_moved(self):
        pos = self.mouse.coords
        self.paintbrush.setPos(*pos)

        if self.mouse.buttons.left:
            self.paintbrush.fill_pixmap(self.graphics.roiPixmap, self._origin)
            self.graphics.roiLayer.setPixmap(self.graphics.roiPixmap)
            self._origin = pos
            pix = self.graphics.roiPixmap
            x = self.pixmap_to_ndarray(pix)[:,:,3] > 0
            print('pixels:%d' % (x.sum()))

    def mouse_released(self):
        self._origin = None


class Params(HasTraits):
    erase = Bool(False)
    size = Range(low=0, high=64, value=1)
    alpha = Range(low=1, high=255, value=200)
    color = Color((241,0,0))
    connectPoints = Bool(True)
    findROI = Button('Show ROI')
    debug = Button('Debug')

    view = View('color', 'alpha', 'size',
            'erase','connectPoints','findROI',
            'debug')


class PixelPainterTool(GraphicsToolFactory):
    klass = _PixelPainterTool
    params = Instance(Params)


class DrawViewer(HasTraits):
    slicer = Instance(Slicer)
    pixmap = Property(depends_on='slicer.view')
    cmap = Instance(ColorMapper)
    params = Instance(Params, Params)

    def __init__(self, slicer):
        self.slicer = slicer
        self.cmap = ColorMapper(slicer=slicer)
        self.toolset = ToolSet(factories=[
            PanTool(button='right'),
            ZoomTool(),
            PixelPainterTool(params=self.params)])

    def default_traits_view(self):
        return View(
                Group(
                    Item('pixmap', 
                        editor=PixmapEditor(toolSet=self.toolset), 
                        show_label=False),
                    Item('params', show_label=False, style='custom')),
            resizable=True)

    @cached_property
    def _get_pixmap(self):
        return self.cmap.array_to_pixmap(self.slicer.view)


if __name__ == '__main__':
    import numpy as np

    arr = np.random.random((512,256))
    view = DrawViewer(slicer=Slicer(arr=arr))
    view.configure_traits()
