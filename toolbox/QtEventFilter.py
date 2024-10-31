import warnings

from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtWidgets import QApplication, QMessageBox

warnings.filterwarnings("ignore", category=DeprecationWarning)


# ----------------------------------------------------------------------------------------------------------------------
# Classes
# ----------------------------------------------------------------------------------------------------------------------


class GlobalEventFilter(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.label_window = main_window.label_window
        self.annotation_window = main_window.annotation_window
        self.image_window = main_window.image_window
        self.deploy_model_dialog = main_window.deploy_model_dialog
        self.auto_distill_deploy_model_dialog = main_window.auto_distill_deploy_model_dialog

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.modifiers() & Qt.ControlModifier:

                # Handle WASD keys for selecting Label
                if event.key() in [Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D]:
                    self.label_window.handle_wasd_key(event.key())
                    return True

                # Handle hotkey for image classification prediction
                if event.key() == Qt.Key_1:
                    self.deploy_model_dialog.predict_classification()
                    return True

                # Handle hotkey for object detection prediction
                if event.key() == Qt.Key_2:
                    self.deploy_model_dialog.predict_detection()
                    return True

                # Handle hotkey for instance segmentation prediction
                if event.key() == Qt.Key_3:
                    self.deploy_model_dialog.predict_segmentation()
                    return True

                # Handle hotkey for auto distill prediction
                if event.key() == Qt.Key_4:
                    self.auto_distill_deploy_model_dialog.predict()
                    return True

                # Handle annotation cycling hotkeys
                if event.key() == Qt.Key_Left:
                    self.annotation_window.cycle_annotations(-1)
                    return True
                if event.key() == Qt.Key_Right:
                    self.annotation_window.cycle_annotations(1)
                    return True

                # Handle thumbnail cycling hotkeys
                if event.key() == Qt.Key_Up:
                    self.image_window.cycle_previous_image()
                    return True
                if event.key() == Qt.Key_Down:
                    self.image_window.cycle_next_image()
                    return True

                # Handle Delete key for Deleting selected annotations or images
                if event.key() == Qt.Key_Delete:

                    if self.annotation_window.selected_annotations:
                        self.annotation_window.delete_selected_annotation()
                        return True

                    # Rows are numbers, 0 indexed
                    if self.image_window.selected_image_path:
                        self.image_window.delete_selected_image()
                        return True

            # Unselect annotation on End key press
            if event.key() == Qt.Key_End:
                self.annotation_window.unselect_annotations()
                return True

            # Untoggle all tools on Home key press
            if event.key() == Qt.Key_Home:
                self.main_window.untoggle_all_tools()
                return True

            # Handle Escape key for exiting program
            if event.key() == Qt.Key_Escape:
                self.show_exit_confirmation_dialog()
                return True

        # Return False for other events to allow them to be processed by the target object
        return False

    def show_exit_confirmation_dialog(self):
        # noinspection PyTypeChecker
        reply = QMessageBox.question(None,
                                     'Confirm Exit',
                                     'Are you sure you want to exit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()