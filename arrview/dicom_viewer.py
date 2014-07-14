import os.path
from threading import Thread

from traits.api import (HasTraits, HasStrictTraits, List, Int, String, Button, Instance,
        Directory, Any)
from traitsui.api import (View, Group, HGroup, TableEditor, Item)
from traitsui.table_column import ObjectColumn

import jtmri.dcm

from . import view

class DicomSeries(HasStrictTraits):
    series_number = Int
    description = String
    images = Int
    slices = Int

    series = Any

    def __init__(self, series):
        s = series.first
        self.series = series
        self.series_number = s.SeriesNumber
        self.description = s.SeriesDescription
        self.images = len(series)
        self.slices = len(set(filter(lambda x: x is not None, series.all.SliceLocation))) 


dicomseries_editor = TableEditor(
    sortable = False,
    configurable = False,
    auto_size = True,
    show_toolbar = False,
    selection_mode = 'row',
    selected = 'selection',
    columns = [ ObjectColumn(name='series_number', label='Series', editable=False),
                ObjectColumn(name='description', label='Description', editable=False, width=1.0),
                ObjectColumn(name='slices', label='Slices', editable=False),
                ObjectColumn(name='images', label='Images', editable=False) ])


class DicomReaderThread(Thread):
    def __init__(self, directory, progress=lambda x:x, finished=lambda x:x):
        super(DicomReaderThread, self).__init__()
        self.dcms = []
        self.count = 0
        self.directory = directory
        self.progress = progress
        self.finished = finished

    def run(self):
        self.dcms = jtmri.dcm.read(self.directory, progress=self.progress, disp=False)
        self.finished(self.dcms) 


class DicomSeriesViewer(HasStrictTraits): 
    viewseries = Button
    directory = Directory
    load = Button

    series = List(DicomSeries, [])
    message = String('Select a directory to load dicoms from')
    selection = Instance(DicomSeries)

    dicomReaderThread = Instance(Thread)

    def default_traits_view(self):
        dicomseries_editor.dclick
        return View(
            Group(
                HGroup(
                    Item('viewseries',
                        label='View',
                        show_label=False,
                        enabled_when='selection is not None'),
                    Item('directory',
                        enabled_when='dicomReaderThread is None',
                        show_label=False),
                    Item('load',
                        label='Load',
                        enabled_when='dicomReaderThread is None',
                        show_label=False)),
                Group(
                    Item('series',
                            show_label=False,
                            editor=dicomseries_editor,
                            style='readonly',
                            visible_when='len(series) > 0'),
                    Item('message',
                        show_label=False,
                        style='readonly',
                        visible_when='len(series) == 0'))),
            title='Dicom Viewer',
            height=400,
            width=600,
            resizable=True)

    def _viewseries_fired(self):
        grouper = ['SliceLocation'] if self.selection.slices > 0 else []
        series = self.selection.series
        
        try:
            roi_filename = series.first.meta.roi_filename
        except AttributeError as e:
            roi_filename = os.path.dirname(series.first.filename)

        view(series.data(grouper), roi_filename=roi_filename)

    def _load_fired(self):
        self._read_directory()
        
    def _directory_default(self):
        return os.path.abspath('.')
   
    def _directory_changed(self):
        self._read_directory()

    def _read_directory(self):
        self.series = []
        self.dicomReaderThread = DicomReaderThread(self.directory,
                progress=self._update_progress,
                finished=self._directory_finished_loading)
        self.dicomReaderThread.start()

    def _update_progress(self, count=0):
        self.message = 'Read %d dicoms from %s' % (count, self.directory)

    def _directory_finished_loading(self, dcms):
        dicomseries = []
        for series in dcms.series():
            s = series.first
            dicomseries.append(DicomSeries(series))
        self.series = dicomseries
        self.dicomReaderThread = None


def main(path):
    viewer = DicomSeriesViewer()
    viewer.configure_traits()
    return viewer


if __name__=='__main__':
    main(os.path.abspath('.'))
