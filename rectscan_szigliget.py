from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtSvg import QSvgGenerator
import threading


class GraphicsViewport(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def wheelEvent(self, event):
        zoomSpeed = 0.001
        if event.pixelDelta().y() > 0:
            zoomFactor = 1+event.pixelDelta().y()*zoomSpeed
            self.scale(zoomFactor, zoomFactor)
        else:
            zoomFactor = 1+event.pixelDelta().y()*zoomSpeed
            self.scale(zoomFactor, zoomFactor)


class BaseWindow(QSplitter):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # settings
        self.settings = QSettings("ablakok.ini", QSettings.IniFormat)

        # viewport
        self.view = GraphicsViewport()
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy ( Qt.ScrollBarAlwaysOff )
        self.view.setVerticalScrollBarPolicy ( Qt.ScrollBarAlwaysOff )
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        # inspector
        self.inspector = QWidget()
        self.inspector.setLayout(QVBoxLayout())

        # layout
        self.addWidget(self.inspector)
        self.addWidget(self.view)
        self.setStretchFactor(0,0)
        self.setStretchFactor(1,1)

        # attributes dictionary
        self._attributes = {}

    def sizeHint(self):
        return QSize(1024, 768)

    def addAttribute(self, name):
        # add ui for an attribute
        slider = self.addSlider(name, defaultValue=self.settings.value(name, 50))
        def updateSettings(value, name=name):
            self.settings.setValue(name, value)
            self.settings.sync()

        slider.valueChanged.connect(updateSettings)
        self._attributes[name] = {'slider': slider}
        return slider

    def addSlider(self, name, defaultValue=None):
        print("add slider:", name, defaultValue)
        label = QLabel("{} {}".format(name, defaultValue))
        slider = QSlider(orientation=Qt.Horizontal, maximum=1000)
        slider.setTracking(True)

        if defaultValue:
            slider.setValue(int(defaultValue))

        def syncLabel(value):
            label.setText("{} {}".format(name, value))

        slider.valueChanged.connect(syncLabel)

        widget = QWidget()
        widget.setLayout(QHBoxLayout())
        widget.layout().addWidget(slider)
        widget.layout().addWidget(label)
        self.inspector.layout().addWidget(widget)
        return slider


class Window(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # attributes
        self.addAttribute('length').valueChanged.connect(self.updateRectangles)
        self.addAttribute('count').valueChanged.connect(self.updateRectangles)
        self.addAttribute('k').valueChanged.connect(self.updateRectangles)
        self.addAttribute('horizont').valueChanged.connect(self.updateRectangles)

        # actions
        self.exportButton = QPushButton("export")
        self.exportButton.clicked.connect(self.export)
        self.inspector.layout().addWidget(self.exportButton)

        self.packButton = QPushButton("pack")
        self.packButton.clicked.connect(self.pack)
        self.inspector.layout().addWidget(self.packButton)

        #
        self.rectangles = []
        self.baseRect = QRectF(0,0, 210, 297) #A4
        self.binRect = QRectF(0,0, 420*2, 594*2) #A2
        self.pen = QPen(
            QBrush(QColor(0,0,0)),
            0.1, # width,
            Qt.SolidLine,
            Qt.SquareCap,
            Qt.RoundJoin
            )

        # init rectangles
        self.updateRectangles()

    @property
    def count(self):
        return self._attributes['count']['slider'].value()

    @property
    def length(self):
        return self._attributes['length']['slider'].value()

    @property
    def k(self):
        return self._attributes['k']['slider'].value()

    @property
    def horizont(self):
        return self._attributes['horizont']['slider'].value() / 1000

    def updateRectangles(self):
        # calc persp rectangles
        def scaledRect(rect, factor, center=(0.5, 0.5)):
            # 
            left, top, width, height = rect.top(), rect.left(), rect.width(), rect.height()

            center = QPointF( rect.topLeft() + QPointF(rect.size().width() * center[0], rect.size().height()*center[1]) )
            left = (left - center.x() ) * factor + center.x()
            top =  (top -  center.y() ) * factor + center.y()
            width = width * factor
            height = height * factor
            
            return QRectF(left, top, width, height)

        try:
            scales = [1/(1+distance/self.count*self.length/self.k) for distance in range(self.count)]
            self.rectangles = [(scaledRect(self.baseRect, scale, center=(0.5, self.horizont))) for scale in scales]
            self.scene.clear()
            for rect in self.rectangles:
                rectItem = QGraphicsRectItem(rect)
                rectItem.setPen(self.pen)
                self.scene.addItem(rectItem)

        except ZeroDivisionError:
            self.scene.clear()

    def pack(self):
        import rectpack
        packer = rectpack.newPacker(rotation=False)

        # Add the rectangles to packing queue
        for rect in self.rectangles:
            packer.add_rect( rect.width(), rect.height() )

        # Add the bins where the rectangles will be placed
        packer.add_bin(self.binRect.width(), self.binRect.height())

        # Start packing
        packer.pack()

        # add to scene
        self.scene.clear()
        nbins = len(packer)
        print(nbins)
        for b in packer:
            binItem = QGraphicsRectItem(0,0,b.width, b.height)
            binItem.setPen(QColor(255,0,0))
            self.scene.addItem(binItem)
            for r in packer[0]:
                rectItem = QGraphicsRectItem(r.x, r.y, r.width, r.height)
                # rectItem.setPen(self.pen)
                # rectItem.setBrush(QColor(128, 128, 128, 10))
                self.scene.addItem(rectItem)

    def export(self):
        filename = "test.svg"
        generator = QSvgGenerator()
        generator.setFileName(filename)
        #

        generator.setDescription("paper: A4mm count: {} length:{} k:{} horizont: {}".format(self.count, self.length, self.k, self.horizont))
        generator.setSize(QSize(400, 400))
        generator.setViewBox(QRect(0, 0, 400, 400))
        painter = QPainter()
        painter.begin(generator)
        self.scene.render(painter)
        painter.end()

        import subprocess
        subprocess.run(['open', filename], check=True)

if __name__ == "__main__":
    import sys, os
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec()
    os._exit(0)

