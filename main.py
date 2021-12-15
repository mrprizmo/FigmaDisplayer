import sys
from logging.config import dictConfig
from math import ceil
import logging
import requests
from PyQt5 import uic
from typing import Any
from PyQt5.QtCore import Qt, QEvent, QRect, QPointF
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPolygonF, QPen, QPainterPath, QFont

dictLogConfig = {
        'version': 1,
        "handlers": {
            "fileHandler": {
                "class": "logging.FileHandler",
                "formatter": "standard",
                "filename": "logging.log",
                "mode": 'w+'
            }
        },
        "loggers": {
            "Displayer": {
                "handlers": ["fileHandler"],
                "level": "INFO",
            }
        },
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    }

dictConfig(dictLogConfig)
log = logging.getLogger("Displayer")


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
        self.offset_x = self.offset_y = 0
        self.scale = 1
        self.eps = 20
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
                try:
                    x, y = (obj['absoluteBoundingBox']['x'] - self.offset_x) * self.scale, (
                            obj['absoluteBoundingBox']['y'] - self.offset_y) * self.scale
                    width, height = obj['absoluteBoundingBox']['width'] * self.scale, obj['absoluteBoundingBox'][
                        'height'] * self.scale
                    box = QRect(x, y, width, height)
                    color = QColor(obj['fills'][0]['color']['r'] * 255, obj['fills'][0]['color']['g'] * 255,
                                   obj['fills'][0]['color']['b'] * 255, obj['fills'][0]['color']['a'] * 255)

                    if obj['type'] == "RECTANGLE":
                        qp.setBrush(QBrush(color, Qt.SolidPattern))
                        qp.setPen(QPen(color, 1, Qt.SolidLine))
                        if obj.get('shapeType'):
                            if obj['shapeType'] == "ROUNDED_RECTANGLE":
                                qp.drawRoundedRect(box, 15, 15)
                        else:
                            qp.drawRect(box)
                        """
                        roundedpath = QPainterPath()
                        roundedpath.setFillRule(Qt.WindingFill)
                        roundedpath.addEllipse(box)
                        roundedpath.addRoundedRect(x, y + height // 2, width // 2, height // 2, ???)
                        """

                    elif obj['type'] == "SHAPE_WITH_TEXT":
                        qp.setBrush(QBrush(color, Qt.SolidPattern))
                        qp.setPen(QPen(color, 1, Qt.SolidLine))
                        if obj['shapeType'] == "ELLIPSE":
                            qp.drawEllipse(box)
                        elif obj['shapeType'] == "SQUARE" or obj['shapeType'] == "ROUNDED_RECTANGLE":
                            qp.drawRoundedRect(box, 15, 15)
                        elif obj['shapeType'] == "TRIANGLE_DOWN":
                            points = (QPointF(x, y), QPointF(x + width, y), QPointF(x + width // 2, y + height))
                            qp.drawPolygon(QPolygonF(points))
                        elif obj['shapeType'] == "PARALLELOGRAM_RIGHT":
                            points = (
                                QPointF(x + width // 5, y), QPointF(x + width, y),
                                QPointF(x + 4 * width // 5, y + height),
                                QPointF(x, y + height)
                            )
                            qp.drawPolygon(QPolygonF(points))
                        elif obj['shapeType'] == "PARALLELOGRAM_LEFT":
                            points = (
                                QPointF(x, y), QPointF(x + 4 * width // 5, y), QPointF(x + width, y + height),
                                QPointF(x + width // 5, y + height)
                            )
                            qp.drawPolygon(QPolygonF(points))
                        qp.setPen(QPen(QColor(0, 0, 0), 12, Qt.SolidLine))
                        qp.drawText(box, Qt.AlignCenter, obj['characters'])

                    elif obj['type'] == "TEXT":
                        qp.setFont(QFont(obj["style"]["fontFamily"], obj["style"]["fontSize"]))
                        qp.setPen(QPen(color))
                        width, height = obj['absoluteBoundingBox']['width'] * self.scale + self.eps, obj['absoluteBoundingBox']['height'] * self.scale + self.eps
                        box = QRect(x, y, width, height)
                        qp.drawText(box, Qt.AlignCenter, obj['characters'].strip())
                except BaseException as exeption:
                    log.exception(f"ERROR:\n{exeption.args}")

            qp.end()
            self.canvas.setPixmap(self.pixmap)
            self.need_to_update = 0

    def make_request(self) -> None:
        header = {}
        request = 'https://api.figma.com/v1/files/{}'
        header['X-FIGMA-TOKEN'] = self.line_access_token.text().strip()
        header['Content-Type'] = 'application/json'
        response = requests.get(request.format(self.line_project_name.text().strip()), headers=header)
        log.info(f"RESPONSE:\n{response.json()}")
        if response:
            self.need_to_update = 1
            try:
                response = response.json()['document']['children'][0]['children']
                self.response = []
                x = [0]
                y = [0]
                for obj in response:
                    self.response.append(obj)
                    x.append(obj['absoluteBoundingBox']['x'])
                    y.append(obj['absoluteBoundingBox']['y'])
                    x.append(obj['absoluteBoundingBox']['x'] + obj['absoluteBoundingBox']['width'])
                    y.append(obj['absoluteBoundingBox']['y'] + obj['absoluteBoundingBox']['height'])
                self.offset_x = min(x)
                self.offset_y = min(y)
                if max(x) - self.offset_x != 0 and max(y) - self.offset_y != 0:
                    self.scale = min(self.width / (max(x) - self.offset_x), self.height / (max(y) - self.offset_y))
                else:
                    self.scale = 1
            except BaseException as exeption:
                log.exception(f"ERROR:\n{exeption.args}")


def except_hook(cls: Any, exception: Any, traceback: Any) -> None:
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FigmaDisplayer()
    ex.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())