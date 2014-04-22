from PySide.QtCore import (Qt, QEvent as QEV, QObject, Signal,
        QAbstractTableModel)
from PySide.QtGui import (QWidget, QVBoxLayout, QCheckBox, QGraphicsPixmapItem, 
        QPixmap, QImage, QColor, QTableView, QHeaderView, QAbstractItemView)

import numpy as np

from .drawing import PaintBrushItem
from ..colormap import ArrayPixmap
from ..events import MouseFilter
from ..slicer import Slicer


def pixmap_to_ndarray(pixmap, alpha_threshold=0):
    img = pixmap.toImage()
    w,h = img.width(),img.height()
    ptr = img.constBits()
    arr = np.frombuffer(ptr, dtype='uint8').reshape(h,w,4)
    out = (arr[...,3] > alpha_threshold).copy()
    return out


def ndarray_to_pixmap(array, color=[0,255,0], alpha=128):
    '''
    Args:
    color -- RGB color tuple. [0,255] for each channel
    alpha -- Alpha channel. [0,255]
    '''
    assert array.ndim == 2, 'Only 2D arrays are supported'
    assert len(color) == 3
    h,w = array.shape
    array = (alpha*array).astype('uint32') << 24 | (color[0]*array).astype('uint32') << 16 | (color[1]*array).astype('uint32') << 8 | (color[2]*array).astype('uint32')
    pixdata = array.flatten()
    img = QImage(pixdata, w, h, QImage.Format_ARGB32)
    pixmap = ArrayPixmap(pixdata, QPixmap.fromImage(img))
    return pixmap


class PixelPainterTool(QObject):
    updated = Signal()

    def __init__(self):
        super(PixelPainterTool, self).__init__()
        self._origin = None

    @property
    def array(self):
        return pixmap_to_ndarray(self.pixmap)

    @array.setter
    def array(self, arr):
        self.pixmap = ndarray_to_pixmap(arr)
        self.pixmapitem.setPixmap(self.pixmap)

    def attach_event(self, graphics):
        self.paintbrush = PaintBrushItem(radius=5, color=QColor(0,255,0,128))
        self.pixmapitem = QGraphicsPixmapItem()
        #TODO: Should not be referencing graphics._pixmap
        self.pixmap = QPixmap(graphics._pixmap.size())
        self.pixmap.fill(Qt.transparent)
        graphics.scene().addItem(self.paintbrush)
        graphics.scene().addItem(self.pixmapitem)

    def detach_event(self, graphics):
        graphics.scene().removeItem(self.paintbrush)
        graphics.scene().removeItem(self.pixmapitem)

    def mouse_press_event(self, ev):
        self._origin = ev.mouse.pos
        self.paintbrush.fill_pixmap(self.pixmap, self._origin)
        self.pixmapitem.setPixmap(self.pixmap)

    def mouse_release_event(self, ev):
        self._origin = None
        self.updated.emit()

    def mouse_move_event(self, ev):
        self.paintbrush.setPos(ev.mouse.pos)
        
        if self._origin:
            self.paintbrush.fill_pixmap(self.pixmap, self._origin)
            self.pixmapitem.setPixmap(self.pixmap)
            self._origin = ev.mouse.pos
            return True


class ROITableModel(QAbstractTableModel):
    roi_name_changed = Signal(object, str)
    header = ['name', 'mean', 'std', 'size']

    def __init__(self, rois):
        super(ROITableModel, self).__init__()
        self.rois = rois

    def rowCount(self, parent):
        return len(self.rois)

    def columnCount(self, parent):
        return 4

    def data(self, index, role):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        return self.rois[index.row()][index.column()+1]

    def setData(self, index, value, role):
        if index.column() != 0:
            return False
        row = self.rois[index.row()]
        row[1] = value
        self.roi_name_changed.emit(row[0], value)
        return True

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ROITableModel.header[col]
        return None

    def flags(self, index):
        flags = super(ROITableModel, self).flags(index)
        if index.column() == 0:
            flags |= Qt.ItemIsEditable
        return flags


class ROIManager(object):
    def __init__(self, rois):
        self.rois = rois 

    def widget(self):
        model = ROITableModel(rois)
        table = QTableView()
        table.setModel(model)
        table.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setResizeMode(3, QHeaderView.ResizeToContents)
        table.verticalHeader().hide()
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        return table

    
class ROIPanel(object):
    def __init__(self, arrview):
        self.arrview = arrview
        self.roi_slicer = Slicer(np.zeros(arrview.slicer.shape, dtype=bool))
        self.arrview.sliceeditor.slice_changed.connect(self._slice_changed)
        self.tool = None
        self.filters = [
            MouseFilter(QEV.MouseMove), 
            MouseFilter([QEV.MouseMove, QEV.MouseButtonPress, QEV.MouseButtonRelease], 
                buttons=Qt.LeftButton)]

    def _state_changed(self, state):
        if state == Qt.Checked:
            self.tool = PixelPainterTool()
            self.tool.updated.connect(self._roi_updated)
            self.arrview.add_tool(self.tool, self.filters)
        elif state == Qt.Unchecked and self.tool is not None:
            self.arrview.remove_tool(self.tool)
            self.tool = None

    def _roi_updated(self):
        self.roi_slicer.view = self.tool.array

    def _slice_changed(self, slc):
        if self.tool is not None:
            self.roi_slicer.slc = slc
            self.tool.array = self.roi_slicer.view

    def widget(self):
        drawbutton = QCheckBox('draw')
        drawbutton.stateChanged.connect(self._state_changed)
        panel = QWidget()
        panel.setLayout(QVBoxLayout())
        panel.layout().addWidget(drawbutton)
        return panel


if __name__ == '__main__':
    import sys
    from PySide.QtGui import QApplication

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    rois = []
    for i in range(10):
        roi = np.random.random((10,10)) > 0.5
        rois.append([roi, 'roi-%i' % i, i*10, i*0.2, i*100])
    roi_manager = ROIManager(rois)
    table = roi_manager.widget()
    table.show()
    sys.exit(app.exec_())

