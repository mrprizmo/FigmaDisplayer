import sys
import requests
from PyQt5 import uic
from typing import Any
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPolygonF
from PyQt5.QtCore import Qt, QEvent, QRect, QPointF
from PyQt5.QtWidgets import QApplication, QMainWindow


class FigmaDisplayer(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.unitUI()
        self.btn_apply.clicked.connect(self.make_request)

    def unitUI(self) -> None:
        uic.loadUi("UI\\mainwindow.ui", self)
        self.setFixedSize(self.size())
        self.width, self.height = self.canvas.size().width(), self.canvas.size().height()
        self.pixmap = QPixmap(self.width, self.height)
        self.canvas.setPixmap(self.pixmap)
        self.need_to_update = 1
        self.offset_x = self.offset_y = self.scale = 0
        self.response = []
        self.update()

    def paintEvent(self, event: QEvent) -> None:
        if self.need_to_update:
            qp = QPainter()
            qp.begin(self.pixmap)
            self.pixmap.fill(Qt.white)
            if not self.response:
                qp.drawText(QRect(0, 0, self.width, self.height), Qt.AlignCenter, "No objects")
            for obj in self.response:
                x, y = (obj['absoluteBoundingBox']['x'] - self.offset_x) * self.scale, (obj['absoluteBoundingBox']['y'] - self.offset_y) * self.scale
                width, height = obj['absoluteBoundingBox']['width'] * self.scale, obj['absoluteBoundingBox']['height'] * self.scale
                box = QRect(x, y, width, height)
                color = QColor(obj['fills'][0]['color']['r'] * 255, obj['fills'][0]['color']['g'] * 255,
                               obj['fills'][0]['color']['b'] * 255)
                brush = QBrush(color, Qt.SolidPattern)
                qp.setBrush(brush)

                if obj['shapeType'] == "ELLIPSE":
                    qp.drawEllipse(box)
                elif obj['shapeType'] == "SQUARE" or obj['shapeType'] == "ROUNDED_RECTANGLE":
                    qp.drawRoundedRect(box, 15, 15)
                elif obj['shapeType'] == "TRIANGLE_DOWN":
                    points = (QPointF(x, y), QPointF(x + width, y), QPointF((x + width) // 2, y + height))
                    qp.drawPolygon(QPolygonF(points))
                elif obj['shapeType'] == "PARALLELOGRAM_RIGHT":
                    points = (
                        QPointF(x + width // 5, y), QPointF(x + width, y), QPointF(x + 4 * width // 5, y + height),
                        QPointF(x, y + height)
                    )
                    qp.drawPolygon(QPolygonF(points))
                elif obj['shapeType'] == "PARALLELOGRAM_LEFT":
                    points = (
                        QPointF(x, y), QPointF(x + 4 * width // 5, y), QPointF(x + width, y + height),
                        QPointF(x + width // 5, y + height)
                    )
                    qp.drawPolygon(QPolygonF(points))
                qp.drawText(box, Qt.AlignCenter, obj['characters'])

            qp.end()
            self.canvas.setPixmap(self.pixmap)
            self.need_to_update = 0

    def make_request(self) -> None:
        header = {}
        request = 'https://api.figma.com/v1/files/{}'
        header['X-FIGMA-TOKEN'] = self.line_access_token.text().strip()
        header['Content-Type'] = 'application/json'
        response = requests.get(request.format(self.line_project_name.text().strip()), headers=header)
        if response:
            self.need_to_update = 1
            try:
                response = response.json()['document']['children'][0]['children']
                self.response = []
                x = []
                y = []
                for obj in response:
                    if obj['type'] == "SHAPE_WITH_TEXT":
                        self.response.append(obj)
                        x.append(obj['absoluteBoundingBox']['x'])
                        y.append(obj['absoluteBoundingBox']['y'])
                        x.append(obj['absoluteBoundingBox']['x'] + obj['absoluteBoundingBox']['width'])
                        y.append(obj['absoluteBoundingBox']['y'] + obj['absoluteBoundingBox']['height'])
                self.offset_x = min(x)
                self.offset_y = min(y)
                self.scale = min(self.width / (max(x) - self.offset_x), self.height / (max(y) - self.offset_y))
            except BaseException:
                pass


def except_hook(cls: Any, exception: Any, traceback: Any) -> None:
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FigmaDisplayer()
    ex.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())