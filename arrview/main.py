import os
import csv
import logging

from traits.api import *
from traitsui.api import *
from traitsui.key_bindings import KeyBinding, KeyBindings

from arrview.colormapper import ColorMapper
from arrview.file_dialog import qt_open_file, qt_save_file
from arrview.roi import ROIManager
from arrview.roi_persistence import load_rois, store_rois
from arrview.slicer import Slicer
from arrview.tools import *
from arrview.ui.dimeditor import SlicerDims
from arrview.ui.slicereditor import PixmapEditor


log = logging.getLogger(__name__)


class BottomPanel(HasTraits):
    slicerDims = Instance(SlicerDims)
    cmap = Instance(ColorMapper)

    view = View(
            Item('slicerDims', style='custom', show_label=False),
            Item('cmap', style='custom', show_label=False),
            )


class ArrayViewer(HasTraits):
    slicer = Instance(Slicer)
    pixmap = Property(depends_on=['bottomPanel.cmap.+',
        'bottomPanel.cmap.norm.+', 'slicer.view'])
    bottomPanel = Instance(BottomPanel)
    mode = Enum('pan', 'draw', 'erase')
    roi_size = Range(0, 30, 3)
    roi_manager = Instance(ROIManager)

    cursorInfo = Str
    colormapInfo = Str

    toolSet = Instance(ToolSet)

    def __init__(self, slicer, roi_filename=None, title=None, rois_updated=None):
        '''Initialize ArrayViewer from a slicer and optional roi file
        Args:
            slice        -- Slice object that holds array and currently viewed slice
            roi_filename -- Filename for read/writing ROIs to
            title        -- (default: Array Viewer) Title of the window
            rois_updated -- (default: None) Callback function, called when ROIs have changed
        '''
        super(ArrayViewer, self).__init__()
        self._title = 'Array Viewer' if title is None else title
        self.slicer = slicer
        slicerDims = SlicerDims(self.slicer)
        self.roi_manager = ROIManager(
                slicer=self.slicer,
                slicerDims=slicerDims)
        self.bottomPanel = BottomPanel(
                slicerDims=slicerDims,
                cmap=ColorMapper(slicer=self.slicer))
        self.bottomPanel.cmap.norm.set_scale(slicer.arr)
        self._rois_updated = rois_updated if rois_updated is not None else lambda x:x

        if roi_filename is None:
            self.roi_filename = os.path.join(os.path.abspath('.'))
        else:
            try:
                rois = load_rois(roi_filename, self.slicer.shape)
                self.roi_manager.add_rois(rois)
                log.info('loading rois from: %s' % roi_filename)
            except IOError:
                log.debug('failed to load rois, ignoring')
                pass
            self.roi_filename = roi_filename

        self._defaultFactories = [
            CursorInfoTool(
                slicer=self.slicer,
                callback=self.update_cursorinfo),
            ColorMapTool(
                slicer=self.slicer,
                colorMapper=self.bottomPanel.cmap,
                callback=self.update_colormapinfo),
            PanTool(button='middle'),
            ZoomTool()]

        self._factoryMap = {
            'pan': [PanTool(button='left'), ROITool(factory=self, roi_manager=self.roi_manager)],
            'draw': [ROITool(factory=self, roi_manager=self.roi_manager, mode='draw')],
            'erase': [ROITool(factory=self, roi_manager=self.roi_manager, mode='erase')]
            }

        self.toolSet = ToolSet()
        self.mode_changed()

    @on_trait_change('mode')
    def mode_changed(self):
        log.debug('mode changed to %r', self.mode)
        self.toolSet.factories = self._defaultFactories + self._factoryMap[self.mode]

    def update_cursorinfo(self, msg):
        self.cursorInfo = msg

    def update_colormapinfo(self, msg):
        self.colormapInfo = msg

    def default_traits_view(self):
        return View(
            VSplit(
                HSplit(
                    Item('pixmap',
                        editor=PixmapEditor(toolSet=self.toolSet),
                        show_label=False,
                        width=0.9),
                    Group(
                        HGroup(
                            Item('mode', style='custom',springy=False),
                            show_labels=False),
                        Item('roi_size', enabled_when='mode in ["draw", "erase"]'),
                        Item('roi_manager', style='custom'),
                        show_labels=False)),
                Item('bottomPanel', style='custom', show_label=False,
                    height=1)),
            statusbar = [
                StatusItem(name='cursorInfo'),
                StatusItem(name='colormapInfo')],
            menubar = MenuBar(
                Menu(
                    Action(name='Quit', action='_quit'),
                    name='File'),
                Menu(
                    Action(name='Save', action='_save_rois'),
                    Action(name='Load', action='_load_rois'),
                    Menu(
                        Action(name='As CSV', action='_export_csv'),
                        name='Export'),
                    name='ROI')),
            resizable=True,
            title=self._title,
            key_bindings=KeyBindings(
                KeyBinding(binding1='Esc',
                    description='Escape Key',
                    method_name='escape_pressed'),
                KeyBinding(binding1='D',
                    description='Increment free dimension',
                    method_name='free_dim_increment'),
                KeyBinding(binding1='A',
                    description='Decrement free dimension',
                    method_name='free_dim_decrement'),
                *[KeyBinding(binding1=str(i),
                             description='Select ROI {}'.format(i),
                             method_name='select_roi_{}'.format(i))
                  for i in range(1, 10)]),
            handler=ArrayViewerHandler(roi_file=self.roi_filename,
                                       export_file=os.path.splitext(self.roi_filename)[0]))

    @cached_property
    def _get_pixmap(self):
        return self.bottomPanel.cmap.array_to_pixmap(self.slicer.view)


