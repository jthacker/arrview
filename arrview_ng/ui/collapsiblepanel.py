from PySide.QtCore import Qt, QObject, Signal
from PySide.QtGui import QWidget, QSplitter, QSplitterHandle, QHBoxLayout


class SplitterHandle(QSplitterHandle):
    clicked = Signal()
    
    def __init__(self, *args, **kwargs):
        super(SplitterHandle, self).__init__(*args, **kwargs)
        self.mouse_pressed = False
        self.mouse_moved = False

    def mousePressEvent(self, ev):
        super(SplitterHandle, self).mousePressEvent(ev)
        self.mouse_pressed = True

    def mouseMoveEvent(self, ev):
        super(SplitterHandle, self).mouseMoveEvent(ev)
        self.mouse_moved = True

    def mouseReleaseEvent(self, ev):
        super(SplitterHandle, self).mouseReleaseEvent(ev)
        if self.mouse_pressed and not self.mouse_moved: 
            self.clicked.emit()
        self.mouse_pressed = False
        self.mouse_moved = False


class Splitter(QSplitter):
    handle_clicked = Signal()

    def __init__(self, orientation, parent):
        super(Splitter, self).__init__(orientation, parent)

    def createHandle(self):
        print('createHandle')
        handle = SplitterHandle(self.orientation(), self)
        handle.clicked.connect(self.handle_clicked.emit)
        return handle


class CollapsiblePanel(QWidget):
    North = 'north'
    South = 'south'
    East = 'east'
    West = 'west'

    def __init__(self, parent, panel, location, collapsed=False):
        super(CollapsiblePanel, self).__init__()
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

        if location == CollapsiblePanel.North:
            self._init_panel(parent, panel, Qt.Vertical, False)
        elif location == CollapsiblePanel.South:
            self._init_panel(parent, panel, Qt.Vertical, True)
        elif location == CollapsiblePanel.East:
            self._init_panel(parent, panel, Qt.Horizontal, True)
        elif location == CollapsiblePanel.West:
            self._init_panel(parent, panel, Qt.Horizontal, False)

        if collapsed:
            self.collapse()

    def _init_panel(self, parent, panel, orientation, parent_first):
        panel.adjustSize()
        if orientation == Qt.Vertical:
            panel.setFixedHeight(panel.height())
        else:
            panel.setFixedWidth(panel.width())

        self._split = Splitter(orientation, self)
        self._split.handle_clicked.connect(self.toggle_collapsed)
        self.layout().addWidget(self._split, 1)
        if parent_first:
            self._split.addWidget(parent)
            self._split.addWidget(panel)
            self._parentidx, self._panelidx = 0,1
        else:
            self._split.addWidget(panel)
            self._split.addWidget(parent)
            self._parentidx, self._panelidx = 1,0

        self._split.setStretchFactor(self._parentidx, 1)
        self._split.setStretchFactor(self._panelidx, 0)

    def toggle_collapsed(self):
        if self.is_collapsed():
            self.uncollapse()
        else:
            self.collapse()

    def is_collapsed(self):
        size = self._split.sizes()
        return size[self._panelidx] == 0

    def collapse(self):
        sizes = self._split.sizes()
        sizes[self._panelidx] = 0
        self._split.setSizes(sizes)
    
    def uncollapse(self):
        sizes = self._split.sizes()
        sizes[self._panelidx] = 1
        self._split.setSizes(sizes)


if __name__ == '__main__':
    from PySide.QtGui import QApplication, QMainWindow, QWidget, QLabel
    import sys

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    parent = QWidget()
    b1 = QLabel('parent', parent)

    child = QWidget()
    b2 = QLabel('child', child)

    panel = CollapsiblePanel(parent, child, CollapsiblePanel.West)
    panel.resize(400,400)
    panel.show()
    sys.exit(app.exec_())
