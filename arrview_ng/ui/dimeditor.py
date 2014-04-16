from PySide.QtCore import Signal, Qt, QMimeData, QObject
from PySide.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QDrag, QFrame

from itertools import chain, cycle, izip
from functools import partial
from collections import OrderedDict

from .slider import SliderIntegerEditor
from ..slicer import SliceTuple

class DraggableLabel(QLabel):
    dragStart = Signal(object)
    dragFinish = Signal(object, object)
    dragEnter = Signal(object, object)
    dragLeave = Signal(object)

    def __init__(self, obj, disp, group):
        '''
        Args:
        group -- any object that can be used to determine the group that
                 a set of draggable labels belongs too. This will limit 
                 which labels can be dragged onto others.
        '''
        super(DraggableLabel, self).__init__()
        self.setAcceptDrops(True)
        self.disp = disp
        self.setObj(obj)
        self.group = group

    def setObj(self, obj):
        self.setText(self.disp(obj) if obj != None else ' ')
        self.obj = obj

    def dragLeaveEvent(self, ev):
        self.dragLeave.emit(self)

    def dragEnterEvent(self, ev):
        src = ev.source()
        if src.group is self.group:
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


class DimOrderWidget(QWidget):
    order_changed = Signal(object)

    def __init__(self, dimlist, slc, disp=_default_disp):
        super(DimOrderWidget, self).__init__()
        self.labels = []
        grp = object()
        for e in dimlist:
            l = DraggableLabel(e, disp, group=grp)
            l.setAlignment(Qt.AlignCenter)
            l.dragStart.connect(self.labelDragStart)
            l.dragEnter.connect(self.labelDragEnter)
            l.dragLeave.connect(self.labelDragLeave)
            l.dragFinish.connect(self.labelDragFinish)
            self.labels.append(l)
       
        self.setLayout(self._init_horizontal(dimlist, slc, disp))

        self.dimlist = dimlist
        self.setStyleSheet(
                'QLabel { qproperty-alignment: AlignCenter; color: rgb(50,50,50); } '
                'DraggableLabel { border: 1px solid; } ')

    def _init_horizontal(self, dimlist, slc, disp):
        self.slc_labels = []
        box = QHBoxLayout()
        box.setSpacing(0)
        box.setContentsMargins(0,0,0,0)
       
        header = QWidget()
        header.setLayout(QVBoxLayout())
        header.layout().addWidget(QLabel('len'))
        header.layout().addWidget(QLabel('slc'))
        header.layout().addWidget(QLabel('view'))
        header.setStyleSheet("QLabel { qproperty-alignment: 'AlignVCenter | AlignRight'; }")
        box.addWidget(header)

        cols = []
        for i,l in enumerate(self.labels):   
            col = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(0)
            layout.setContentsMargins(1,0,1,0)
            slcLabel = QLabel(str(slc[i]))
            self.slc_labels.append(slcLabel)
            col.setLayout(layout)
            col.layout().addWidget(QLabel(str(slc.shape[i])))
            col.layout().addWidget(slcLabel)
            col.layout().addWidget(l)
            cols.append(col)
            box.addWidget(col)
       
        sizes = [c.minimumSizeHint() for c in cols]
        if len(sizes) > 0:
            minSize = max(sizes, key=lambda x:x.width())
            for c in cols:
                c.setMinimumSize(minSize)
        return box

    def update_slc(self, slc):
        for i,d in enumerate(slc):
            self.slc_labels[i].setText(str(d))

    def getState(self):
        return [d.obj for d in self.labels]

    def setState(self, dimlist):
        assert len(dimlist) == len(self.labels)
        for d,label in izip(dimlist,self.labels):
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
            self.order_changed.emit(self.getState())
        else: 
            self.setState(self.startState)



_color_map = {
    'x': 'red',
    'y': 'blue',
    'z': 'green',
    't': 'magenta' }

def _disp(name, color_map=_color_map):
    if name in color_map:
        color = color_map[name]
        return "<font color='%s'>%s</font>" % (color, name)
    else:
        return name


class SliceEditor(QObject):
    slice_changed = Signal(object)
    view_changed = Signal(object)
    freedim_names = ('z', 't')

    def __init__(self, slc):
        super(SliceEditor, self).__init__()
        self._slc = slc
        self._dimlist = self._init_dimlist(slc)
        self._freedim_editors = self._init_freedim_editors()
        self._update_freedim_editors(self._dimlist)

    def _init_dimlist(self, slc):
        dimlist = [d if i in slc.viewdims else None for i,d in enumerate(slc)]
        for fd,name in zip(slc.freedims, SliceEditor.freedim_names):
            dimlist[fd] = name
        return dimlist

    def _init_freedim_editors(self):
        editors = OrderedDict()
        for name in SliceEditor.freedim_names:
            editor = SliderIntegerEditor(0,0,0)
            editor.value_changed.connect(lambda val, name=name: self._freedim_value_changed(name, val))
            editors[name] = editor
        return editors
   
    def _update_freedim_editors(self, dimlist):
        freedims = ((name,d) for d,name in enumerate(dimlist) if name in SliceEditor.freedim_names)
        for name,d in freedims:
            editor = self._freedim_editors[name]
            editor.range = (0, self.slc.shape[d]-1)
            editor.value = self.slc[d]

    def _freedim_value_changed(self, name, val):
        dim = self._dimlist.index(name)
        self._slc = self.slc.set_freedim(dim, val)
        self.slice_changed.emit(self._slc)

    def _vieworder_changed(self, dimlist):
        self._dimlist = dimlist
        self._slc = self.slc.set_viewdims(dimlist.index('x'), dimlist.index('y'))
        self._update_freedim_editors(dimlist)
        self.view_changed.emit(dimlist)
        self.slice_changed.emit(self._slc)

    def widget(self):
        dimorder = DimOrderWidget(self._dimlist, self.slc, disp=_disp)
        dimorder.order_changed.connect(self._vieworder_changed)
        self.slice_changed.connect(dimorder.update_slc)
        self.view_changed.connect(dimorder.setState)

        fd_widgets = QWidget()
        fd_widgets.setLayout(QVBoxLayout())
        for name,editor in self._freedim_editors.iteritems():
            row = QWidget()
            row.setLayout(QHBoxLayout())
            row.layout().setContentsMargins(0,0,0,0)
            row.layout().addWidget(QLabel(_disp(name)))
            row.layout().addWidget(editor.widget())
            fd_widgets.layout().addWidget(row)

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)

        widget = QWidget()
        widget.setLayout(QHBoxLayout())
        widget.layout().setContentsMargins(0,0,0,0)
        widget.layout().addWidget(dimorder)
        widget.layout().addWidget(line)
        widget.layout().addWidget(fd_widgets)
        return widget

    @property
    def slc(self):
        return self._slc


## Quick Test ##
def main():
    import sys
    import numpy as np
    from PySide.QtGui import QApplication, QMainWindow
    from ..slicer import Slicer

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    def debug(state): print('slice changed', state)

    slicer = Slicer(np.empty((10,20,30,40,50)))
    editor = SliceEditor(slicer.slc.set_viewdims(2,4))
    editor.slice_changed.connect(debug)
    
    win = QMainWindow()
    win.setCentralWidget(editor.widget)
    win.setVisible(True)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 
