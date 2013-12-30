from PySide.QtGui import QGraphicsView

class ImageTool(object):
    name = 'None'

    def init(self, graphicsView):
        pass

    def destroy(self):
        pass

    def mouse_pressed(self, mouse):
        pass

    def mouse_moved(self, mouse):
        pass

    def mouse_wheeled(self, mouse):
        pass


class DrawROITool(ImageTool):
    name = 'Draw ROI'


class PanAndZoomTool(ImageTool):
    name = 'Pan/Zoom'

    def init(self, graphicsView):
        graphicsView.setDragMode(QGraphicsView.ScrollHandDrag)
        graphicsView.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.graphicsView = graphicsView
        self.currentScale = 1

    def destroy(self):
        self.graphicsView.setDragMode(QGraphicsView.NoDrag)

    def mouse_wheeled(self, mouse):
        zoomIn = mouse.delta < 0
        s = 1.2 if zoomIn else 1/1.2
        lessThanMax = zoomIn and self.currentScale < 20
        greaterThanMin = not zoomIn and self.currentScale > 0.1
        if lessThanMax or greaterThanMin:
            self.graphicsView.scale(s,s)
            self.currentScale *= s 

tools = [PanAndZoomTool, DrawROITool]