class ArrayViewerHandler(Handler):
    roi_file = File
    export_file = File

    def _quit(self, info):
        log.debug('closing window')
        self.close(info, is_ok=True)

    def _save_rois(self, info):
        filename = qt_save_file(file_name=self.roi_file, filters='ROI (*.h5)')
        if filename:
            self.roi_file = filename
            store_rois(info.object.roi_manager.rois, filename)
            info.object._rois_updated(filename)

    def _load_rois(self, info):
        filename = qt_open_file(file_name=self.roi_file, filters='ROI (*.h5)')
        if filename:
            self.roi_file = filename
            rois = load_rois(filename, info.object.slicer.shape)
            info.object.roi_manager.add_rois(rois)

    def _get_export_file_name(self, ext):
        file_name = self.export_file
        if os.path.isfile(file_name):
            path, old_ext = os.path.splitext(file_name)
            file_name = os.path.join(path, ext)
        return file_name

    def _export_csv(self, info):
        """Exports the ROIs to a CSV file"""
        file_name = qt_save_file(file_name=self._get_export_file_name('csv'), filters='CSV (*.csv)')
        if not file_name:
            return
        self.export_file = file_name
        with open(file_name, 'w') as f:
            wr = csv.writer(f)
            wr.writerow(('roi', 'mean', 'std', 'size'))
            for rv in info.object.roi_manager.roiviews:
                wr.writerow((rv.roi.name, rv.mean, rv.std, rv.size))
        log.debug('finished export to csv %r', file_name)

    def escape_pressed(self, info):
        """Prevent escape key from closing the window"""
        log.debug('ignoring escape key, prevents window from closing')

    def free_dim_increment(self, info):
        info.object.bottomPanel.slicerDims.freedim.inc()

    def free_dim_decrement(self, info):
        info.object.bottomPanel.slicerDims.freedim.dec()

    def select_roi_1(self, info):
        self.select_roi_by_index(info, 1)

    def select_roi_2(self, info):
        self.select_roi_by_index(info, 2)

    def select_roi_3(self, info):
        self.select_roi_by_index(info, 3)

    def select_roi_4(self, info):
        self.select_roi_by_index(info, 4)

    def select_roi_5(self, info):
        self.select_roi_by_index(info, 5)

    def select_roi_6(self, info):
        self.select_roi_by_index(info, 6)

    def select_roi_7(self, info):
        self.select_roi_by_index(info, 7)

    def select_roi_8(self, info):
        self.select_roi_by_index(info, 8)

    def select_roi_9(self, info):
        self.select_roi_by_index(info, 9)

    def select_roi_by_index(self, info, idx):
        info.object.roi_manager.select_roi_by_index(idx)


def view(arr, roi_filename=None, rois_updated=None, title=None):
    viewer = ArrayViewer(Slicer(arr),
                         roi_filename=roi_filename,
                         title=title,
                         rois_updated=rois_updated)
    viewer.configure_traits()
    return viewer


def main():
    import numpy as np

    logging.getLogger().setLevel(logging.DEBUG)
    logging.basicConfig()
    log.debug('debugging enabled')

    shape = [256, 256, 16, 34]
    arr = np.random.random(reduce(lambda a,b: a*b, shape)).reshape(*shape)
    view(arr)


if __name__ == '__main__':
    main()
