import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (QGridLayout, QLabel, QDialog, QPushButton)
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFileDialog

from coralnet_toolbox.QtImageWindow import ImageWindow
from coralnet_toolbox.Icons import get_icon

# ----------------------------------------------------------------------------------------------------------------------
# Classes
# ----------------------------------------------------------------------------------------------------------------------

class PatchEditorWindowDialog(QDialog):
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Patch Editor")
        self.setWindowIcon(get_icon("coral.png"))
        # self.setWindowState(Qt.WindowMaximized)  # Ensure the dialog is maximized

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.loadButton = QPushButton("Load Images")
        self.loadButton.clicked.connect(self.load_images)
        self.layout.addWidget(self.loadButton, 0, 0)

    def load_images(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")

        if directory:
            import os

            self._base_dir = os.getcwd()
            self._images_dir = os.path.join(self._base_dir, directory)

            self.list_of_images = os.listdir(directory)
            self.list_of_images = sorted(self.list_of_images)

            print("list images: " + str(self.list_of_images))

            # Length of Images
            print('Number of Images in the selected folder: {}'.format(len(self.list_of_images)))

        # Create and add image labels to the grid
        row, col = 0, 0
        for image in self.list_of_images:
            image_path = '{}\\{}'.format(self._images_dir, image)
            label = QLabel()
            pixmap = QPixmap(image_path)
            label.setPixmap(pixmap)
            label.setScaledContents(True)
            label.setMaximumSize(600, 400) # limit image size
            self.layout.addWidget(label, row, col)

            col += 1
            if col > 2:  # 3 columns per row
                col = 0
                row += 1