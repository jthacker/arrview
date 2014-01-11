from traits.api import Any, Str, Button
from traitsui.file_dialog import OpenFileDialog, FileExistsHandler
from traitsui.api import (View, VGroup, HGroup, Item, 
        ImageEditor, spring, Handler)

import os

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

def save_file ( **traits ):
    """ Returns a file name to save to or an empty string if the user cancels
        the operation. In the case where the file selected already exists, the
        user will be prompted if they want to overwrite the file before the
        selected file name is returned.
    """
    traits.setdefault( 'title', 'Save File' )
    traits[ 'is_save_file' ] = True
    fd = FixedOpenFileDialog( **traits )
    if fd.edit_traits( view = 'open_file_view' ).result:
        return fd.file_name

    return ''

def open_file ( **traits ):
    """ Returns a file name to open or an empty string if the user cancels the
        operation.
    """
    fd = OpenFileDialog( **traits )
    if fd.edit_traits( view = 'open_file_view' ).result:
        return fd.file_name

    return ''
