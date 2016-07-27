from traits.api import Any, Str, Button
from traitsui.file_dialog import OpenFileDialog, FileExistsHandler
from traitsui.api import (View, VGroup, HGroup, Item,
        ImageEditor, spring, Handler)

import os
import logging


from PySide import QtGui


log = logging.getLogger('file_dialog')


class FixedFileExistsHandler(FileExistsHandler):
    zzParent = Any
    view = View(
            VGroup(
                HGroup(
                    Item( 'handler.message',
                        editor = ImageEditor( image = '@icons:dialog-warning' )
                        ),
                    Item( 'handler.message', style = 'readonly' ),
                    show_labels = False
                    ),
                HGroup(
                    spring,
                    Item( 'handler.ok' ),
                    Item( 'handler.cancel' ),
                    show_labels = False
                    )
                ),
            kind = 'modal')

    def handler_ok_changed ( self, info ):
        """ Handles the user clicking the OK button.
        """
        info.ui.dispose( True )
        self.zzParent.dispose(True)


class FixedOpenFileDialog(OpenFileDialog):
    def _file_already_exists (self ):
        """ Handles prompting the user when the selected file already exists,
            and the dialog is a 'save file' dialog.
        """
        FixedFileExistsHandler( message = ("The file '%s' already exists.\nDo "
                                      "you wish to overwrite it?") %
                                      os.path.basename( self.file_name ),
                                zzParent = self.info.ui
            ).edit_traits( context = self,
                           parent  = self.info.ok.control ).set(
                           parent  = self.info.ui )


def traits_save_file(file_name):
    """ Returns a file name to save to or an empty string if the user cancels
        the operation. In the case where the file selected already exists, the
        user will be prompted if they want to overwrite the file before the
        selected file name is returned.
    """
    log.info('save_file: {}'.format(traits))
    traits.setdefault( 'title', 'Save File' )
    traits[ 'is_save_file' ] = True
    fd = FixedOpenFileDialog(file_name=file_name)
    if fd.edit_traits( view = 'open_file_view' ).result:
        return fd.file_name
    return ''


def traits_open_file(file_name):
    """ Returns a file name to open or an empty string if the user cancels the
        operation.
    """
    fd = OpenFileDialog(file_name=filename)
    if fd.edit_traits(view = 'open_file_view').result:
        return fd.file_name
    return ''


def qt_save_file(file_name, filters=None):
    filename, _ =  QtGui.QFileDialog.getSaveFileName(None, 'Save File',
                                                     file_name, filters)
    return filename


def qt_open_file(file_name, filters=None):
    filename, _ = QtGui.QFileDialog.getOpenFileName(None, 'Open File',
                                                    file_name, filters)
    return filename
