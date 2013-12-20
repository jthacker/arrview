import matplotlib
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavToolbar
from matplotlib.figure import Figure

from PySide.QtGui import *
from PySide.QtCore import *

from traits.api import Any, Instance
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory


class _MPLFigureEditor(Editor):

    scrollable  = True

    def init(self, parent):
        self.control = self._create_canvas(parent)
        self.set_tooltip()

    def update_editor(self):
        print('update_editor')

    def _create_canvas(self, parent):
        """ Create the MPL canvas. """
        # The panel lets us add additional controls.
        panel = QWidget()
        #panel.setStyleSheet(":hover {border: 2px solid;}") 
        
        # matplotlib commands to create a canvas
        self._canvas = FigureCanvas(self.value)
        self._canvas.setParent(panel)
        self._toolbar = NavToolbar(self._canvas, panel)

        vbox = QVBoxLayout()
        vbox.addWidget(self._canvas)
        vbox.addWidget(self._toolbar)
        panel.setLayout(vbox)
        return panel

class MPLFigureEditor(BasicEditorFactory):

    klass = _MPLFigureEditor


if __name__ == "__main__":
    # Create a window to demo the editor
    from traits.api import HasTraits
    from traitsui.api import View, Item
    from numpy import sin, cos, linspace, pi

    class Test(HasTraits):

        figure = Instance(Figure, ((5,8),))

        def __init__(self):
            super(Test, self).__init__()
            axes = self.figure.add_subplot(111)
            t = linspace(0, 2*pi, 200)
            axes.plot(sin(t)*(1+0.5*cos(11*t)), cos(t)*(1+0.5*cos(11*t)))


    view = View(Item('figure', editor=MPLFigureEditor(),
        show_label=False),
        width=400,
        height=300,
        resizable=True)

    Test().configure_traits(view=view)
