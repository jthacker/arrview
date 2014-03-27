from PySide.QtCore import Qt, QObject, QEvent as QEV
from PySide.QtGui import QWidget

from . import colormap as cmap
from .slicer import Slicer
from .ui.pixmapgraphicsview import PixmapGraphicsView
from .ui.tools import PanTool, ZoomTool
from .events import GraphicsViewEventFilter, MouseFilter

class ArrayView(object):
    def __init__(self, ndarray):
        self.slicer = Slicer(ndarray)
        self.cmap = cmap.jet
        self.norm = cmap.LinearNorm(*cmap.autoscale(ndarray))

    def widget(self):
        pixmap = cmap.ndarray_to_pixmap(self.slicer.view, self.cmap, self.norm)
        return PixmapGraphicsView(pixmap)


def main(arr):
    import sys
    from PySide.QtGui import (QApplication, QMainWindow)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
  
    view = ArrayView(arr).widget()
    tools = {
        PanTool(): 
            [ MouseFilter([QEV.MouseMove, QEV.MouseButtonPress], buttons=Qt.LeftButton),
              MouseFilter(QEV.MouseButtonRelease) ],
        ZoomTool():
            [ MouseFilter(QEV.MouseButtonDblClick, buttons=Qt.MiddleButton),
              MouseFilter(QEV.Wheel) ]
        }

    view.viewport().installEventFilter(GraphicsViewEventFilter(view, tools))
    
    win = QMainWindow()
    win.setCentralWidget(view)
    win.resize(600,600)
    win.show()
    app.exec_()


if __name__ == '__main__':
    import numpy as np
    main(np.random.random((32,64,128)))
