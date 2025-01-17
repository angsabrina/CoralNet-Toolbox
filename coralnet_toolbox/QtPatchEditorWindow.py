import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QVBoxLayout, QGridLayout, QLabel, QDialog, QListWidget, QListWidgetItem, QScrollArea, QPushButton, QWidget)
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFileDialog
from PyQt5 import QtCore

from pyqtgraph.dockarea import DockArea, Dock

from coralnet_toolbox.QtImageWindow import ImageWindow
from coralnet_toolbox.Icons import get_icon

text = (
    "This is the patch editor tool.\n"
    "\n"
    "The use the button below to load a directory of patches to edit.\n"
    "\n"
    "You can retrieve the child widget using the widget() function. The view can be made to be "
    "resizable with the setWidgetResizable() function. The alignment of the widget can be "
    "specified with setAlignment().\n"
)


# ----------------------------------------------------------------------------------------------------------------------
# Classes
# ----------------------------------------------------------------------------------------------------------------------

class DockArea(DockArea):
    ## This is to prevent the Dock from being resized to te point of disappear
    def makeContainer(self, typ):
        new = super(DockArea, self).makeContainer(typ)
        new.setChildrenCollapsible(False)
        return new
    
class PatchEditorWindowDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Patch Editor")
        self.setWindowIcon(get_icon("coral.png"))

        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        ## The DockArea as its name says, is the are where we place the Docks
        dock_area = DockArea(self)
        ## Create the Docks and change some esthetic of them
        self.dock1 = Dock('Labels', size=(200, 500))
        self.dock2 = Dock('Patches', size=(600, 500))
        self.dock1.hideTitleBar()
        self.dock2.hideTitleBar()
        self.dock1.nStyle = """
        Dock > QWidget {
            border: 0px solid #000;
            border-radius: 0px;
        }"""
        self.dock2.nStyle = """
        Dock > QWidget {
            border: 0px solid #000;
            border-radius: 0px;
        }"""
        self.button = QPushButton('Exit')
        self.widget_one = showLabels()
        self.widget_two = showPatches()
        ## Place the Docks inside the DockArea
        dock_area.addDock(self.dock1)
        # Patches dock will be to the right of labels
        dock_area.addDock(self.dock2, 'right', self.dock1)
        
        # self.main_layout.addWidget(label)
        self.main_layout.addWidget(dock_area)
        self.main_layout.addWidget(self.button)

        ## Add the Widgets inside each dock
        self.dock1.addWidget(self.widget_one)
        self.dock2.addWidget(self.widget_two)
        ## This is for set the initial size and position of the main window
        self.setGeometry(200, 100, 2400, 1600)
        ## Connect the actions to functions, there is a default function called close()
        self.widget_two.imageClicked.connect(self.dob_click)
        self.button.clicked.connect(self.close)

    def dob_click(self, feed):
        self.widget_two.text_box.clear()
        self.widget_two.text_box.setText(
            'Title : ' + feed[0]\
            + '\n\n' +\
            'Summary : ' + feed[1]
        )


class showLabels(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.labelName = QLabel('Label : ---')
        self.patchName = QLabel('Patch Name : ---')
        self.labelCount = QLabel('Label Count : ---')
        self.layout.addWidget(self.labelName)
        self.layout.addWidget(self.patchName)
        self.layout.addWidget(self.labelCount)

class showPatches(QWidget):
    imageClicked = QtCore.pyqtSignal([list]) # Signal Created
    def __init__(self):
        QWidget.__init__(self)
        ## 
        self.layout = QVBoxLayout()  # Vertical Layout
        self.setLayout(self.layout)
        self.titleList = QListWidget()

        # Create load image button and call load_images function on click
        self.loadButton = QPushButton("Load Images")
        self.loadButton.clicked.connect(self.load_images)
        self.layout.addWidget(self.loadButton)

        self.titleList.itemDoubleClicked.connect(self.onClicked)

    def onClicked(self, item):
        ## Just test parameters and signal emited
        self.imageClicked.emit([item.text(), item.text()+item.text()]) 

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

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

            # Clear the existing layout
            self.clear_layout(self.layout)

            label = QLabel('Edit the patches below: ')
            label.setMaximumHeight(15)

            # Create a scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)

            # Create a container widget for the grid layout
            container_widget = QWidget()
            grid_layout = QGridLayout(container_widget)

            # Create and add image labels to the grid
            row, col = 0, 0
            for image in self.list_of_images:
                image_path = os.path.join(self._images_dir, image)
                label = QLabel()
                pixmap = QPixmap(image_path)
                label.setPixmap(pixmap)
                label.setScaledContents(True)
                label.setMaximumSize(600, 400)  # limit image size
                grid_layout.addWidget(label, row, col)

                col += 1
                if col > 2:  # 3 columns per row
                    col = 0
                    row += 1

            # Set the container widget as the scroll area's widget
            scroll_area.setWidget(container_widget)

            # Add the scroll area to the main layout
            self.layout.addWidget(scroll_area)