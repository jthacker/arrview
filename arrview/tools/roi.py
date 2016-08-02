import logging
import math

import numpy as np

#TODO: Remove this line
from PySide.QtGui import QGraphicsPolygonItem, QImage

from PySide.QtGui import QColor, QGraphicsPixmapItem, QPixmap
from PySide.QtCore import QPoint, QPointF, Qt

from traits.api import Bool, Enum, HasTraits, Instance, Int, List, WeakRef, on_trait_change

from arrview import settings
from arrview.colormapper import ArrayPixmap
from arrview.roi import ROI, ROIManager
from arrview.slicer import Slicer
from arrview.tools.base import GraphicsTool, GraphicsToolFactory, MouseState
from arrview.tools.paintbrush import PaintBrushItem


log = logging.getLogger(__name__)

_paintbrush_z = 100
_foreground_roi_z = 11
_background_roi_z = 10


def _pixmap_to_ndarray(pixmap, alpha_threshold=0):
    """Convert a pixmap to a ndarray mask

    Parameters
    ----------
    pixmap : QPixmap
        pixmap to convert to ndarray
    alpha_threshold : float
        convert pixels with alpha > than this value to 1's and values <= threshold to 0's

    Returns
    -------
    A binary mask of the pixmap as a ndarray
    """
    img = pixmap.toImage()
    w, h = img.width(), img.height()
    ptr = img.constBits()
    arr = np.frombuffer(ptr, dtype='uint8').reshape(h, w, 4)
    out = (arr[...,3] > alpha_threshold).copy()
    return out


def _ndarray_to_arraypixmap(array, color=(0, 255, 0, 128)):
    """Convert a binary array to an ArrayPixmap with specified color and alpha level
    Args:
        array -- binary ndarray
        color -- RGBA color tuple. [0, 255] for each channel
    Returns:
        An ArrayPixmap with of the ndarray with constant alpha value
    and color. The input array is colored with *color* and *alpha*
    anywhere it is equal to 1.
    """
    assert array.ndim == 2, 'Only 2D arrays are supported'
    assert len(color) == 4, 'Color should be a 4-tuple'
    h, w = array.shape
    array = array.astype('uint32')
    array =   (color[3] * array) << 24 \
            | (color[0] * array) << 16 \
            | (color[1] * array) << 8 \
            | (color[2] * array)
    pixdata = array.flatten()
    img = QImage(pixdata, w, h, QImage.Format_ARGB32)
    return ArrayPixmap(pixdata, QPixmap.fromImage(img))


def _display_color(color, is_selected):
    alpha = 0.7 if is_selected else 0.4
    color = QColor(color)
    color.setAlpha(255 * alpha)  # Set alpha to half for display
    return color


class ROIDisplayItem(HasTraits):
    roi = Instance(ROI)
    is_selected = Bool
    slicer = Instance(Slicer)
    pixmap = Instance(QPixmap, default=None)
    pixmapitem = Instance(QGraphicsPixmapItem, default=None)

    def __init__(self, graphics, slicer, **kwargs):
        self._graphics = graphics
        self.slicer = slicer
        super(ROIDisplayItem, self).__init__(**kwargs)

    def destroy(self):
        self._graphics.scene().removeItem(self.pixmapitem)

    def _set_pixmap_from_roi(self, roi):
        color = _display_color(roi.color, self.is_selected)
        self.pixmap = _ndarray_to_arraypixmap(roi.mask[self.slicer.slc.view_slice], color.toTuple())
        self.pixmapitem.setPixmap(self.pixmap)
        self.pixmapitem.setZValue(_foreground_roi_z if self.is_selected else _background_roi_z)

    @on_trait_change('roi')
    def _roi_changed(self, obj, name, old, new):
        if old is not None:
            self._graphics.scene().removeItem(self.pixmapitem)
            self.pixmapitem = None
            self.pixmap = None
        if new is not None:
            self.pixmapitem = QGraphicsPixmapItem()
            self._set_pixmap_from_roi(new)
            self._graphics.scene().addItem(self.pixmapitem)

    @on_trait_change('roi:updated,slicer:slc,is_selected')
    def _roi_updated(self, obj, name, old, new):
        self._set_pixmap_from_roi(self.roi)


