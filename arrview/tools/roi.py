import logging
import math

import numpy as np

#TODO: Remove this line
from PySide.QtGui import QGraphicsPolygonItem, QImage

from PySide.QtGui import QColor, QGraphicsPixmapItem, QPixmap
from PySide.QtCore import QPoint, QPointF, Qt

from traits.api import Bool, Enum, DelegatesTo, Dict, HasTraits, Instance, Int, List, WeakRef, on_trait_change

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


def _display_color(color, selected):
    alpha = 0.7 if selected else 0.4
    color = QColor(color)
    color.setAlpha(255 * alpha)  # Set alpha to half for display
    return color


class ROIDisplayItem(HasTraits):
    roi = Instance(ROI)
    selected = Bool(False)
    slicer = Instance(Slicer)
    pixmap = Instance(QPixmap, default=None)
    pixmapitem = Instance(QGraphicsPixmapItem, default=None)

    def __init__(self, graphics, slicer, **kwargs):
        self._graphics = graphics
        self.slicer = slicer
        super(ROIDisplayItem, self).__init__(**kwargs)

    def destroy(self):
        self._graphics.scene().removeItem(self.pixmapitem)

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

    @on_trait_change('roi:updated,roi:visible,slicer:slc,selected')
    def _roi_updated(self):
        self._set_pixmap_from_roi(self.roi)

    def _set_pixmap_from_roi(self, roi):
        if roi.visible:
            color = _display_color(roi.color, self.selected)
        else:
            color = QColor(Qt.transparent)
        self.pixmap = _ndarray_to_arraypixmap(roi.mask[self.slicer.slc.view_slice], color.toTuple())
        self.pixmapitem.setPixmap(self.pixmap)
        self.pixmapitem.setZValue(_foreground_roi_z if self.selected else _background_roi_z)


class ROIEdit(HasTraits):
    roi_tool = WeakRef('_ROITool')
    color = Instance(QColor, default=QColor(Qt.black))

    def __init__(self, **traits):
        self._origin = None
        super(ROIEdit, self).__init__(**traits)
        self.paintbrush = PaintBrushItem(radius=self.roi_tool.roi_size)
        self.paintbrush.setZValue(_paintbrush_z)  # Make this item draw on top
        self.paintbrush.hide()
        self.roi_tool.graphics.scene().addItem(self.paintbrush)

    def destroy(self):
        self.roi_tool.graphics.scene().removeItem(self.paintbrush)

    @on_trait_change('roi_tool:roi_size')
    def _roi_size_changed(self):
        self.paintbrush.set_radius(self.roi_tool.roi_size)

    def _paint(self):
        for rdi in self.roi_tool.roi_display_item_dict.itervalues():
            if rdi.selected and rdi.roi.visible:
                self.paintbrush.fill_pixmap(rdi.pixmap,
                                            QPoint(*self._origin),
                                            QPoint(*self.roi_tool.mouse.coords))
                rdi.pixmapitem.setPixmap(rdi.pixmap)

    @on_trait_change('roi_tool:roi_manager.selection[]')
    def _roi_manager_selection_changed(self):
        if not self.roi_tool.mode == 'erase' and len(self.roi_tool.roi_manager.selection) == 1:
            color = _display_color(self.roi_tool.roi_manager.selection[0].roi.color, selected=True)
        else:
            color = QColor(Qt.transparent)
        self.paintbrush.set_color(color)

    @on_trait_change('roi_tool:mouse:entered')
    def mouse_entered(self):
        self.paintbrush.show()

    @on_trait_change('roi_tool:mouse:left')
    def mouse_left(self):
        self.paintbrush.hide()
        self._origin = None

    @on_trait_change('roi_tool:mouse:pressed')
    def mouse_pressed(self):
        if not self.roi_tool.mouse.buttons.left:
            return
        if not (self.roi_tool.mode == 'erase' or self.roi_tool.roi_manager.selection):
            self.roi_tool.roi_manager.new_roi()
        self._origin = self.roi_tool.mouse.coords
        self._paint()

    @on_trait_change('roi_tool:mouse:moved')
    def mouse_moved(self):
        coords = self.roi_tool.mouse.coords
        self.paintbrush.setPos(QPoint(*coords))
        if self._origin:
            self._paint()
            self._origin = coords
            return True

    @on_trait_change('roi_tool:mouse:released')
    def mouse_released(self):
        self._origin = None
        for rdi in self.roi_tool.roi_display_item_dict.itervalues():
            if rdi.selected and rdi.roi.visible:
                mask = _pixmap_to_ndarray(rdi.pixmap)
                self.roi_tool.roi_manager.update_mask(rdi.roi, mask)


class _ROITool(GraphicsTool):
    name = 'ROI'
    roi_size = Int(0)
    mode = DelegatesTo('factory')
    roi_display_item_dict = Dict(ROI, ROIDisplayItem)
    roi_manager = Instance(ROIManager)

    def init(self):
        self.roi_editor = None
        if self.mode in {'draw', 'erase'}:
            self.roi_editor = ROIEdit(roi_tool=self)
        self.roi_manager = self.factory.roi_manager
        self.roi_size = self.factory.factory.roi_size

    def destroy(self):
        for rdi in self.roi_display_item_dict.values():
            rdi.destroy()
        if self.roi_editor:
            self.roi_editor.destroy()
            self.roi_editor = None  # Remove reference to ROIEdit, ensures delete

    @on_trait_change('factory:factory.roi_size')
    def _factory_roi_size_changed(self):
        self.roi_size = self.factory.factory.roi_size

    @on_trait_change('roi_manager')
    def _roi_manager_changed(self):
        self._update_roi_display_item_dict(self.roi_manager.rois)
        self._update_roi_selection(self.roi_manager.selection)

    @on_trait_change('roi_manager:selection[]')
    def _roi_selection_changed(self, obj, name, old, new):
        for rv in old:
            rdi = self.roi_display_item_dict.get(rv.roi)
            if rdi:
                rdi.selected = False
        self._update_roi_selection(new)

    @on_trait_change('roi_manager:rois[]')
    def _rois_changed(self, obj, name, old, new):
        for roi in old:
            rdi = self.roi_display_item_dict.pop(roi)
            rdi.destroy()
        self._update_roi_display_item_dict(new)

    def _update_roi_selection(self, roi_views):
        for rv in roi_views:
            self.roi_display_item_dict[rv.roi].selected = True

    def _update_roi_display_item_dict(self, rois):
        for roi in rois:
            self.roi_display_item_dict[roi] = ROIDisplayItem(self.graphics,
                                                             self.roi_manager.slicer,
                                                             roi=roi)


class ROITool(GraphicsToolFactory):
    klass = _ROITool
    roi_manager = Instance(ROIManager)
    factory = Instance(object)
    mode = Enum('view', 'draw', 'erase')
