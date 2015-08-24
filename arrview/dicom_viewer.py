#!/usr/bin/env python
import os.path
import sys
import logging
from threading import Thread

## arrview must be imported before traits so that the qt backend will be used
from arrview import view
import jtmri.dcm
import jtmri.roi
from jtmri.fit import fit_r2star_with_threshold
from jtmri.reports.summary import DicomStudySummaryReport

from traits.api import (HasStrictTraits, List, Int, Str, Button, Instance,
        Directory, Any, Event, Bool, File)
from traitsui.api import (View, Group, HGroup, TableEditor, Item, MenuBar, Menu, Action,
                          Controller)
from traitsui.table_column import ObjectColumn
from traitsui.extras.checkbox_column import CheckboxColumn

from .reports import SummaryReportDialog, CombineForm722ReportDialog

log = logging.getLogger('dicom-viewer')


class DicomSeries(HasStrictTraits):
    series_number = Int
    description = Str
    images = Int
    slices = Int
    rois = Str
    series = Any

    def __init__(self, series):
        self.series = series
        self.update()
        
    def update(self):
        series = self.series
        s = series.first
        self.series_number = s.SeriesNumber
        self.description = s.SeriesDescription
        self.images = len(series)
        self.slices = len(set(filter(lambda x: x is not None, series.all.SliceLocation)))
        self.rois = ' '
        try:
            rois = sorted(series.first.meta.roi.iteritems(), key=lambda x: x[0])
            self.rois = ' '.join('%s: %d' % (k,len(v)) for k,v in rois)
        except AttributeError:
            pass


dicomseries_editor = TableEditor(
    sortable = False,
    configurable = False,
    auto_size = True,
    show_toolbar = False,
    selection_mode = 'rows',
    selected = 'selection',
    dclick = 'series_dclick',
    columns = [ ObjectColumn(name='series_number', label='Series', editable=False),
                ObjectColumn(name='description', label='Description', editable=False,
                             width=0.8),
                ObjectColumn(name='slices', label='Slices', editable=False),
                ObjectColumn(name='images', label='Images', editable=False),
                ObjectColumn(name='rois', label='ROIs', editable=False, width=0.2)])


class DicomReaderThread(Thread):
    def __init__(self, directory, progress=lambda x:x, finished=lambda x:x):
        super(DicomReaderThread, self).__init__()
        self.dcms = []
        self.count = 0
        self.directory = directory
        self.progress = progress
        self.finished = finished

    def run(self):
        self.dcms = jtmri.dcm.read(self.directory, progress=self.progress,
                                   disp=False, make_cache=True)
        self.finished(self.dcms) 


class DicomSeriesViewer(HasStrictTraits): 
    viewseries = Button
    directory = Directory
    load = Button
    roi_tag = Str('/')

    message = Str('Select a directory to load dicoms from')
    series = List(DicomSeries, [])
    selection = List(DicomSeries)
    series_dclick = Event

    dicomReaderThread = Instance(Thread)

    def _get_roi_filename(self, series):
        try:
            return series.first.meta.roi_filename[self.roi_tag]
        except (AttributeError, KeyError):
            return None

    def _series_dclick_fired(self):
        self._viewseries_fired()

    def _viewseries_fired(self):
        assert len(self.selection) == 1
        grouper = ['SliceLocation'] if self.selection[0].slices > 0 else []
        series = self.selection[0].series
        file_dir = os.path.dirname(series.first.filename) 
        roi_filename = self._get_roi_filename(series)
        if roi_filename is None:
            # Create ROIs directory if it does not exist
            # Assume that the ROIs will be saved to series_##.h5
            rois_dir = os.path.join(file_dir, 'rois')
            if not os.path.exists(rois_dir):
                os.mkdir(rois_dir)
            series_number = series.first.SeriesNumber
            series_name = 'series_%02d.h5' % series_number
            log.info('rois_dir: {} series: {}'.format(rois_dir, series_name))
            roi_filename = os.path.join(rois_dir, series_name)

        def rois_updated(filename):
            assert len(self.selection) == 1
            jtmri.dcm.dcminfo.update_metadata_rois(series)
            self.selection[0].update()

        view(series.data(grouper),
             title='Viewing: Series {} {!r}'.format(series.first.SeriesNumber,
                                                    series.first.SeriesDescription),
             roi_filename=roi_filename,
             rois_updated=rois_updated)

    def _load_fired(self):
        self._read_directory()
        
    def _directory_default(self):
        return os.path.abspath('.')
   
    def _directory_changed(self):
        self._read_directory()

    def _read_directory(self):
        self.series = []
        self._update_progress()
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

    def default_traits_view(self):
        return View(
            Group(
                HGroup(
                    Item('directory',
                        enabled_when='dicomReaderThread is None',
                        show_label=False),
                    Item('load',
                        label='Reload',
                        enabled_when='dicomReaderThread is None',
                        visible_when='False',
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
                        visible_when='len(series) == 0'),
                    springy=True),
                HGroup(
                    Item('viewseries',
                        label='View',
                        show_label=False,
                        enabled_when='len(selection) == 1'),
                    Item('roi_tag', label='ROI Tag'),
                    visible_when='len(series) > 0'),
                springy=True),
            menubar = MenuBar(
                Menu(
                    Action(name='Quit', action='_quit'),
                    name='File'),
                Menu(
                    Action(name='Images', action='_view_images',
                           enabled_when='len(selection) == 1'),
                    Action(name='R2* Map', action='_view_r2star_map',
                           enabled_when='len(selection) == 1'),
                    name='View'),
                Menu(
                    Action(name='Summary', action='_create_summary_report',
                           enabled_when='len(selection) > 0'),
                    Action(name='COMBINE 722', action='_create_combine_722_report',
                           enabled_when='len(selection) > 0'),
                    name='Reports')),
            title='Dicom Viewer',
            height=400,
            width=600,
            resizable=True,
            handler=DicomViewerHandler())


class DicomViewerHandler(Controller):
    def _quit(self, info):
        log.debug('closing window')
        self.close(info, is_ok=True)
        sys.exit(0)

    def _view_images(self, info):
        info.object._viewseries_fired()

    def _create_summary_report(self, info):
        selected_series = info.object.selection
        SummaryReportDialog(series=selected_series).configure_traits()
    
    def _create_combine_722_report(self, info):
        selected_series = info.object.selection
        CombineForm722ReportDialog(series=selected_series).configure_traits()

    def _view_r2star_map(self, info):
        '''Create R2star map or read the saved version'''
        log.debug('view R2*')
        dv = info.object
        assert len(dv.selection) == 1
        grouper = ['SliceLocation'] if dv.selection[0].slices > 0 else []
        series = dv.selection[0].series
        roi_filename = dv._get_roi_filename(series)
        data = series.data(grouper)
        echo_times = series.all_unique.EchoTime / 1000.
        r2star = fit_r2star_with_threshold(echo_times, data)
        view(r2star, roi_filename=roi_filename)


def main(path=None):
    if path is None:
        path = os.path.abspath('.')
    viewer = DicomSeriesViewer(directory=path)
    viewer.configure_traits()
    return viewer


if __name__=='__main__':
    from terseparse import Parser, Arg, KW
    import os
    import logging

    logging.getLogger().setLevel(logging.DEBUG)
    logging.basicConfig()

    p = Parser('dicom-viewer', 'Display dicom series for viewing and editing ROIs',
            Arg('directory', 'Working directory to start the viewer in',
                default=os.path.abspath('.'), nargs='?'))
    _, args = p.parse_args()
    main(args.ns.directory)
