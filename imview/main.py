import numpy as np

from traits.api import HasTraits, Instance, Any, on_trait_change, Int, Str, List
from traitsui.api import View, Item, Handler, HGroup, VGroup, Group

from .slicer import Slicer
from .colormapper import ColorMapper, ndarray_to_arraypixmap, ArrayPixmap
from .ui.slicereditor import SlicerEditor, MouseInput
from .ui.listeditor import DimEditor

class ImageView(HasTraits):
    slicer = Instance(Slicer)
    cmap = Instance(ColorMapper, ColorMapper())
    pixmap = Instance(ArrayPixmap)
    viewdims = List
    mi = MouseInput()
    mouse = Instance(MouseInput, mi)
    msg = Str()

    view = View(
        Group(
            HGroup(
                Item(name='pixmap', 
                    editor=SlicerEditor(mouse=mi),
                    show_label=False),
                VGroup(
                    Item(name='cmap', 
                        style='custom',
                        show_label=False),
                    Item(name='viewdims',
                         editor=DimEditor(),
                         show_label=False),
                    Item(name='msg',
                         style='readonly',
                         show_label=False)))),
        resizable=True)

    def __init__(self, arr):
        super(ImageView,self).__init__()
        self.slicer = Slicer(arr)
        self.viewdims = self._init_viewdims()
        self.update_pixmap()
        self.mouse.on_trait_change(self._pos_update, 'pos')

    def _init_viewdims(self):
        dims = self.slicer.dims
        viewdims = [None] * self.slicer.ndim
        viewdims[dims.x] = 'x'
        viewdims[dims.y] = 'y'
        return viewdims

    def viewdims_to_map(self):
        return {d:i for i,d in enumerate(self.viewdims)}

    @on_trait_change('viewdims')
    def update_view(self):
        m = self.viewdims_to_map() 
        self.slicer.set_viewdims(m['x'], m['y'])

    def _pos_update(self, trait, name, prev, curr):
        x,y = curr
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
    [XX,YY,TT] = np.meshgrid(x,y,t)
    arr = np.sqrt(XX**2 + YY**2) * np.exp(-2*TT)
    arr[arr > 0.8] = 0
    return ImageView(arr)

if __name__ == '__main__':
    init().configure_traits()
