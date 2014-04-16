from PySide.QtGui import (QApplication, QGraphicsView, QGraphicsScene,
                          QMainWindow, QPixmap, QPainter)
from PySide.QtCore import Qt
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    view.scale(15, 15)

    pix = QPixmap(200, 50)
    pix.fill(Qt.white)
    p = QPainter(pix)
    p.setPen(Qt.black)
    #p.setBrush(Qt.red)
    for i in range(1, 10):
        p.drawEllipse(0, 0, i, i)
        p.translate(i+5, 0)
    p.end()
    pixItem = scene.addPixmap(pix)

    win = QMainWindow()
    win.setCentralWidget(view)
    win.resize(700, 200)
    win.show()

    sys.exit(app.exec_())
