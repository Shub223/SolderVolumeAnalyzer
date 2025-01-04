import sys
import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def setup_logging():
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with timestamp
    log_file = os.path.join(logs_dir, f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    # Set specific loggers to different levels
    logging.getLogger('src.gerber_parser').setLevel(logging.WARNING)  # Only show warnings and errors for parser
    logging.getLogger('src.gui').setLevel(logging.INFO)
    logging.getLogger('src.thickness_manager').setLevel(logging.INFO)
    
    logging.info("Logging initialized")
    logging.info(f"Log file: {log_file}")

def main():
    """Main application entry point"""
    # Set up logging
    setup_logging()
    
    # Create and run application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
