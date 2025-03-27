import warnings
import os

warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QVBoxLayout, QGridLayout, QLabel, QDialog, QListWidget, QListWidgetItem, QScrollArea, QPushButton, QWidget)
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFileDialog
from PyQt5 import QtCore, QtGui

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

        ## Create the Docks
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

        self.widget_one = showLabels(self)
        self.widget_two = showPatches(self)

        # Wrap widget_one (showLabels) in a QScrollArea
        scroll_area_widget_one = QScrollArea()
        scroll_area_widget_one.setWidgetResizable(True)  # Allow resizing of the scroll area
        scroll_area_widget_one.setWidget(self.widget_one)  # Set widget_one as the scrollable content

        # Add the widgets to docks
        self.dock1.addWidget(scroll_area_widget_one)
        self.dock2.addWidget(self.widget_two)

        # Add buttons to main layout
        self.load_button = QPushButton('Load images')
        self.load_button.clicked.connect(self.load_images)

        self.exit_button = QPushButton('Exit')
        self.exit_button.clicked.connect(self.close)

        ## Place the Docks inside the DockArea
        # Dock 1 is the left area with labels
        dock_area.addDock(self.dock1)
        # Dock 2 is the right area with images/patches
        # Patches dock will be to the right of labels
        dock_area.addDock(self.dock2, 'right', self.dock1)
        
        # self.main_layout.addWidget(label)
        self.main_layout.addWidget(dock_area)
        self.main_layout.addWidget(self.exit_button)
        self.main_layout.addWidget(self.load_button)

        ## This is for set the initial size and position of the main window
        self.setGeometry(200, 100, 2400, 1600)

        # Count the number of selected patches by user
        self.numSelectPatches = 0

    def clear_layout(self, layout):
        if layout is not None:
            if layout.count() is not None:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    def load_images(self, layout):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")

        if directory:
            import os

            self._base_dir = os.getcwd()
            self._images_dir = os.path.join(self._base_dir, directory)

            self.list_of_images = os.listdir(directory)
            self.list_of_images = sorted(self.list_of_images)

            # TODO: in the case that the directory chosen only contains folders and not images, 
            # show a dialog that says no images found in directory

            # Set directory details in dock1, widget_one
            self.widget_one.directoryName.setText('Directory: {}'.format(directory))
            self.widget_one.patchCount.setText('Patch Count: {}'.format(len(self.list_of_images)))
            self.widget_one.selectedPatchCount.setText('Selected Patch Count: {}'.format(self.numSelectPatches))

            # Clear the existing layout in widget_two (in dock2)
            self.clear_layout(self.widget_two.layout)

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
                label = ClickableLabel(directory.split('/')[-1], image_path.split('/')[-1])
                # label.clicked.connect(self.widget_one.handleLabelClickedInLabels)
                label.clicked.connect(self.widget_two.handleLabelClickedInPatches)
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

            # Add the scroll area to widget_two in dock2
            self.widget_two.layout.addWidget(scroll_area)

            # Make patch editing buttons visible in dock1
            self.widget_one.layout.addWidget(showEditButtons(self))

class showLabels(QWidget):

    # class functions
    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.directoryName = QLabel('Directory : ---')
        self.patchName = QLabel('Patch File Name : ---')
        self.patchCount = QLabel('Patch Count : ---')
        self.selectedPatchCount = QLabel('Selected Patch Count : ---')
        self.selectedImageList = QLabel('Selected Image List : ---')

        self.layout.addWidget(self.directoryName)
        self.layout.addWidget(self.patchName)
        self.layout.addWidget(self.patchCount)
        self.layout.addWidget(self.selectedPatchCount)
        self.layout.addWidget(self.selectedImageList)

class showEditButtons(QWidget):
    # class functions
    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.deleteImagesButton = QPushButton('Delete')
        self.deselectAllButton = QPushButton('Unselect All')

        self.layout.addWidget(self.deleteImagesButton)
        self.deleteImagesButton.clicked.connect(self.deleteImages)

        self.layout.addWidget(self.deselectAllButton)


    # for each image in selectedImages list, delete the image
    def deleteImages(self):
        # Check if there are any selected images
        if not self.parent.widget_two.selectedImages:
            print("No images selected for deletion.")
            return

        # Iterate through the selected images and delete them
        for image in self.parent.widget_two.selectedImages:
            try:
                print('Deleting image: ', image)
                os.remove(image)  # Delete the image file
                print("All selected images have been deleted.")
            except FileNotFoundError:
                print(f"File not found: {image}")
            except Exception as e:
                print(f"Error deleting file {image}: {e}")

        # Clear the selectedImages list
        self.parent.widget_two.selectedImages.clear()

        # Update the UI
        self.parent.widget_one.selectedPatchCount.setText('Selected Patch Count : 0')
        self.parent.widget_one.selectedImageList.setText('Selected Image List : ---')
        # self.parent.clear_layout(self.parent.widget_two.layout)  # Clear the layout in widget_two

class showPatches(QWidget):
    # class variables
    selectedImages = []
    # imageClicked = QtCore.pyqtSignal([list]) # Signal Created

    # class functions
    def __init__(self, parent):
        QWidget.__init__(self)
        ## 
        self.parent = parent
        self.layout = QVBoxLayout()  # Vertical Layout
        self.setLayout(self.layout)
        self.titleList = QListWidget()

        # Call gather_images function on image click
        # self.imageClicked.connect(self.gather_images)

        # self.titleList.itemDoubleClicked.connect(self.onClicked)

    # signal 'slot' 
    def handleLabelClickedInPatches(self, name, fileName):
        if fileName not in self.selectedImages:
            # add recently selected image to selectedImages list
            self.selectedImages.append(fileName)
            # SEND SIGNAL TO SHOW SELECTED ICON
        else:
            # if image was already in selectedImages list, remove it
            self.selectedImages.remove(fileName)
            # SEND SIGNAL TO REMOVE SELECTED ICON
        print('"%s" clicked with %s file name' % (name, fileName))
        print('Selected Images: ', self.selectedImages)

        # Update the patchName and selectedPatchCount labels in widget_one (showLabels instance)
        self.parent.widget_one.patchName.setText('Patch File Name : {}'.format(fileName))
        self.parent.widget_one.selectedPatchCount.setText('Selected Patch Count : {}'.format(len(self.selectedImages)))
        self.parent.widget_one.selectedImageList.setText('Selected Image List : {}'.format(self.selectedImages))

class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal(str, str)

    def __init__(self, imageLabel, imageFileName, parent=None):
        super(ClickableLabel, self).__init__()
        self.imageLabel = imageLabel
        self.imageFileName = imageFileName

    def mousePressEvent(self, event):
        # self.clicked.emit(self.objectName(), self.imageLabel, self.imageFileName)
        self.clicked.emit(self.imageLabel, self.imageFileName)
    