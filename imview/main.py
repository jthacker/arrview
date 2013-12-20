from traitsui.api import View, Item
from .slicer import Slicer
from .ui.slicer import SlicerEditor
import numpy as np

if __name__ == '__main__':
   view = View(Item(name='view', editor=SlicerEditor(),
       show_label=False),
       width=400,
       height=300,
       resizable=True)

   x = np.linspace(-1,1,256)
   [XX,YY] = np.meshgrid(x,x)
   arr = np.sqrt(XX**2 + YY**2)
   arr[arr > 0.8] = 0
   slicer = Slicer(arr)
   slicer.configure_traits(view=view)
