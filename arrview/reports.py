import logging

import jtmri.dcm
from jtmri.fit import fit_r2star_with_threshold
from jtmri.reports.summary import DicomStudySummaryReport
from jtmri.reports import DicomStudySummaryReport, CombineForm722Report
from jtmri.utils import flatten, unique

from traits.api import (HasTraits, HasStrictTraits, List, Int, Str, Button, Instance,
        Directory, Any, Event, Bool, File, Enum, Property)
from traitsui.api import (View, Group, HGroup, TableEditor, Item, MenuBar, Menu, Action,
                          Controller)

from traitsui.table_column import ObjectColumn
from traitsui.extras.checkbox_column import CheckboxColumn

from .file_dialog import qt_save_file


log = logging.getLogger('reports')


class ReportSeries(HasStrictTraits):
    series_number = Int
    description = Str
    r2star = Bool(default=False)
    series = Any

    @staticmethod
    def from_dicom_series(dicom_series):
        s = dicom_series.series.first
        return ReportSeries(
            series_number = s.SeriesNumber,
            description = s.SeriesDescription,
            series = dicom_series.series)


report_series_editor = TableEditor(
    sortable = False,
    configurable = True,
    reorderable = True,
    deletable = True,
    auto_size = True,
    show_toolbar = True,
    columns = [
        ObjectColumn(name='series_number', label='Series', editable=False),
        ObjectColumn(name='description', label='Description', editable=True),
        CheckboxColumn(name='r2star', label='Offline R2*', editable=True) ])


class SummaryReportDialog(HasStrictTraits):
    series = List(ReportSeries)
    save = Button
    report_file = File

    def __init__(self, series):
        series = [ReportSeries.from_dicom_series(s) for s in series]
        super(SummaryReportDialog, self).__init__(
                series=series,
                report_file='summary-report.html')
    
    def _save_fired(self):
        log.info('report building started')
        filename = qt_save_file(file_name=self.report_file, filters='html (*.html)')
        if not filename:
            return
        self.report_file = filename
        dcms = jtmri.dcm.DicomSet(flatten(rs.series for rs in self.series))
        report = DicomStudySummaryReport(dcms)
        for report_series in self.series:
            log.info('adding series {}'.format(report_series.series_number))
            if report_series.r2star:
                report.add_series_r2star(report_series.series_number,
                                         description=report_series.description)
            else:
                report.add_series(report_series.series_number,
                                  description=report_series.description)
        log.debug('report building finished')
        with open(filename, 'w') as f:
            f.write(report.to_html())

    def default_traits_view(self):
        return View(
            Item('series',
                 show_label=False,
                 editor=report_series_editor,
                 visible_when='len(series) > 0'),
            Item('save',
                 label='Save',
                 show_label=False),
            resizable=True)
    

class CombineForm722ReportDialog(HasTraits):
    observer = Enum(values='_observer_values')
    _observer_values = Property()
    adc_series_num = Enum(values='series_numbers')
    r2s_pre_series_num = Enum(values='series_numbers')
    r2s_post_series_num = Enum(values='series_numbers')
    series_numbers = Property
    save = Button
    report_file = File

    def _get__observer_values(self):
        observers = []
        for rs in self._input_series:
            series = rs.series
            tags = [tag for (tag,) in series.first.meta.roi.groupby('tag').keys()]
            observers.extend(tags)
        return unique(observers)

    def _get_series_numbers(self):
        return [s.series_number for s in self._input_series] + [None]

    def __init__(self, series):
        assert len(series) >= 2
        self._input_series = [ReportSeries.from_dicom_series(s) for s in series]
        nums = [s.series_number for s in self._input_series]

        def get(x, n):
            if len(x) <= n:
                return None
            else:
                return x[n]

        super(CombineForm722ReportDialog, self).__init__(
            adc_series_num=get(nums, 0),
            r2s_pre_series_num=get(nums, 1),
            r2s_post_series_num=get(nums, 2),
            report_file='combine-form722-report.html')
    
    def _save_fired(self):
        log.info('report building started')
        filename = qt_save_file(file_name=self.report_file, filters='html (*.html)')
        if not filename:
            return
        self.report_file = filename
        dcms = jtmri.dcm.DicomSet(flatten(rs.series for rs in self._input_series))
        report = CombineForm722Report(dcms, self.observer)
        log.info('adding adc series {}'.format(self.adc_series_num))
        log.info('adding r2s pre series {}'.format(self.r2s_pre_series_num))
        log.info('adding r2s post series {}'.format(self.r2s_post_series_num))
        report.set_series(self.adc_series_num, self.r2s_pre_series_num, self.r2s_post_series_num)
        log.debug('report building finished')
        with open(filename, 'w') as f:
            f.write(report.to_html())

    def default_traits_view(self):
        return View(
            Item('observer'),
            Item('adc_series_num', label='ADC'), 
            Item('r2s_pre_series_num', label='R2* Pre'), 
            Item('r2s_post_series_num', label='R2* Post'), 
            Item('save',
                 label='Save',
                 show_label=False),
            resizable=True)
