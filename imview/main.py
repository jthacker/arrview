import numpy as np

from traits.api import (HasTraits, Instance, Any, 
        on_trait_change, Int, Str, List)
from traitsui.api import (View, Item, Handler, 
        HGroup, VGroup, Group, RangeEditor, EnumEditor)

from .slicer import Slicer
from .colormapper import ColorMapper, ndarray_to_arraypixmap, ArrayPixmap
from .tool import tools
from .util import weave
from .ui.slicereditor import SlicerEditor, MouseInput, ArrayGraphicsView
from .ui.listeditor import DimEditor

class ImageView(HasTraits):
    slicer = Instance(Slicer)
    cmap = Instance(ColorMapper, ColorMapper())
    pixmap = Instance(ArrayPixmap)
    viewdims = List
    zDimVal = Int
    zDimHigh = Int
    mouse = Instance(MouseInput, MouseInput())
    graphicsView = Instance(ArrayGraphicsView, ArrayGraphicsView())
    tool = Any(tools[0])
    msg = Str()

    view = View(
            Group(
                HGroup(
                    Item(name='pixmap', 
                        editor=SlicerEditor(mouse=mouse.default_value, 
                            view=graphicsView.default_value),
                        show_label=False),
                    VGroup(
                        Item(name='cmap', 
                            style='custom',
                            show_label=False),
                        Item(name='viewdims',
                            editor=DimEditor(),
                            show_label=False),
                        Item(name='zDimVal',
                            editor=RangeEditor(low=0,
                                high_name='zDimHigh',
                                mode='slider'),
                            show_label=False),
                        Item(name='msg',
                            style='readonly',
                            show_label=False),
                        Item(name='tool',
                            editor=EnumEditor(values={t:t.name for t in tools}))))),
                        resizable=True)

    def __init__(self, arr):
        super(ImageView,self).__init__()
        self.slicer = Slicer(arr)
        self.viewdims = self._init_viewdims()
        self.update_pixmap()
        self.mouse.on_trait_event(self.mouse_moved, 'moved')
        self.mouse.on_trait_event(self.mouse_wheeled, 'wheeled')
        self.tool_instance = self.tool()
        self.tool_instance.init(self.graphicsView)

    def _init_viewdims(self):
        dims = self.slicer.dims
        viewdims = [None] * self.slicer.ndim
        viewdims[dims.x] = 'x'
        viewdims[dims.y] = 'y'
        if dims.free:
            viewdims[list(sorted(dims.free))[0]] = 'z'
        return viewdims

    def viewdims_to_map(self):
        return {d:i for i,d in enumerate(self.viewdims)}

    @on_trait_change('tool')
    def tool_changed(self, trait, name, prev, curr):
        self.tool_instance.destroy()
        self.tool_instance = curr()
        self.tool_instance.init(self.graphicsView)

    @on_trait_change('viewdims')
    def update_view(self):
        m = self.viewdims_to_map() 
        self.slicer.set_viewdims(m['x'], m['y'])
        if 'z' in m:
            zdim = m['z']
            self.zDimVal = self.slicer.slc[zdim]
            self.zDimHigh = self.slicer.dim_size(zdim)-1

    @on_trait_change('zDimVal')
    def zDimVal_updated(self):
        zdim = self.viewdims_to_map()['z']
        self.slicer.set_freedim(zdim, self.zDimVal)

    
    def display_array_value(self):
        x,y = self.mouse.pos
        slc = list(self.slicer.slc)
        xDim,yDim,_ = self.slicer.dims
        slc[xDim], slc[yDim] = x,y
        
        view = self.slicer.view
        shape = view.shape
        xMax,yMax = shape[1],shape[0]

        msg = '(%s) ' % ','.join(['%03d' % p for p in slc])
        if 0 <= x < xMax and 0 <= y < yMax:
            msg += "%0.2f" % view[y,x]
        else:
            msg += "  "
        self.msg = msg

    def mouse_moved(self):
        self.display_array_value()
        self.tool_instance.mouse_moved(self.mouse)

    def mouse_wheeled(self):
        self.tool_instance.mouse_wheeled(self.mouse)

    @on_trait_change('[cmap.+, slicer.view]')
    def update_pixmap(self):
        self.pixmap = ndarray_to_arraypixmap(self.slicer.view,
                self.cmap.cmap, self.cmap.norm)


def changed(a,b,c,d): 
    print('Debug',a,b,c,d)


def init():
    x = np.linspace(-1,1,256)
    y = np.linspace(-1,1,128)
    t = np.linspace(0,1,32)
    v = np.linspace(-np.pi,np.pi,64)
    [XX,YY,TT,VV] = np.meshgrid(x,y,t,v)
    arr = np.sqrt(XX**2 + YY**2) * np.exp(-2*TT) * np.cos(VV)
    arr[arr > 0.8] = 0
    return ImageView(arr)

if __name__ == '__main__':
    init().configure_traits()
