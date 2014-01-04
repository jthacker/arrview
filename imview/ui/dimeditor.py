from traits.api import (HasPrivateTraits, Property, Int, Instance,
        List, Bool, Range, on_trait_change)
from traitsui.api import (View, Group, Item, RangeEditor, HGroup,
        Spring)
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory

from PySide.QtCore import QTimer

from .listeditor import ListOrderWidget
from ..slicer import Slicer

class _DimEditor(Editor):
    @staticmethod
    def disp(name):
        colorMap = { 
            'x': 'red',
            'y': 'blue',
            'z': 'green' }
        if name in colorMap:
            color = colorMap[name]
            return "<font color='%s'>%s</font>" % (color,name)
        else:
            return name

    def init(self, parent):
        self.control = ListOrderWidget(self.value, _DimEditor.disp)
        self.control.orderChanged.connect(self._changed)

    def _changed(self, lst):
        self.value = lst

    def update_editor(self):
        self.control.setState(self.value)


class DimEditor(BasicEditorFactory):
    klass = _DimEditor


class FreeDim(HasPrivateTraits):
    dim = Int
    val = Int(0)
    val_high = Int
    fps = Range(low=1, high=30, value=30)
    sleep_ms = Property(depends_on=['fps'])
    autoInc = Bool(False)

    view = View(
            HGroup(
                Item('autoInc',
                    label='Inc'),
                Item('fps'),
                Item('val',
                    editor=RangeEditor(
                        low=0,
                        high_name='val_high',
                        mode='slider'))))

    def __init__(self, **traits):
        super(FreeDim, self).__init__(**traits)
        self._timer = QTimer()
        self._timer.timeout.connect(self.inc)

    def _get_sleep_ms(self):
        time = int(1000.0/self.fps)
        return time

    @on_trait_change('autoInc,fps')
    def autoinc_toggled(self):
        if self.autoInc:
            self._timer.start(self.sleep_ms)
        else:
            self._timer.stop()

    def inc(self):
        if self.val == self.val_high:
            self.val = 0
        else:
            self.val += 1


class SlicerDims(HasPrivateTraits):
    slicer = Instance(Slicer)
    freedim = Instance(FreeDim)
    _dimlist = List

    view = View(
            HGroup(
                Item('_dimlist', editor=DimEditor(), 
                    springy=False, show_label=False), 
                Item('freedim', style='custom', show_label=False)))

    def __init__(self, slicer):
        super(SlicerDims, self).__init__(slicer=slicer)
        dims = [None] * slicer.ndim
        dims[slicer.xdim] = 'x'
        dims[slicer.ydim] = 'y'
        freedims = slicer.freedims
        if freedims:
            dims[freedims[0]] = 'z'
        self.freedim = FreeDim()
        self._dimlist = dims
    
    def _dimlist_to_map(self):
        return {d:i for i,d in enumerate(self._dimlist)}

    @on_trait_change('_dimlist[]')
    def dimlist_changed(self):
        m = self._dimlist_to_map() 
        self.slicer.set_viewdims(m['x'], m['y'])
        if 'z' in m:
            zdim = m['z']
            self.freedim.dim = zdim
            self.freedim.val = self.slicer.slc[zdim]
            self.freedim.val_high = self.slicer.dim_size(zdim)-1

    @on_trait_change('freedim.val')
    def freedim_changed(self):
        f = self.freedim
        self.slicer.set_freedim(f.dim, f.val)
    

## Quick Test ##
if __name__ == '__main__':
    from traits.api import HasTraits, Instance
    from traitsui.api import View, Item, Group
    from ..slicer import Slicer
    import numpy as np

    arr = np.arange(2*3*4*5).reshape([2,3,4,5])
    sd = SlicerDims(slicer=Slicer(arr))
    sd.configure_traits()
