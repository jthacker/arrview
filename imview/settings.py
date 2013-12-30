from PySide.QtGui import QPen,QBrush,QColor
from PySide.QtCore import Qt

def default_roi_pen():
    pen = QPen()
    pen.setStyle(Qt.DashLine)
    pen.setBrush(Qt.green)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen

def default_roi_brush():
    return QBrush(QColor(0,255,0,100))

