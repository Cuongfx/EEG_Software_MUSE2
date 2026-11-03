import sys
from PyQt6.QtWidgets import QApplication
from gui.pyqt_interface import PyQtInterface
from muse.muselsl_interface import MuselslInterface

def main():
    # Initialize the Muse headset connection
    muselsl = MuselslInterface()
    muselsl.start_streaming()

    # Start the GUI application
    app = QApplication(sys.argv)
    interface = PyQtInterface()
    interface.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()