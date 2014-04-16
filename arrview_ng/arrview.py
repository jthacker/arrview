from PySide.QtCore import Qt, QObject, QEvent as QEV, Signal
from PySide.QtGui import QWidget, QStatusBar, QPixmap, QHBoxLayout, QVBoxLayout, QLabel

from collections import OrderedDict

from . import colormap as cm
from .slicer import Slicer
from .ui.pixmapgraphicsview import PixmapGraphicsView
from .ui.collapsiblepanel import CollapsiblePanel
from .ui.dimeditor import SliceEditor
from .ui.roi import ROIPanel
from .ui.slider import SliderIntegerEditor
from .ui.tools import PanTool, ZoomTool, ArrayValueFromCursorTool, ColorMapTool
from .events import GraphicsViewEventFilter, MouseFilter

class ArrayView(QObject):
    refreshed = Signal()
    tool_added = Signal(object, object)
    tool_removed = Signal(object)

    def __init__(self, ndarray):
        super(ArrayView, self).__init__()
        self.slicer = Slicer(ndarray)
        self.cmap = cm.ColorMapper(cm.jet, cm.LinearNorm(*cm.autoscale(ndarray)))
        self.cmap.updated.connect(self.refreshed.emit)
        self.sliceeditor = SliceEditor(self.slicer.slc)
        self.sliceeditor.slice_changed.connect(self._slice_changed)
        self.roipanel = ROIPanel(self)
        self.tools = OrderedDict()

    def _slice_changed(self, slc):
        self.slicer.slc = slc
        self.refreshed.emit()

    def widget(self):
        graphics = PixmapGraphicsView(self.cmap.ndarray_to_pixmap(self.slicer.view))
        evf = GraphicsViewEventFilter(graphics, self.tools.iteritems())
        self.tool_added.connect(evf.add_tool)
        self.tool_removed.connect(evf.remove_tool)
        graphics.viewport().installEventFilter(evf)
        self.refreshed.connect(lambda: graphics.setPixmap(self.cmap.ndarray_to_pixmap(self.slicer.view)))

        sidebar = QWidget()
        sidebar.setLayout(QVBoxLayout())
        sidebar.layout().addWidget(QLabel('Sidebar'))
        sidebar.layout().addWidget(self.roipanel.widget())
        main = CollapsiblePanel(graphics, sidebar, CollapsiblePanel.East, collapsed=False)
        return CollapsiblePanel(main, self.sliceeditor.widget(), CollapsiblePanel.South, collapsed=True)

    def add_tool(self, tool, filters):
        self.tools[tool] = filters
        self.tool_added.emit(tool, filters)

    def remove_tool(self, tool):
        if self.tools.pop(tool, None):
            self.tool_removed.emit(tool) 


def cursor_info(display_widget, info):
    status = '(%s)' % ','.join('%03d' % i for i in info['slc']) 
    val = info['val']
    if val is not None:
        status += ' %0.2f' % val
    display_widget.setText(status)


def colormap_info(display_widget, cmap):
    fmt = lambda scale: '[%s]' % ','.join('%0.1f' % x for x in scale)
    status = fmt(cmap.scale) + ' ' + fmt(cmap.limits)
    display_widget.setText(status)


def view(arr):
    import sys
    from PySide.QtGui import QApplication, QMainWindow

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    arrview = ArrayView(arr)
    viewWidget = arrview.widget()

    cursor_info_widget = QLabel()
    cursortool = ArrayValueFromCursorTool(arrview.slicer)
    cursortool.status_changed.connect(lambda info: cursor_info(cursor_info_widget, info))

    colormap_info_widget = QLabel()
    colormap_info(colormap_info_widget, arrview.cmap)
    arrview.cmap.updated.connect(lambda: colormap_info(colormap_info_widget, arrview.cmap))

    arrview.add_tool(PanTool(),
            MouseFilter([QEV.MouseMove, QEV.MouseButtonPress, QEV.MouseButtonRelease], buttons=Qt.LeftButton))
    arrview.add_tool(ZoomTool(), [ MouseFilter(QEV.MouseButtonDblClick, buttons=Qt.MiddleButton),
            MouseFilter(QEV.Wheel) ])
    arrview.add_tool(ColorMapTool(arrview), 
            MouseFilter([QEV.MouseMove, QEV.MouseButtonPress, QEV.MouseButtonDblClick], buttons=Qt.RightButton))
    arrview.add_tool(cursortool,MouseFilter(QEV.MouseMove))
    
    win = QMainWindow()
    win.setCentralWidget(viewWidget)
    win.setStatusBar(QStatusBar())
    win.statusBar().addWidget(cursor_info_widget, 0)
    win.statusBar().addWidget(QWidget(), 1)
    win.statusBar().addWidget(colormap_info_widget, 0)
    win.resize(600,600)
    win.show()
    
    app.exec_()


if __name__ == '__main__':
    import numpy as np
    view(np.random.random((128,256,2,4)))
