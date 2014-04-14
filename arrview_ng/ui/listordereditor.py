from PySide.QtCore import Signal, Qt, QMimeData
from PySide.QtGui import QLabel, QWidget, QHBoxLayout, QDrag

from itertools import chain, cycle, izip
from functools import partial

from ..util import weave


class DraggableLabel(QLabel):
    dragStart = Signal(object)
    dragFinish = Signal(object, object)
    dragEnter = Signal(object, object)
    dragLeave = Signal(object)

    def __init__(self, obj, disp):
        super(DraggableLabel, self).__init__()
        self.setAcceptDrops(True)
        self.disp = disp
        self.setObj(obj)

    def setObj(self, obj):
        self.setText(self.disp(obj) if obj != None else ' ')
        self.obj = obj

    def dragLeaveEvent(self, ev):
        self.dragLeave.emit(self)

    def dragEnterEvent(self, ev):
        src = ev.source()
        if src.parent() == self.parent():
            self.dragEnter.emit(src, self)
            ev.accept()

    def dropEvent(self, ev):
        ev.accept()

    def mouseMoveEvent(self, ev):
        if ev.buttons() == Qt.LeftButton and self.obj != None:
            drag = QDrag(self)
            mimeData = QMimeData()
            mimeData.setText(str(self.obj))
            drag.setMimeData(mimeData)
            self.dragStart.emit(self)
            drag.start(Qt.MoveAction)
            self.dragFinish.emit(self, drag.target())

    def __repr__(self):
        return "DraggableLabel(obj=%s)" % (self.obj)


def _default_disp(obj):
    return str(obj)


class ListOrderWidget(QWidget):
    orderChanged = Signal(object)

    def __init__(self, lst, disp=_default_disp):
        super(ListOrderWidget, self).__init__()
        hbox = QHBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(5,0,0,0)
        self.init_labels(lst, hbox, disp)
        self.setLayout(hbox)
        self.lst = lst

    def init_labels(self, lst, layout, disp):
        self.labels = []
        sizes = []
        for e in lst:
            l = DraggableLabel(e, disp)
            l.dragStart.connect(self.labelDragStart)
            l.dragEnter.connect(self.labelDragEnter)
            l.dragLeave.connect(self.labelDragLeave)
            l.dragFinish.connect(self.labelDragFinish)
            self.labels.append(l)
            sizes.append(l.size())

        layout.addWidget(QLabel('['))
        for l in weave(lambda: QLabel(','), self.labels):
            layout.addWidget(l)
        layout.addWidget(QLabel(']'))
       
        sizes = [l.minimumSizeHint() for l in self.labels]
        if len(sizes) > 0:
            minSize = max(sizes, key=lambda x:x.width())
            for l in self.labels:
                l.setMinimumSize(minSize)

    def getState(self):
        return [d.obj for d in self.labels]

    def setState(self, lst):
        assert len(lst) == len(self.labels)
        for d,label in izip(lst,self.labels):
            label.setObj(d)

    def labelDragStart(self, src):
        self.startState = self.getState()

    def labelDragLeave(self, ev):
        self.setState(self.startState)

    def labelDragEnter(self, src, target):
        self.setState(self.startState)
        self._swapLabels(src, target)

    def _swapLabels(self, l1, l2):
        o1 = l1.obj
        o2 = l2.obj
        l1.setObj(o2)
        l2.setObj(o1)

    def labelDragFinish(self, src, target):
        if target:
            self.setState(self.startState)
            self._swapLabels(src, target)
            self.orderChanged.emit(self.getState())
        else: 
            self.setState(self.startState)



## Quick Test ##
def main():
    import sys
    from PySide.QtGui import QApplication, QMainWindow
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    def debug(state): print('order changed', state)

    listWidget = ListOrderWidget(['x','y','z',None,None])
    listWidget.orderChanged.connect(debug)

    win = QMainWindow()
    win.setCentralWidget(listWidget)
    win.setVisible(True)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 