class ROIEdit(HasTraits):
    mouse = Instance(MouseState)
    roi_manager = Instance(ROIManager)
    roi_display_items = List(ROIDisplayItem)
    color = Instance(QColor, default=QColor(Qt.black))
    radius = Int(0)
    erase = Bool(False)

    def __init__(self, graphics, **traits):
        self._origin = None
        self.graphics = graphics
        self.paintbrush = PaintBrushItem(radius=self.radius, color=QColor(Qt.transparent))
        self.paintbrush.setZValue(_paintbrush_z)  # Make this item draw on top
        self.paintbrush.hide()
        self.graphics.scene().addItem(self.paintbrush)
        super(ROIEdit, self).__init__(**traits)

    def destroy(self):
        self.graphics.scene().removeItem(self.paintbrush)

    def _paint(self):
        for roi_display_item in self.roi_display_items:
            self.paintbrush.fill_pixmap(
                    roi_display_item.pixmap,
                    QPoint(*self._origin),
                    QPoint(*self.mouse.coords))
            roi_display_item.pixmapitem.setPixmap(roi_display_item.pixmap)

    @on_trait_change('roi_manager.selection[]')
    def _roi_manager_selection_changed(self):
        if not self.erase and self.roi_manager.selection:
            color = _display_color(self.roi_manager.selection[-1].roi.color, is_selected=True)
        else:
            color = QColor(Qt.transparent)
        self.paintbrush.set_color(color)

    @on_trait_change('radius')
    def _radius_changed(self):
        self.paintbrush.set_radius(self.radius)

    @on_trait_change('mouse:entered')
    def mouse_entered(self):
        self.paintbrush.show()

    @on_trait_change('mouse:left')
    def mouse_left(self):
        self.paintbrush.hide()
        self._origin = None

    @on_trait_change('mouse:pressed')
    def mouse_pressed(self):
        if not (self.erase or self.roi_manager.selection):
            self.roi_manager.new_roi()
        self._origin = self.mouse.coords
        self._paint()

    @on_trait_change('mouse:moved')
    def mouse_moved(self):
        coords = self.mouse.coords
        self.paintbrush.setPos(QPoint(*coords))
        if self._origin:
            self._paint()
            self._origin = coords
            return True

    @on_trait_change('mouse:released')
    def mouse_released(self):
        self._origin = None
        for roi_display_item in self.roi_display_items:
            mask = _pixmap_to_ndarray(roi_display_item.pixmap)
            self.roi_manager.update_mask(roi_display_item.roi, mask)


class _ROITool(GraphicsTool):
    name = 'ROI'
    roi_manager = Instance(ROIManager)

    def init(self):
        self.roi_manager = self.factory.roi_manager
        self._roi_display_item_map = {}
        self._update_roi_display_items(self.roi_manager.rois)
        self.roiedit = None
        if self.factory.mode in {'draw', 'erase'}:
            self.roiedit = ROIEdit(graphics=self.graphics,
                                   mouse=self.mouse,
                                   roi_manager=self.roi_manager,
                                   erase=self.factory.mode == 'erase',
                                   radius=self.factory.factory.roi_size)
            self._update_edit_views()

    @on_trait_change('factory:factory:roi_size')
    def _roi_size_changed(self, obj, name, old, new):
        if self.roiedit:
            self.roiedit.radius = new

    def destroy(self):
        for roi_display_item in self._roi_display_item_map.values():
            roi_display_item.destroy()
        if self.roiedit:
            self.roiedit.destroy()

    def _update_roi_display_items(self, rois):
        for roi in rois:
            roi_display_item = ROIDisplayItem(self.graphics,
                                              self.roi_manager.slicer,
                                              roi=roi)
            self._roi_display_item_map[roi] = roi_display_item

    def _update_edit_views(self):
        if self.roiedit:
            self.roiedit.roi_display_items = [
                    self._roi_display_item_map[rv.roi] for rv in self.roi_manager.selection]

    @on_trait_change('roi_manager:selection[]')
    def _roi_selection_changed(self, obj, name, old, new):
        self._update_edit_views()
        for rv in old:
            rdt = self._roi_display_item_map.get(rv.roi)
            if rdt:
                rdt.is_selected = False
        for rv in new:
            self._roi_display_item_map[rv.roi].is_selected = True

    @on_trait_change('roi_manager:rois[]')
    def _rois_changed(self, obj, name, old, new):
        for roi in old:
            roi_display_item = self._roi_display_item_map[roi]
            roi_display_item.destroy()
            del self._roi_display_item_map[roi]
        self._update_roi_display_items(new)


class ROITool(GraphicsToolFactory):
    klass = _ROITool
    roi_manager = Instance(ROIManager)
    factory = Instance(object)
    mode = Enum('view', 'draw', 'erase')
