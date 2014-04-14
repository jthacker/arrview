from PySide.QtCore import Qt
from PySide.QtGui import QWidget, QSplitter, QHBoxLayout


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

        self._split = QSplitter(orientation, self)
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

    def collapse(self):
        self._split.setSizes([0,0])
    
    def uncollapse(self):
        self._split.setSizes([1,1])


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
