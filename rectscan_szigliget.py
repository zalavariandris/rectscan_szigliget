from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtSvg import QSvgGenerator
import threading

# WIDGETS
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


class SliderLabel(QWidget):
    valueChanged = pyqtSignal(int)
    def __init__(self, text, value=None, parent=None):
        super().__init__(parent=parent)
        self.text = text
        self.slider = QSlider(orientation=Qt.Horizontal, maximum=100)
        self.slider.setTracking(True)

        if value:
            self.slider.setValue(int(value))

        self.label = QLabel("{} {}".format(text, self.value()))

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.slider)
        self.layout().addWidget(self.label)

        self.slider.valueChanged.connect(lambda val: self.valueChanged.emit(val))
        self.valueChanged.connect(self.updateLabel)

    def value(self):
        return self.slider.value()

    def updateLabel(self):
        self.label.setText("{} {}".format(self.text, self.value()))

    def setValue(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)


# BASE WINDOW with Inspector
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

    def sizeHint(self):
        return QSize(1024, 768)


# GRAPHICS ITEMS
class QGraphicsLayerItem(QGraphicsItem):
    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        pass


class CorridorItem(QGraphicsRectItem):
    def __init__(self, parent=None):
        super().__init__()

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        self._length = value
        self.update()

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, value):
        self._count = value
        self.update()

    @property
    def k(self):
        return self._k

    @k.setter
    def k(self, value):
        self._k = value
        self.update()

    @property
    def horizont(self):
        return self._horizont

    @horizont.setter
    def horizont(self, value):
        self._horizont = value
        self.update()

    def doors(self):
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
            return [(scaledRect(self.rect(), scale, center=(0.5, self.horizont))) for scale in scales]
        except ZeroDivisionError:
            return []

    def paint(self, painter, option, widget):
        # draw base rect
        painter.drawRect(self.rect())

        for door in self.doors():
            painter.drawRect(door)


class PaperItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        self.setBrush(QColor(255,255,255))
        self.setPen(QPen(Qt.NoPen))
        self.setZValue(-1)


# MAIN APP WINDOW
class Window(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.corridorItem = CorridorItem()
        self.corridorItem.setRect(0,0, 210, 297)
        self.corridorItem.length = int(self.settings.value('length', 50))
        self.corridorItem.count = int(self.settings.value('count', 50))
        self.corridorItem.k = int(self.settings.value('k', 50))
        self.corridorItem.horizont = int(self.settings.value('horizont', 50))/100

        self.paperItem = PaperItem(0,0, 840, 1188) #A1
        self.scene.addItem(self.paperItem)

        # bind sliders to corridorItem
        def updateItemLength(val):
            self.corridorItem.length = val
            self.settings.setValue('length', val)
            self.settings.sync()
        self.lengthSlider = SliderLabel("length")
        self.lengthSlider.setValue(self.corridorItem.length)
        self.lengthSlider.valueChanged.connect(updateItemLength)
        self.inspector.layout().addWidget(self.lengthSlider)

        def updateItemCount(val):
            self.corridorItem.count = val*10
            self.settings.setValue('count', val)
            self.settings.sync()
        self.countSlider = SliderLabel('count')
        self.countSlider.setValue(self.corridorItem.count/10)
        self.countSlider.valueChanged.connect(updateItemCount)
        self.inspector.layout().addWidget(self.countSlider)

        def updateItemK(val):
            self.corridorItem.k = val
            self.settings.setValue('k', val)
            self.settings.sync()
        self.kSlider = SliderLabel('k')
        self.kSlider.setValue(self.corridorItem.k)
        self.kSlider.valueChanged.connect(updateItemK)
        self.inspector.layout().addWidget(self.kSlider)

        def updateItemHorizont(val):
            self.corridorItem.horizont = val/100
            self.settings.setValue('horizont', val)
            self.settings.sync()
        self.horizontSlider = SliderLabel('horizont')
        self.horizontSlider.setValue(self.corridorItem.horizont*100)
        self.horizontSlider.valueChanged.connect(updateItemHorizont)
        self.inspector.layout().addWidget(self.horizontSlider)

        # paper UI
        self.inspector.layout().addWidget(QLabel('paper'))
        paper_selector = QComboBox()
        paper_selector.addItem("A1")
        paper_selector.addItem("A2")
        paper_selector.addItem("A3")
        paper_selector.addItem("A4")
        paper_selector.addItem("A5")
        self.inspector.layout().addWidget(paper_selector)

        # actions
        self.exportButton = QPushButton("export")
        self.exportButton.clicked.connect(self.export)
        self.inspector.layout().addWidget(self.exportButton)

        self.packButton = QPushButton("pack")
        self.packButton.clicked.connect(self.pack)
        self.inspector.layout().addWidget(self.packButton)

        def update_paper(i):
            paper = paper_selector.itemText(i)
            print("update paper item size", paper)
            if paper == "A1":
                self.paperItem.setRect(0,0, 840, 1188)
            elif paper == "A2":
                self.paperItem.setRect(0,0, 420, 594)
            if paper == "A3":
                self.paperItem.setRect(0,0, 297, 420)
            elif paper == "A4":
                self.paperItem.setRect(0,0, 210, 297)
            elif paper == "A5":
                self.paperItem.setRect(0,0, 148, 210)

        paper_selector.currentIndexChanged.connect(update_paper)
        self.scene.addItem(self.corridorItem)

    def pack(self):
        import rectpack
        packer = rectpack.newPacker(rotation=False)

        # Add the rectangles to packing queue
        for rect in self.corridorItem.doors():
            packer.add_rect( rect.width(), rect.height() )

        # Add the bins where the doors will be placed
        packer.add_bin(self.paperItem.rect().width(), self.paperItem.rect().height())

        # Start packing
        packer.pack()

        # clear rectangles:
        if not hasattr(self, 'rectangles_layer'):
            self.rectangles_layer = QGraphicsLayerItem()
            self.scene.addItem(self.rectangles_layer)

        for child in self.rectangles_layer.childItems():
            self.scene.removeItem(child)

        # add packed rectangles
        nbins = len(packer)
        print("number of bins:", nbins)
        for b in packer:
            for r in packer[0]:
                rectItem = QGraphicsRectItem(r.x, r.y, r.width, r.height)
                rectItem.setParentItem(self.rectangles_layer)

    def export(self):
        filename = "test.svg"

        generator = QSvgGenerator()
        generator.setFileName(filename)
        generator.setDescription("paper: A4mm count: {} length:{} k:{} horizont: {}".format(self.corridorItem.count, self.corridorItem.length, self.corridorItem.k, self.corridorItem.horizont))
        generator.setSize(QSize(400, 400))
        generator.setViewBox(QRect(0, 0, 400, 400))

        painter = QPainter()
        painter.begin(generator)
        self.scene.render(painter)
        painter.end()

        try:
            import subprocess
            subprocess.run(['open', filename], check=True)
        except FileNotFoundError as err:
            print(err)

if __name__ == "__main__":
    import sys, os
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec()
    os._exit(0)

