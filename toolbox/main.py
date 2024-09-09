# TODO
#   - update pre-warm inference based on input size of model
#   - CoralNet tools
#   - Clean up QImage, Rasterio Image, PixMap
#   - add tensorboard option for modeling training
#   - file explorer for annotations to edit, delete in batches
#   - master transparency for all annotations / classes
#   - restart training from yaml file
#   - add importing of coralnet predictions / output
#   - Consider removing the visual updates when making predictions for faster inference

import traceback
from PyQt5.QtWidgets import QApplication
from toolbox.QtMain import MainWindow
from toolbox.utilities import console_user


# ----------------------------------------------------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------------------------------------------------


def run():
    try:
        app = QApplication([])
        app.setStyle('WindowsXP')
        main_window = MainWindow()
        main_window.show()
        app.exec_()

    except Exception as e:
        console_user(f"{e}\n{traceback.format_exc()}")


if __name__ == '__main__':
    run()