from PySide.QtGui import QPen,QBrush,QColor
from PySide.QtCore import Qt

def default_roi_pen(dashed=True,color=Qt.green):
    pen = QPen()
    if dashed:
        pen.setStyle(Qt.DashLine)
    pen.setBrush(color)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen

def default_roi_brush(alpha=50):
    return QBrush(QColor(0,255,0,alpha))

