from PySide.QtCore import Qt
from PySide.QtGui import QSlider, QStyleOptionSlider, QStyle, QAbstractSlider, QWidget, QHBoxLayout, QPushButton

class Slider(QSlider):
    '''Allow the user to click near a tick mark and have the slider 
    jump to that position. The usual action results in the slider 
    moving one tick in the direction of the cursor.'''
    def __init__(self, *args, **kwargs):
        super(Slider, self).__init__(*args, **kwargs)
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
        super(Slider, self).setValue(val)

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
            super(Slider, self).mousePressEvent(event)


class PlayableSlider(QWidget):
    def __init__(self, *args, **kwargs):
        super(PlayableSlider, self).__init__(*args, **kwargs)
        self.setLayout(QHBoxLayout())

        self.playIcon = self.style().standardIcon(QStyle.SP_MediaPlay)
        self.pauseIcon = self.style().standardIcon(QStyle.SP_MediaPause)
        self.playbutton = QPushButton()
        self.playbutton.setIcon(self.playIcon)
        self.layout().addWidget(self.playbutton)

        self.slider = Slider(Qt.Horizontal)
        self.slider.setPageStep(1)
        self.slider.setTickPosition(QSlider.TicksAbove)
        self.layout().addWidget(self.slider)

    def set_slider_range(self, low, high):
        self.slider.setRange(low, high)

    def set_slider_value(self, val):
        self.slider.setValue(val)



if __name__ == '__main__':
    import sys
    from PySide.QtGui import QApplication, QMainWindow
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    def debug(val):
        print('value changed', val)

    slider = Slider(Qt.Horizontal)
    slider.setMinimum(0)
    slider.setMaximum(100)
    slider.valueChanged.connect(debug)
    slider.setTickPosition(QSlider.TicksBelow)

    win = QMainWindow()
    win.setCentralWidget(slider)
    win.setVisible(True)

    sys.exit(app.exec_())
