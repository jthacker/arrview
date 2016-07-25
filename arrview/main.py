import os
import csv
import logging

from traits.api import *
from traitsui.api import *
from traitsui.key_bindings import KeyBinding, KeyBindings

from arrview.colormapper import ColorMapper
from arrview.file_dialog import qt_open_file, qt_save_file
from arrview.roi import ROIManager, ROIPersistence 
from arrview.slicer import Slicer
from arrview.tools import *
from arrview.ui.dimeditor import SlicerDims
from arrview.ui.slicereditor import PixmapEditor


import jtmri.roi


log = logging.getLogger('arrview')


bindings = KeyBindings(
    KeyBinding(binding1='Esc', 
        description='Escape Key',
        method_name='escape_pressed'))


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
    mode = Enum('pan','draw','move')
    roiManager = Instance(ROIManager)

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
        self.roiManager = ROIManager(
                slicer=self.slicer,
                slicerDims=slicerDims)
        self.bottomPanel = BottomPanel(
                slicerDims=slicerDims,
                cmap=ColorMapper(slicer=self.slicer))
        self.bottomPanel.cmap.norm.set_scale(slicer.arr)
        self._rois_updated =  rois_updated if rois_updated is not None else lambda x:x

        if roi_filename is None:
            self.roi_filename = os.path.join(os.path.abspath('.'))
        else:
            try:
                rois = ROIPersistence.load(roi_filename, self.slicer.shape)
                self.roiManager.rois.extend(rois)
                log.info('loading rois from: %s' % roi_filename)
            except IOError:
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
            'pan' : [PanTool(button='left'), 
                        ROIDisplayTool(roiManager=self.roiManager)],
            'draw': [ROIDrawTool(roiManager=self.roiManager),
                        ROIDisplayTool(roiManager=self.roiManager)],
            'move': [ROIEditTool(roiManager=self.roiManager)],
            }

        self.toolSet = ToolSet()
        self.mode_changed()

    @on_trait_change('mode')
    def mode_changed(self):
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
                            Item(),
                            show_labels=False),
                        Item('roiManager', style='custom'),
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
                        Action(name='As CSV', action='_export_csv_collapsed'),
                        name='Export'),
                    name='ROI')),
            resizable=True,
            title=self._title,
            key_bindings=bindings,
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
            ROIPersistence.save(info.object.roiManager.rois, filename)
            info.object._rois_updated(filename)

    def _load_rois(self, info):
        filename = qt_open_file(file_name=self.roi_file, filters='ROI (*.h5)')
        if filename:
            self.roi_file = filename
            rois = ROIPersistence.load(filename)
            info.object.roiManager.rois.extend(rois)

    def _get_export_file_name(self, ext):
        file_name = self.export_file
        if os.path.isfile(file_name):
            path, old_ext = os.path.splitext(file_name)
            file_name = os.path.join(path, ext)
        return file_name

    def _export_csv_collapsed(self, info):
        '''Exports the ROIs to a CSV file.
        ROIs with the same name are grouped together before the statistics
        are calculated.
        '''
        file_name = qt_save_file(file_name=self._get_export_file_name('csv'), filters='CSV (*.csv)')
        if not file_name:
            return
        self.export_file = file_name
        with open(file_name, 'w') as f:
            wr = csv.writer(f)
            wr.writerow(('roi', 'mean', 'std', 'size'))
            rois = jtmri.roi.ROISet(
                    [jtmri.roi.ROI(name=roi.name,
                                   poly=roi.poly,
                                   slc=roi.slc)
                                   for roi 
                                   in info.object.roiManager.rois])
            arr = info.object.slicer.arr
            for name in rois.names:
                mask = rois.by_name(name).to_mask(arr.shape)
                masked = arr[mask]
                wr.writerow((name, masked.mean(), masked.std(), masked.size))
    
    def escape_pressed(self, info):
        '''Prevent escape key from closing the window'''
        pass


if __name__ == '__main__':
    import numpy as np
    from operator import mul
    from . import view

    arr = np.random.random(32*43*53*23).reshape(32,43,53,23)
    view(arr)
