from PySide.QtCore import Qt, QObject, QEvent as QEV
from PySide.QtGui import QWidget, QStatusBar, QPixmap, QHBoxLayout, QVBoxLayout, QLabel

from . import colormap as cm
from .slicer import Slicer
from .ui.pixmapgraphicsview import PixmapGraphicsView
from .ui.collapsiblepanel import CollapsiblePanel
from .ui.dimeditor import SliceEditor
from .ui.slider import SliderIntegerEditor
from .ui.tools import PanTool, ZoomTool, ArrayValueFromCursorTool, ColorMapTool
from .events import GraphicsViewEventFilter, MouseFilter

class ArrayView(object):
    def __init__(self, ndarray):
        self.slicer = Slicer(ndarray)
        self.cmap = cm.ColorMapper(cm.jet, cm.LinearNorm(*cm.autoscale(ndarray)))
        self.cmap.updated.connect(self.refresh)
        self.sliceeditor = SliceEditor(self.slicer.slc)
        self.sliceeditor.slice_changed.connect(self._slice_changed)
        self.graphics = None
        self.refresh()

    def _slice_changed(self, slc):
        self.slicer.slc = slc
        self.refresh()

    def refresh(self):
        pixmap = self.cmap.ndarray_to_pixmap(self.slicer.view)
        if self.graphics is None:
            self.graphics = PixmapGraphicsView(pixmap)
        else:
            self.graphics.setPixmap(pixmap)

    def widget(self):
        sidebar = QWidget()
        sidebar.setLayout(QHBoxLayout())
        sidebar.layout().addWidget(QLabel('Sidebar'))

        main = CollapsiblePanel(self.graphics, sidebar, CollapsiblePanel.East, collapsed=True)

        return CollapsiblePanel(main, self.sliceeditor.widget, CollapsiblePanel.South, collapsed=True)

    def set_tools(self, tools):
        self.graphics.viewport().installEventFilter(GraphicsViewEventFilter(self.graphics, tools))


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

    win = QMainWindow()
    win.setCentralWidget(viewWidget)
    win.setStatusBar(QStatusBar(win))
    win.statusBar().addWidget(cursor_info_widget, 0)
    win.statusBar().addWidget(QWidget(), 1)
    win.statusBar().addWidget(colormap_info_widget, 0)
    win.resize(600,600)
    

    tools = {
        PanTool(): 
            [ MouseFilter([QEV.MouseMove, QEV.MouseButtonPress], buttons=Qt.LeftButton),
              MouseFilter(QEV.MouseButtonRelease) ],
        ZoomTool():
            [ MouseFilter(QEV.MouseButtonDblClick, buttons=Qt.MiddleButton),
              MouseFilter(QEV.Wheel) ],
        cursortool:
            [ MouseFilter(QEV.MouseMove) ],
        ColorMapTool(arrview):
            [ MouseFilter([QEV.MouseMove, QEV.MouseButtonPress, QEV.MouseButtonDblClick], buttons=Qt.RightButton)],
        }
    arrview.set_tools(tools)
    
    win.show()
    app.exec_()


if __name__ == '__main__':
    import numpy as np
    view(np.random.random((32,10,128,2,4)))
