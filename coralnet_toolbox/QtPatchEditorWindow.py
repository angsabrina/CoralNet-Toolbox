import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import random

from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QColor, QPen, QBrush
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QCheckBox,
                             QVBoxLayout, QLabel, QDialog, QHBoxLayout, QPushButton,
                             QComboBox, QSpinBox, QGraphicsPixmapItem, QGraphicsRectItem,
                             QFormLayout, QButtonGroup)


# ----------------------------------------------------------------------------------------------------------------------
# Classes
# ----------------------------------------------------------------------------------------------------------------------

class PatchEditorWindowDialog(QDialog):
    annotationsSampled = pyqtSignal(list, bool)  # Signal to emit the sampled annotations and apply to all flag

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.annotation_window = main_window.annotation_window
        self.label_window = main_window.label_window
        self.image_window = main_window.image_window

        self.setWindowTitle("Patch Editor")
        self.setWindowState(Qt.WindowMaximized)  # Ensure the dialog is maximized

        self.layout = QVBoxLayout(self)