import pkg_resources

import torch

import warnings


warnings.filterwarnings("ignore", category=DeprecationWarning)


# ----------------------------------------------------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------------------------------------------------


def get_available_device():
    """
    Get available devices

    :param self:
    :return:
    """
    devices = []
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            devices.append(f'cuda:{i}')
    if torch.backends.mps.is_available():
        devices.append('mps')
    devices.append('cpu')
    return devices


def get_icon_path(icon_name):
    """

    :param icon_name:
    :return:
    """
    return pkg_resources.resource_filename('toolbox', f'icons/{icon_name}')


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