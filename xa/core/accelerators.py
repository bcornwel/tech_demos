"""
This file contains utilties to manage accelerators
"""


class Accelerator:
    def get_utilization(self) -> dict:
        """
        Get the utilization of the accelerator
        """
        raise NotImplementedError("Utilization not implemented")
    
    def get_temperature(self) -> dict:
        """
        Get the temperature of the accelerator
        """
        raise NotImplementedError("Temperature not implemented")

    def get_power(self) -> dict:
        """
        Get the power of the accelerator
        """
        raise NotImplementedError("Power not implemented")

    def reset(self) -> bool:
        """
        Reset the accelerator
        """
        raise NotImplementedError("Reset not implemented")

    # other functions?

class Gaudi2(Accelerator):
    pass

class Gaudi3(Accelerator):
    pass

class FS1(Accelerator):  # falcon shores
    pass

class JS1(Accelerator):  # jaguar shores
    pass


def get_accelerators() -> dict:
    """
    Get the accelerators available on the system
    """
    pass

def get_accelerator(device_id) -> dict:
    """
    Get the accelerator with the specified device id
    """
    pass

