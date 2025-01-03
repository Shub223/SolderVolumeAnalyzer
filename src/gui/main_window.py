from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QFileDialog, QLabel, QTableWidget, QMessageBox,
                            QStatusBar, QSplitter)
from PyQt6.QtCore import Qt
from src.gui.pcb_view import PCBView
from src.gui.volume_table import VolumeTable
from src.gerber_parser import GerberParser
import logging
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerber Solder Volume Analyzer")
        
        # Initialize components
        self.gerber_parser = GerberParser()
        self.current_file = None
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create splitter for PCB view and table
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Create PCB view container with fixed aspect ratio
        pcb_container = QWidget()
        pcb_layout = QVBoxLayout(pcb_container)
        pcb_layout.setContentsMargins(0, 0, 0, 0)
        pcb_layout.setSpacing(0)
        
        # Create PCB view
        self.pcb_view = PCBView()
        pcb_layout.addWidget(self.pcb_view)
        
        # Create volume table
        self.volume_table = VolumeTable()
        
        # Add widgets to splitter
        splitter.addWidget(pcb_container)
        splitter.addWidget(self.volume_table)
        
        # Set initial splitter sizes (70% PCB view, 30% table)
        splitter.setSizes([700, 300])
        
        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        main_layout.addLayout(button_layout)
        
        # Add load button
        load_button = QPushButton("Load Gerber File")
        load_button.clicked.connect(self._load_gerber_file)
        button_layout.addWidget(load_button)
        
        # Add export button
        export_button = QPushButton("Export Data")
        export_button.clicked.connect(self._export_data)
        button_layout.addWidget(export_button)
        
        # Add zoom controls
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)
        zoom_in_button = QPushButton("Zoom In")
        zoom_out_button = QPushButton("Zoom Out")
        zoom_fit_button = QPushButton("Fit View")
        zoom_in_button.clicked.connect(self.pcb_view.zoom_in)
        zoom_out_button.clicked.connect(self.pcb_view.zoom_out)
        zoom_fit_button.clicked.connect(self.pcb_view.fit_view)
        zoom_layout.addWidget(zoom_in_button)
        zoom_layout.addWidget(zoom_out_button)
        zoom_layout.addWidget(zoom_fit_button)
        button_layout.addLayout(zoom_layout)
        
        # Add spacer to push buttons to the left
        button_layout.addStretch()
        
        # Add status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Set window size and center it
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        self._center_window()
        
        # Initialize status
        self._update_status()
        
    def _load_gerber_file(self):
        """Handle Gerber file loading"""
        try:
            logging.info("Opening file dialog...")
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Gerber File",
                "",
                "Gerber Files (*.gbr *.ger);;All Files (*.*)"
            )

            if file_path:
                self.current_file = file_path
                logging.info(f"Selected file: {file_path}")
                # Parse Gerber file
                logging.info("Starting to parse file...")
                pads = self.gerber_parser.parse_file(file_path)
                logging.info(f"Successfully parsed {len(pads)} pads")
                
                # Update PCB view
                logging.info("Updating PCB view...")
                self.pcb_view.set_pads(pads)
                
                # Update volume table
                logging.info("Updating volume table...")
                self.volume_table.update_data(pads)
                
                # Update status
                self._update_status(pads)
                logging.info("GUI update complete")
        except Exception as e:
            logging.error(f"Error loading Gerber file: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load Gerber file: {str(e)}")
    
    def _export_data(self):
        """Handle data export"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Data",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*.*)"
            )
            
            if file_path:
                self.volume_table.export_data(file_path)
                self.statusBar.showMessage(f"Data exported to {file_path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
            
    def _update_status(self, pads=None):
        """Update status bar with current information"""
        if not pads:
            self.statusBar.showMessage("No file loaded")
            return
            
        # Calculate total volume
        total_volume = sum(pad.volume for pad in pads)
        
        # Create status message
        file_name = os.path.basename(self.current_file) if self.current_file else "No file"
        status_msg = f"File: {file_name} | Pads: {len(pads)} | Total Volume: {total_volume:.2f} mm³"
        self.statusBar.showMessage(status_msg)

    def _center_window(self):
        """Center the window on the screen"""
        frame_geometry = self.frameGeometry()
        screen = self.screen()
        if screen:
            center_point = screen.availableGeometry().center()
            frame_geometry.moveCenter(center_point)
            self.move(frame_geometry.topLeft())
