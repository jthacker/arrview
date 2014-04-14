from PySide.QtCore import Qt, QObject, QEvent as QEV
from PySide.QtGui import QWidget, QStatusBar, QPixmap

from . import colormap as cm
from .slicer import Slicer
from .ui.pixmapgraphicsview import PixmapGraphicsView
from .ui.collapsiblepanel import CollapsiblePanel
from .ui.tools import PanTool, ZoomTool, ArrayValueFromCursorTool, ColorMapTool
from .events import GraphicsViewEventFilter, MouseFilter

class ArrayView(object):
    def __init__(self, ndarray):
        self.slicer = Slicer(ndarray)
        self.cmap = cm.ColorMapper(cm.jet, cm.LinearNorm(*cm.autoscale(ndarray)))
        self.cmap.updated.connect(self.refresh)
        self.graphics = None
        self.refresh()

    def refresh(self):
        pixmap = self.cmap.ndarray_to_pixmap(self.slicer.view)
        if self.graphics is None:
            self.graphics = PixmapGraphicsView(pixmap)
        else:
            self.graphics.setPixmap(pixmap)

    def widget(self):
        return self.graphics


def view(arr):
    import sys
    from PySide.QtGui import (QApplication, QMainWindow, QWidget, QPushButton,
            QHBoxLayout, QLabel)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
 
    arrview = ArrayView(arr)
    viewWidget = arrview.widget()
   
    sidebar = QWidget()
    sidebar.setLayout(QHBoxLayout())
    sidebar.layout().addWidget(QLabel('Sidebar'))

    main = CollapsiblePanel(viewWidget, sidebar, CollapsiblePanel.East, collapsed=True)

    dim = QWidget()
    dim.setLayout(QHBoxLayout())
    dim.layout().addWidget(QPushButton('Push Me'))
    dim.layout().addWidget(QPushButton('No, push me!'))

    panel = CollapsiblePanel(main, dim, CollapsiblePanel.South, collapsed=True)

    win = QMainWindow()
    win.setCentralWidget(panel)
    win.setStatusBar(QStatusBar(win))
    win.resize(600,600)
    win.show()
    panel.collapse() 
    cursortool = ArrayValueFromCursorTool(arrview.slicer)

    def cursor_info(msg):
        status = '(%s)' % ','.join('%03d' % i for i in msg['slc']) 
        val = msg['val']
        if val is not None:
            status += ' %0.2f' % val
        win.statusBar().showMessage(status)

    cursortool.status.connect(cursor_info)

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

    viewWidget.viewport().installEventFilter(GraphicsViewEventFilter(viewWidget, tools))
    
    app.exec_()


if __name__ == '__main__':
    import numpy as np
    view(np.random.random((128,256,128)))
