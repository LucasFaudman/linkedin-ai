from PyQt5 import QtCore as qtc


class DynamicSignalQObject(qtc.QObject):
    """QObject with the ability to dynamically add signals at runtime."""

    def add_signal(self, signal_name: str, *args, replace_if_exists=False) -> None:
        """
        Dynamically add a signal to a QObject instance by setting its __class__
        to a new type initialized with a pyqtSignal named <signal_name>.

        Example:

        dsqo = DynamicSignalQObject()

        dsqo.add_signal('dynamicSignal', str)

        dsqo.dynamicSignal.connect(dsqo.someSlotOrFunction)

        dsqo.dynamicSignal.emit("This signal was dynamically added to this QObject instance.")

        """
        if replace_if_exists or signal_name not in self.__class__.__dict__:
            # Set the class of the instance to a new type with the signal added
            self.__class__ = type(
                self.__class__.__name__,
                self.__class__.__bases__,
                {**self.__class__.__dict__, signal_name: qtc.pyqtSignal(*args)},
            )


# Example usage:
if __name__ == "__main__":
    dsqo = DynamicSignalQObject()

    dsqo.add_signal("dynamicSignal", str)

    @qtc.pyqtSlot(str)
    def someSlotOrFunction(x):
        print("Slot called:", x)

    dsqo.dynamicSignal.connect(someSlotOrFunction)

    dsqo.dynamicSignal.emit("This signal was dynamically added to this QObject instance.")
