from PySide.QtCore import Qt, Signal, QObject, QTimer
from PySide.QtGui import (QSlider, QStyleOptionSlider, QStyle, QAbstractSlider, 
        QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QSizePolicy)

class ContinuousSlider(QSlider):
    '''Allow the user to click near a tick mark and have the slider 
    jump to that position. The usual action results in the slider 
    moving one tick in the direction of the cursor.'''
    def __init__(self, *args, **kwargs):
        super(ContinuousSlider, self).__init__(*args, **kwargs)
        self.actionTriggered.connect(self.stepped)

    def stepped(self, action):
        if action == QAbstractSlider.SliderSingleStepAdd:
            if self.value() + 1 > self.maximum():
                self.setValue(self.minimum())

        elif action == QAbstractSlider.SliderSingleStepSub:
            if self.value() - 1 < self.minimum():
                self.setValue(self.maximum())
 
    def setValue(self, val):
        if val > self.maximum():
            val = self.minimum()
        if val < self.minimum():
            val = self.maximum()
        signalsBlocked = self.blockSignals(True)
        super(ContinuousSlider, self).setValue(val)
        self.blockSignals(signalsBlocked)

    def mousePressEvent(self, event):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        sr = self.style().subControlRect(QStyle.CC_Slider, 
                opt, QStyle.SC_SliderHandle, self)
        
        if event.button() == Qt.LeftButton and not sr.contains(event.pos()):
            rng = self.maximum() - self.minimum()
            h,w = self.height(),self.width()
            x,y = event.x(), event.y()

            if self.orientation() == Qt.Vertical:
                normPos = float(h-y) / h 
            else: 
                normPos = float(x) / w

            newVal = self.minimum() + (rng * normPos)

            if self.invertedAppearance():
                newVal = self.maximum() - newVal
          
            self.setValue(round(newVal))
            event.accept()
        else:
            super(ContinuousSlider, self).mousePressEvent(event)


class PlayableSlider(QWidget):
    '''Unlike the usual valueChanged signal in QSlider, value_changed here is only
    emitted when the user edits the value. Calling set_value will not emit this signal'''
    value_changed = Signal(int)
    
    def __init__(self, orientation=Qt.Horizontal):
        super(PlayableSlider, self).__init__()
        if orientation == Qt.Horizontal:
            self.setLayout(QHBoxLayout())
        else:
            self.setLayout(QVBoxLayout())
        
        self.playIcon = self.style().standardIcon(QStyle.SP_MediaPlay)
        self.pauseIcon = self.style().standardIcon(QStyle.SP_MediaPause)
        self.playbutton = QPushButton()
        self.playbutton.setIcon(self.playIcon)

        self.slider = ContinuousSlider(orientation)
        self.slider.setPageStep(1)
        self.slider.valueChanged.connect(self._value_changed)
        self.layout().addWidget(self.slider, 1)

        self.lineedit = QLineEdit()
        self.lineedit.setDisabled(True)
        self.lineedit.setFixedWidth(50)
        self.lineedit.setAlignment(Qt.AlignRight)
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().addWidget(self.lineedit, 0)
        self.layout().addWidget(self.playbutton, 0)

    def set_playing(self, is_playing):
        if is_playing:
            self.playbutton.setIcon(self.pauseIcon)
        else:
            self.playbutton.setIcon(self.playIcon)

    def set_range(self, low, high):
        self.slider.setRange(low, high)

    def set_value(self, val):
        self.slider.setValue(val)
        self.lineedit.setText(str(val))

    def _value_changed(self, val):
        self.lineedit.setText(str(val))
        self.value_changed.emit(val)


class SliderIntegerEditor(QObject):
    value_changed = Signal(int)
    
    def __init__(self, value, low, high):
        super(SliderIntegerEditor, self).__init__()
        self.widget = PlayableSlider()
        self.widget.set_range(low, high)
        self.widget.value_changed.connect(self._ui_value_changed)
        self.widget.playbutton.clicked.connect(self._play_clicked)
        self._low = low
        self._high = high
        self._value = value
        self._playing = False
        self._timer = QTimer()
        self._timer.timeout.connect(self._increment)

    def _play_clicked(self):
        if self._playing:
            self.widget.set_playing(False)
            self._playing = False
            self._timer.stop()
        else:
            self.widget.set_playing(True)
            self._playing = True
            self._timer.start(50)

    def _increment(self):
        if self.value + 1 > self.high:
            self.value = 0
        else:
            self.value += 1

    def _ui_value_changed(self, value):
        self.value = value

    def setEnabled(self, enabled):
        self.widget.setEnabled(enabled)

    @property
    def low(self):
        return self._low

    @low.setter
    def low(self, low):
        self.range = low,self.high

    @property
    def high(self):
        return self._high

    @high.setter
    def high(self, high):
        self.range = self.low,high

    @property
    def range(self):
        return self.low,self.high

    @range.setter
    def range(self, rng):
        low,high = rng
        self._low = low
        self._high = high
        self.widget.set_range(low, self.high)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.low <= value <= self.high:
            self._value = value
            self.widget.set_value(value)
            self.value_changed.emit(value)
        else:
            raise ValueError('value must satisy low <= value <= high')


if __name__ == '__main__':
    import sys, random
    from PySide.QtCore import QTimer
    from PySide.QtGui import QApplication, QMainWindow
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    def debug(name, val):
        print(name, 'value changed', val)

    editor = SliderIntegerEditor(50, 0, 100)
    editor.value_changed.connect(debug)

    p = QWidget()
    p.setLayout(QVBoxLayout())

    editors = []
    for i in range(10):
        editor = SliderIntegerEditor(50, 0, 100)
        editor.value_changed.connect(lambda v,i=i: debug('editor %d' % i, v))
        p.layout().addWidget(editor.widget)
        editors.append(editor)

    win = QMainWindow()
    win.setCentralWidget(p)
    win.setVisible(True)

    sys.exit(app.exec_())