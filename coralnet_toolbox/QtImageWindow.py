import warnings

import gc
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from queue import Queue

import numpy as np
import rasterio
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QDateTime
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import (QSizePolicy, QMessageBox, QCheckBox, QWidget, QVBoxLayout,
                             QLabel, QComboBox, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QApplication, QMenu, QButtonGroup, QAbstractItemView,
                             QGroupBox)

from rasterio.windows import Window

from coralnet_toolbox.QtProgressBar import ProgressBar

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


# ----------------------------------------------------------------------------------------------------------------------
# Classes
# ----------------------------------------------------------------------------------------------------------------------


class LoadFullResolutionImageWorker(QThread):
    imageLoaded = pyqtSignal(QImage)
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self._is_cancelled = False
        self.full_resolution_image = None

    def run(self):
        try:
            # Load the QImage
            self.full_resolution_image = QImage(self.image_path)
            # Emit the signal with the loaded image
            if not self._is_cancelled:
                self.imageLoaded.emit(self.full_resolution_image)
        except Exception as e:
            self.errorOccurred.emit(str(e))
        finally:
            self.finished.emit()

    def cancel(self):
        self._is_cancelled = True


class ImageWindow(QWidget):
    imageSelected = pyqtSignal(str)
    imageChanged = pyqtSignal()  # New signal for image change
    MAX_CONCURRENT_THREADS = 8  # Maximum number of concurrent threads
    THROTTLE_INTERVAL = 50  # Minimum time (in milliseconds) between image selection

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.annotation_window = main_window.annotation_window

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # -------------------------------------------
        # Create a QGroupBox for search and filters
        self.filter_group = QGroupBox("Search and Filters")
        self.filter_layout = QVBoxLayout()
        self.filter_group.setLayout(self.filter_layout)

        # Create a horizontal layout for the checkboxes
        self.checkbox_layout = QHBoxLayout()
        self.filter_layout.addLayout(self.checkbox_layout)

        # Add a QButtonGroup for the checkboxes
        self.checkbox_group = QButtonGroup(self)
        self.checkbox_group.setExclusive(False)

        # Add checkboxes for filtering images based on annotations
        self.no_annotations_checkbox = QCheckBox("No Annotations", self)
        self.no_annotations_checkbox.stateChanged.connect(self.filter_images)
        self.checkbox_layout.addWidget(self.no_annotations_checkbox)
        self.checkbox_group.addButton(self.no_annotations_checkbox)

        self.has_annotations_checkbox = QCheckBox("Has Annotations", self)
        self.has_annotations_checkbox.stateChanged.connect(self.filter_images)
        self.checkbox_layout.addWidget(self.has_annotations_checkbox)
        self.checkbox_group.addButton(self.has_annotations_checkbox)

        self.has_predictions_checkbox = QCheckBox("Has Predictions", self)
        self.has_predictions_checkbox.stateChanged.connect(self.filter_images)
        self.checkbox_layout.addWidget(self.has_predictions_checkbox)
        self.checkbox_group.addButton(self.has_predictions_checkbox)

        # Create a vertical layout for the search bars
        self.search_layout = QVBoxLayout()
        self.filter_layout.addLayout(self.search_layout)

        fixed_width = 250

        # Create a horizontal layout for images search
        self.image_search_layout = QHBoxLayout()
        self.search_layout.addLayout(self.image_search_layout)

        # Add label and search bar for images
        self.image_search_label = QLabel("Search Images:", self)
        self.image_search_layout.addWidget(self.image_search_label)
        self.search_bar_images = QComboBox(self)
        self.search_bar_images.setEditable(True)
        self.search_bar_images.setPlaceholderText("Type to search images")
        self.search_bar_images.setInsertPolicy(QComboBox.NoInsert)
        self.search_bar_images.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_bar_images.lineEdit().textChanged.connect(self.filter_images)
        self.search_bar_images.setFixedWidth(fixed_width)
        self.image_search_layout.addWidget(self.search_bar_images)

        # Create a horizontal layout for labels search
        self.label_search_layout = QHBoxLayout()
        self.search_layout.addLayout(self.label_search_layout)

        # Add label and search bar for labels
        self.label_search_label = QLabel("Search Labels:", self)
        self.label_search_layout.addWidget(self.label_search_label)
        self.search_bar_labels = QComboBox(self)
        self.search_bar_labels.setEditable(True)
        self.search_bar_labels.setPlaceholderText("Type to search labels")
        self.search_bar_labels.setInsertPolicy(QComboBox.NoInsert)
        self.search_bar_labels.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_bar_labels.lineEdit().textChanged.connect(self.filter_images)
        self.search_bar_labels.setFixedWidth(fixed_width)
        self.label_search_layout.addWidget(self.search_bar_labels)

        # Add the group box to the main layout
        self.layout.addWidget(self.filter_group)

        # -------------------------------------------
        # Create a QGroupBox for Image Window
        self.info_table_group = QGroupBox("Image Window", self)
        info_table_layout = QVBoxLayout()
        self.info_table_group.setLayout(info_table_layout)

        # Create a horizontal layout for the labels
        self.info_layout = QHBoxLayout()
        info_table_layout.addLayout(self.info_layout)

        # Add a label to display the index of the currently selected image
        self.current_image_index_label = QLabel("Current Image: None", self)
        self.current_image_index_label.setAlignment(Qt.AlignCenter)
        self.current_image_index_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.current_image_index_label.setFixedHeight(24)
        self.info_layout.addWidget(self.current_image_index_label)

        # Add a label to display the total number of images
        self.image_count_label = QLabel("Total Images: 0", self)
        self.image_count_label.setAlignment(Qt.AlignCenter)
        self.image_count_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_count_label.setFixedHeight(24)
        self.info_layout.addWidget(self.image_count_label)

        # Create and setup table widget
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Image Name", "Annotations"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SingleSelection)
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.show_context_menu)
        self.tableWidget.cellClicked.connect(self.load_image)
        self.tableWidget.keyPressEvent = self.tableWidget_keyPressEvent

        self.tableWidget.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
            background-color: #E0E0E0;
            padding: 4px;
            border: 1px solid #D0D0D0;
            }
        """)

        self.tableWidget.setColumnWidth(0, 200)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)

        # Add table widget to the info table group layout
        info_table_layout.addWidget(self.tableWidget)

        # Add the group box to the main layout
        self.layout.addWidget(self.info_table_group)

        self.image_paths = []  # Store all image paths
        self.image_dict = {}  # Dictionary to store all image information
        self.filtered_image_paths = []  # List to store filtered image paths
        self.selected_image_path = None
        self.right_clicked_row = None  # Attribute to store the right-clicked row

        self.images = {}  # Dictionary to store image paths and their QImage representation
        self.rasterio_images = {}  # Dictionary to store image paths and their Rasterio representation
        self.image_cache = {}  # Cache for images

        self.show_confirmation_dialog = True

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.filter_images)
        self.search_bar_images.lineEdit().textChanged.connect(self.debounce_search)
        self.search_bar_labels.lineEdit().textChanged.connect(self.debounce_search)

        self.image_load_queue = Queue()
        self.current_workers = []  # List to keep track of running workers
        self.last_image_selection_time = QDateTime.currentMSecsSinceEpoch()

        # TODO add a dict mapping tableWidget row to image path, faster
        # Connect annotationCreated, annotationDeleted signals to update annotation count in real time
        self.annotation_window.annotationCreated.connect(self.update_annotation_count)
        self.annotation_window.annotationDeleted.connect(self.update_annotation_count)

    def add_image(self, image_path):
        if image_path not in self.image_paths:
            self.image_paths.append(image_path)
            filename = os.path.basename(image_path)
            self.image_dict[image_path] = {
                'filename': filename,
                'has_annotations': False,
                'has_predictions': False,
                'labels': set(),  # Initialize an empty set for labels
                'annotation_count': 0  # Initialize annotation count
            }
            self.update_table_widget()
            self.update_image_count_label()
            self.update_search_bars()
            QApplication.processEvents()

    def update_table_widget(self):
        self.tableWidget.setRowCount(0)  # Clear the table

        # Center align the column headers
        self.tableWidget.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)

        for path in self.filtered_image_paths:
            row_position = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_position)

            item_text = f"{self.image_dict[path]['filename']}"
            item_text = item_text[:23] + "..." if len(item_text) > 25 else item_text
            item = QTableWidgetItem(item_text)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setToolTip(os.path.basename(path))
            item.setTextAlignment(Qt.AlignCenter)  # Center align the text
            self.tableWidget.setItem(row_position, 0, item)

            annotation_count = self.image_dict[path]['annotation_count']
            annotation_item = QTableWidgetItem(str(annotation_count))
            annotation_item.setFlags(annotation_item.flags() & ~Qt.ItemIsEditable)
            annotation_item.setTextAlignment(Qt.AlignCenter)  # Center align the text
            self.tableWidget.setItem(row_position, 1, annotation_item)

        self.update_table_selection()

    def update_table_selection(self):
        if self.selected_image_path in self.filtered_image_paths:
            row = self.filtered_image_paths.index(self.selected_image_path)
            self.tableWidget.selectRow(row)
            self.tableWidget.scrollToItem(self.tableWidget.item(row, 0), QAbstractItemView.PositionAtCenter)
        else:
            self.tableWidget.clearSelection()

    def update_image_count_label(self):
        total_images = len(set(self.filtered_image_paths))
        self.image_count_label.setText(f"Total Images: {total_images}")

    def update_current_image_index_label(self):
        if self.selected_image_path and self.selected_image_path in self.filtered_image_paths:
            index = self.filtered_image_paths.index(self.selected_image_path) + 1
            self.current_image_index_label.setText(f"Current Image: {index}")
        else:
            self.current_image_index_label.setText("Current Image: None")

    def update_image_annotations(self, image_path):
        if image_path in self.image_dict:
            # Check for any annotations
            annotations = self.annotation_window.get_image_annotations(image_path)
            # Check for any predictions
            predictions = [a.machine_confidence for a in annotations if a.machine_confidence != {}]
            # Check for any labels
            labels = {annotation.label.short_label_code for annotation in annotations}
            self.image_dict[image_path]['has_annotations'] = bool(annotations)
            self.image_dict[image_path]['has_predictions'] = len(predictions)
            self.image_dict[image_path]['labels'] = labels
            self.image_dict[image_path]['annotation_count'] = len(annotations)
            self.update_table_widget()
            
    def update_current_image_annotations(self):
        if self.selected_image_path:
            self.update_image_annotations(self.selected_image_path)

    def update_annotation_count(self, annotation_id):
        if annotation_id in self.annotation_window.annotations_dict:
            # Get the image path associated with the annotation
            image_path = self.annotation_window.annotations_dict[annotation_id].image_path
        else:
            # It's already been deleted, so get the current image path
            image_path = self.annotation_window.current_image_path
        # Update the image annotation count in table widget
        self.update_image_annotations(image_path)

    def load_image(self, row, column):
        # Add safety checks
        if not self.filtered_image_paths:
            return

        if row < 0 or row >= len(self.filtered_image_paths):
            return

        # Get the image path associated with the selected row
        image_path = self.filtered_image_paths[row]
        self.load_image_by_path(image_path)

    def load_image_by_path(self, image_path, update=False):
        current_time = QDateTime.currentMSecsSinceEpoch()
        time_since_last_selection = current_time - self.last_image_selection_time

        if time_since_last_selection < self.THROTTLE_INTERVAL:
            # If selecting images too quickly, ignore this request
            return

        if image_path not in self.image_paths:
            return

        if image_path == self.selected_image_path and update is False:
            return

        self.last_image_selection_time = current_time

        # Add the image path to the queue
        self.image_load_queue.put(image_path)

        # Start processing the queue if we're under the thread limit
        self._process_image_queue()
        # Emit the signal when a new image is chosen
        self.imageChanged.emit()
        # Update the search bars
        self.update_search_bars()

    def _process_image_queue(self):
        if self.image_load_queue.empty():
            return

        # Remove finished workers from the list
        self.current_workers = [worker for worker in self.current_workers if worker.isRunning()]

        # If we're at the thread limit, don't start a new one
        if len(self.current_workers) >= self.MAX_CONCURRENT_THREADS:
            return

        image_path = self.image_load_queue.get()

        try:
            # Update the selected image path
            self.selected_image_path = image_path
            self.imageSelected.emit(image_path)
            self.update_table_selection()
            self.update_current_image_index_label()

            # Set the cursor to the wait cursor
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # Load and display scaled-down version
            scaled_image = self.load_scaled_image(image_path)
            self.annotation_window.display_image_item(scaled_image)

            # Create and start the worker thread for full-resolution image
            worker = LoadFullResolutionImageWorker(image_path)
            worker.imageLoaded.connect(self.on_full_resolution_image_loaded)
            worker.finished.connect(lambda: self.on_worker_finished(worker))
            worker.errorOccurred.connect(self.on_worker_error)
            worker.start()

            self.current_workers.append(worker)

        except Exception as e:
            print(f"Error processing image {image_path}: {str(e)}")
            self.on_worker_finished(None)

    def on_worker_finished(self, finished_worker):
        if finished_worker in self.current_workers:
            self.current_workers.remove(finished_worker)

        QTimer.singleShot(0, self._process_image_queue)

    def on_worker_error(self, error_message):
        print(f"Worker error: {error_message}")
        self.on_worker_finished(None)

    def closeEvent(self, event):
        for worker in self.current_workers:
            if worker.isRunning():
                worker.cancel()
                worker.quit()
                worker.wait()
        QApplication.restoreOverrideCursor()
        super().closeEvent(event)

    def load_scaled_image(self, image_path):
        try:
            # Open the raster file with Rasterio
            with rasterio.open(image_path) as src:
                # Get the original size of the image
                original_width = src.width
                original_height = src.height
                # Determine the number of bands
                num_bands = src.count

                # Calculate the scaled size
                scaled_width = original_width // 100
                scaled_height = original_height // 100

                # Read a downsampled version of the image
                # We use a window to read a subset of the image and then resize it
                window = Window(0, 0, original_width, original_height)

                if num_bands == 1:
                    # Read a single band
                    downsampled_image = src.read(window=window,
                                                 out_shape=(scaled_height, scaled_width))

                    # Grayscale image
                    qimage = QImage(downsampled_image.data.tobytes(),
                                    scaled_width,
                                    scaled_height,
                                    QImage.Format_Grayscale8)

                elif num_bands == 3 or num_bands == 4:
                    # Read bands in the correct order (RGB)
                    downsampled_image = src.read([1, 2, 3],
                                                 window=window,
                                                 out_shape=(scaled_height, scaled_width))

                    # Convert to uint8 if it's not already
                    rgb_image = downsampled_image.astype(np.uint8)
                    # Ensure the bands are in the correct order (RGB)
                    rgb_image = np.transpose(rgb_image, (1, 2, 0))

                    # Create QImage directly from the numpy array
                    qimage = QImage(rgb_image.data.tobytes(),
                                    scaled_width,
                                    scaled_height,
                                    scaled_width * 3,
                                    QImage.Format_RGB888)
                else:
                    raise ValueError(f"Unsupported number of bands: {num_bands}")

                # Close the rasterio dataset
                src.close()
                gc.collect()

                return qimage
        except Exception as e:
            print(f"Error loading scaled image {image_path}: {str(e)}")
            return QImage()  # Return an empty QImage if there's an error

    def on_full_resolution_image_loaded(self, full_resolution_image):
        if not self.selected_image_path:
            return

        # Load the Rasterio
        self.rasterio_images[self.selected_image_path] = self.rasterio_open(self.selected_image_path)

        # Update the selected image
        self.update_table_selection()

        # Update the display with the full-resolution image
        self.images[self.selected_image_path] = full_resolution_image
        self.annotation_window.set_image(self.selected_image_path)
        self.imageSelected.emit(self.selected_image_path)

        # Restore the cursor to the default cursor
        QApplication.restoreOverrideCursor()

    @lru_cache(maxsize=32)
    def rasterio_open(self, image_path):
        # Open the image with Rasterio
        self.src = rasterio.open(image_path)
        return self.src

    def rasterio_close(self, image_path):
        # Close the image with Rasterio
        self.rasterio_images[image_path] = None

    def show_context_menu(self, position):
        row = self.tableWidget.rowAt(position.y())
        if row < 0 or row >= len(self.filtered_image_paths):
            return

        self.right_clicked_row = row
        context_menu = QMenu(self)
        delete_annotations_action = context_menu.addAction("Delete Annotations")
        delete_annotations_action.triggered.connect(self.delete_annotations)
        delete_image_action = context_menu.addAction("Delete Image")
        delete_image_action.triggered.connect(self.delete_selected_image)
        context_menu.exec_(self.tableWidget.viewport().mapToGlobal(position))

    def delete_annotations(self):
        if self.right_clicked_row is not None:
            image_path = self.filtered_image_paths[self.right_clicked_row]
            reply = QMessageBox.question(self,
                                         "Confirm Delete",
                                         "Are you sure you want to delete annotations for this image?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                # Proceed with deleting annotations
                self.annotation_window.delete_image_annotations(image_path)
                self.main_window.confidence_window.clear_display()

    def delete_image(self, image_path):
        if image_path in self.image_paths:
            # Get current index before removing
            current_index = self.filtered_image_paths.index(image_path)

            # Remove the image from lists and dict
            self.image_paths.remove(image_path)
            del self.image_dict[image_path]
            if image_path in self.filtered_image_paths:
                self.filtered_image_paths.remove(image_path)

            # Remove the image's annotations
            self.annotation_window.delete_image(image_path)

            # Update the table widget
            self.update_table_widget()

            # Update the image count label
            self.update_image_count_label()

            # Select next available image
            if self.filtered_image_paths:
                # Try to keep same index, fallback to previous
                if current_index < len(self.filtered_image_paths):
                    new_image_path = self.filtered_image_paths[current_index]
                else:
                    new_image_path = self.filtered_image_paths[current_index - 1]
                self.load_image_by_path(new_image_path)
            else:
                self.selected_image_path = None
                self.annotation_window.clear_scene()

            # Update the current image index label
            self.update_current_image_index_label()

    def delete_selected_image(self):
        if self.right_clicked_row is not None:
            image_path = self.filtered_image_paths[self.right_clicked_row]
            if self._confirm_delete() == QMessageBox.Yes:
                self.delete_image(image_path)

    def _confirm_delete(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText("Are you sure you want to delete this image?\n"
                        "This will delete all associated annotations.")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        checkbox = QCheckBox("Do not show this message again")
        msg_box.setCheckBox(checkbox)

        result = msg_box.exec_()

        if checkbox.isChecked():
            self.show_confirmation_dialog = False

        return result

    def tableWidget_keyPressEvent(self, event):
        if event.key() == Qt.Key_Up or event.key() == Qt.Key_Down:
            # Ignore up and down arrow keys
            return
        else:
            # Call the base class method for other keys
            super(QTableWidget, self.tableWidget).keyPressEvent(event)

    def cycle_previous_image(self):
        if not self.filtered_image_paths:
            return

        current_index = self.filtered_image_paths.index(self.selected_image_path)
        new_index = (current_index - 1) % len(self.filtered_image_paths)
        self.load_image_by_path(self.filtered_image_paths[new_index])

    def cycle_next_image(self):
        if not self.filtered_image_paths:
            return

        current_index = self.filtered_image_paths.index(self.selected_image_path)
        new_index = (current_index + 1) % len(self.filtered_image_paths)
        self.load_image_by_path(self.filtered_image_paths[new_index])

    def debounce_search(self):
        self.search_timer.start(10000)

    def filter_images(self):
        # Store the currently selected image path before filtering
        current_selected_path = self.selected_image_path

        search_text_images = self.search_bar_images.currentText()
        search_text_labels = self.search_bar_labels.currentText()
        no_annotations = self.no_annotations_checkbox.isChecked()
        has_annotations = self.has_annotations_checkbox.isChecked()
        has_predictions = self.has_predictions_checkbox.isChecked()

        # Return early if none of the search bar or checkboxes are being used
        if (not (search_text_images or search_text_labels) and
            not (no_annotations or has_annotations or has_predictions)):
            self.filtered_image_paths = self.image_paths.copy()
            self.update_table_widget()
            self.update_current_image_index_label()
            self.update_image_count_label()
            return

        self.filtered_image_paths = []

        # Initialize the progress bar
        progress_dialog = ProgressBar(title="Filtering Images")
        progress_dialog.start_progress(len(self.image_paths))

        # Use a ThreadPoolExecutor to filter images in parallel
        with ThreadPoolExecutor() as executor:
            futures = []
            for path in self.image_paths:
                future = executor.submit(
                    self.filter_image,
                    path,
                    search_text_images,
                    search_text_labels,
                    no_annotations,
                    has_annotations,
                    has_predictions,
                )
                futures.append(future)

            for future in as_completed(futures):
                if future.result():
                    self.filtered_image_paths.append(future.result())
                progress_dialog.update_progress()

        # Sort the filtered image paths to be displaying in ImageWindow
        self.filtered_image_paths.sort()

        # Update the table widget
        self.update_table_widget()

        # After filtering, either restore the previously selected image if it's still in the filtered list,
        # or load the first image if nothing was selected or the previous selection is no longer visible
        if self.filtered_image_paths:
            if current_selected_path and current_selected_path in self.filtered_image_paths:
                self.load_image_by_path(current_selected_path)
            else:
                self.load_first_filtered_image()
        else:
            self.selected_image_path = None
            self.annotation_window.clear_scene()

        # Update the current image index label and image count label
        self.update_current_image_index_label()
        self.update_image_count_label()

        # Stop the progress bar
        progress_dialog.stop_progress()

    def filter_image(self,
                     path,
                     search_text_images,
                     search_text_labels,
                     no_annotations,
                     has_annotations,
                     has_predictions):
        """
        Filter images based on search text and checkboxes

        Args:
            path (str): Path to the image
            search_text_images (str): Search text for image names
            search_text_labels (str): Search text for labels
            no_annotations (bool): Filter images with no annotations
            has_annotations (bool): Filter images with annotations
            has_predictions (bool): Filter images with predictions

            Returns:
                str: Path to the image if it passes the filters, None otherwise
        """
        filename = os.path.basename(path)
        # Check for annotations for the provided path
        annotations = self.annotation_window.get_image_annotations(path)
        # Check for predictions for the provided path
        predictions = self.image_dict[path]['has_predictions']
        # Check the labels for the provided path
        labels = self.image_dict[path]['labels']

        # Filter images based on search text and checkboxes
        if search_text_images and search_text_images not in filename:
            return None
        # Filter images based on search text and checkboxes
        if search_text_labels and search_text_labels not in labels:
            return None
        # Filter images based on checkboxes, and if the image has annotations
        if no_annotations and annotations:
            return None
        # Filter images based on checkboxes, and if the image has no annotations
        if has_annotations and not annotations:
            return None
        # Filter images based on checkboxes, and if the image has predictions
        if has_predictions and not predictions:
            return None

        return path

    def load_first_filtered_image(self):
        if self.filtered_image_paths:
            self.annotation_window.clear_scene()
            self.load_image_by_path(self.filtered_image_paths[0])

    def update_search_bars(self):
        # Store current search texts
        current_image_search = self.search_bar_images.currentText()
        current_label_search = self.search_bar_labels.currentText()

        # Clear and update items
        self.search_bar_images.clear()
        self.search_bar_labels.clear()

        image_names = [self.image_dict[path]['filename'] for path in self.image_paths]
        label_names = set()
        for path in self.image_paths:
            label_names.update(self.image_dict[path]['labels'])

        # Only add items if there are any to add
        if image_names:
            self.search_bar_images.addItems(sorted(image_names))
        if label_names:
            self.search_bar_labels.addItems(sorted(label_names))

        # Restore search texts only if they're not empty
        if current_image_search:
            self.search_bar_images.setEditText(current_image_search)
        else:
            self.search_bar_images.setPlaceholderText("Type to search images")
        if current_label_search:
            self.search_bar_labels.setEditText(current_label_search)
        else:
            self.search_bar_labels.setPlaceholderText("Type to search labels")
