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

        for gesture in [Qt.TapGesture, Qt.TapAndHoldGesture, Qt.PanGesture, Qt.PinchGesture, Qt.SwipeGesture, Qt.CustomGesture]:
            self.grabGesture(gesture)

        self.setBackgroundBrush(QBrush(QColor(240, 240, 240), Qt.SolidPattern));

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event):
        pinch = event.gesture(Qt.PinchGesture)
        if pinch:
            changeFlags = pinch.changeFlags()
            if changeFlags & QPinchGesture.ScaleFactorChanged:
                self.scale(pinch.scaleFactor(), pinch.scaleFactor())
        return True

    def wheelEvent(self, event):
        zoomSpeed = 0.001
        delta = event.angleDelta().y() # consider implementing pixelDelta for macs
        if delta > 0:
            zoomFactor = 1+delta*zoomSpeed
            self.scale(zoomFactor, zoomFactor)
        else:
            zoomFactor = 1+delta*zoomSpeed
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


class QGraphicsLayerItem(QGraphicsItem):
    pass

class Window(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.rectangles = []
        self.baseRect = QRectF(0,0, 210, 297) #A4
        self.page_rect = QRectF(0,0, 420*2, 594*2) #A2
        self.pen = QPen(
            QBrush(QColor(0,0,0)),
            0.1, # width,
            Qt.SolidLine,
            Qt.SquareCap,
            Qt.RoundJoin
            )

        # page setup

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
        self.rectangles_layer = QGraphicsLayerItem()
        self.scene.addItem(self.rectangles_layer)

        # page
        page_selector = QComboBox()
        page_selector.addItem("A2")
        page_selector.addItem("A3")
        page_selector.addItem("A4")
        page_selector.addItem("A5")
        self.inspector.layout().addWidget(page_selector)
        pageItem = QGraphicsRectItem(self.page_rect)
        pageItem.setBrush(QColor(255,255,255))
        pageItem.setPen(QPen(Qt.NoPen))
        pageItem.setZValue(-1)
        self.scene.addItem(pageItem)

        def update_page(i):
            page = page_selector.itemText(i)
            print("update page item size", page)
            if page == "A2":
                self.page_rect = QRectF(0,0, 420, 594)
            if page == "A3":
                self.page_rect = QRectF(0,0, 297, 420)
            elif page == "A4":
                self.page_rect = QRectF(0,0, 210, 297)
            elif page == "A5":
                self.page_rect = QRectF(0,0, 148, 210)

            pageItem.setRect(self.page_rect)
        page_selector.currentIndexChanged.connect(update_page)

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

            # clear rectangles:
            for child in self.rectangles_layer.childItems():
                self.scene.removeItem(child)

            for rect in self.rectangles:
                rectItem = QGraphicsRectItem(rect)
                rectItem.setPen(self.pen)
                rectItem.setParentItem(self.rectangles_layer)

        except ZeroDivisionError:
            self.scene.clear()

    def pack(self):
        import rectpack
        packer = rectpack.newPacker(rotation=False)

        # Add the rectangles to packing queue
        for rect in self.rectangles:
            packer.add_rect( rect.width(), rect.height() )

        # Add the bins where the rectangles will be placed
        packer.add_bin(self.page_rect.width(), self.page_rect.height())

        # Start packing
        packer.pack()

        # clear rectangles:
        for child in self.rectangles_layer.childItems():
            self.scene.removeItem(child)

        # add packed rectangles
        nbins = len(packer)
        print(nbins)
        for b in packer:
            for r in packer[0]:
                rectItem = QGraphicsRectItem(r.x, r.y, r.width, r.height)
                # rectItem.setPen(self.pen)
                # rectItem.setBrush(QColor(128, 128, 128, 10))
                rectItem.setParentItem(self.rectangles_layer)

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

