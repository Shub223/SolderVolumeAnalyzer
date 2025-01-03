import sys
import logging
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

# Configure logging at application start
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # This ensures our configuration takes precedence
)

def main():
    logging.info("Starting application...")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    logging.info("Application window shown")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
