import warnings
import pkg_resources

import torch
import numpy as np

from PyQt5.QtGui import QImage

warnings.filterwarnings("ignore", category=DeprecationWarning)


# ----------------------------------------------------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------------------------------------------------


def get_icon_path(icon_name):
    """

    :param icon_name:
    :return:
    """
    return pkg_resources.resource_filename('toolbox', f'icons/{icon_name}')


def get_available_device():
    """
    Get available devices

    :param self:
    :return:
    """
    devices = ['cpu',]
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            devices.append(f'cuda:{i}')
    if torch.backends.mps.is_available():
        devices.append('mps')
    return devices


def preprocess_image(image):
    """
    Ensure the image has correct dimensions (h, w, 3).

    :param image:
    :return:
    """
    if len(image.shape) == 2:  # Grayscale image
        image = np.stack((image,) * 3, axis=-1)
    elif len(image.shape) == 3:
        if image.shape[2] == 4:  # RGBA image
            image = image[..., :3]  # Drop alpha channel
        elif image.shape[2] != 3:  # If channels are not last
            # Check if channels are first (c, h, w)
            if image.shape[0] == 3:
                image = np.transpose(image, (1, 2, 0))
            elif image.shape[0] == 4:  # RGBA in channels-first format
                image = np.transpose(image, (1, 2, 0))[..., :3]
            else:
                raise ValueError("Image must have 3 or 4 color channels")
    else:
        raise ValueError("Image must be 2D or 3D array")

    return image


def rasterio_to_numpy(rasterio_src):
    """
    Convert a Rasterio dataset to a NumPy array.

    :param rasterio_src:
    :return:
    """
    return rasterio_src.read().transpose(1, 2, 0)


def pixmap_to_numpy(pixmap):
    """
    Convert a QPixmap to a NumPy array.

    :param pixmap:
    :return:
    """
    # Convert QPixmap to QImage
    image = pixmap.toImage()
    # Get image dimensions
    width = image.width()
    height = image.height()

    # Convert QImage to numpy array
    byte_array = image.bits().asstring(width * height * 4)  # 4 for RGBA
    numpy_array = np.frombuffer(byte_array, dtype=np.uint8).reshape((height, width, 4))

    # If the image format is ARGB32, swap the first and last channels (A and B)
    if format == QImage.Format_ARGB32:
        numpy_array = numpy_array[:, :, [2, 1, 0, 3]]

    return numpy_array[:, :, :3]


def qimage_to_numpy(qimage):
    """
    Convert a QImage to a NumPy array.

    :param qimage:
    :return:
    """
    # Get image dimensions
    width = qimage.width()
    height = qimage.height()
    # Get the number of bytes per line
    bytes_per_line = qimage.bytesPerLine()
    # Convert QImage to numpy array
    byte_array = qimage.bits().asstring(height * bytes_per_line)
    image = np.frombuffer(byte_array, dtype=np.uint8).reshape((height, width, 4))
    return image[:, :, :3]  # Remove the alpha channel if present


def console_user(error_msg):
    """

    :param error_msg:
    :return:
    """
    url = "https://github.com/Jordan-Pierce/CoralNet-Toolbox/issues"

    print(f"\n\n\nUh oh! It looks like something went wrong!")
    print(f"{'∨' * 60}")
    print(f"\n{error_msg}\n")
    print(f"{'^' * 60}")
    print(f"Please, create a ticket and copy this error so we can get this fixed:")
    print(f"{url}")