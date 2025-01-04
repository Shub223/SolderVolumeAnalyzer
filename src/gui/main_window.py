from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
from .gl_pcb_view import GLPCBView
from .volume_table import VolumeTable
from .thickness_controls import ThicknessControls
from src.gerber_parser import GerberParser, PadInfo
from src.thickness_manager import ThicknessManager
import logging

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerber Solder Volume Analyzer")
        self.resize(1200, 800)
        
        # Initialize components
        self.pcb_view = GLPCBView()
        self.volume_table = VolumeTable()
        self.thickness_controls = ThicknessControls()
        self.thickness_manager = ThicknessManager()
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        
        # Center the window
        self._center_window()
        
    def _setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top toolbar
        toolbar_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Gerber")
        self.load_button.clicked.connect(self.load_gerber_file)
        toolbar_layout.addWidget(self.load_button)
        
        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self._on_save_settings)
        toolbar_layout.addWidget(self.save_settings_button)
        
        self.load_settings_button = QPushButton("Load Settings")
        self.load_settings_button.clicked.connect(self._on_load_settings)
        toolbar_layout.addWidget(self.load_settings_button)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # Create main content layout
        content_layout = QHBoxLayout()
        
        # Left side: PCB view and thickness controls
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.pcb_view, stretch=2)
        left_layout.addWidget(self.thickness_controls, stretch=1)
        content_layout.addLayout(left_layout, stretch=2)
        
        # Right side: Volume table
        content_layout.addWidget(self.volume_table, stretch=1)
        
        main_layout.addLayout(content_layout)
        
    def _setup_connections(self):
        # Connect PCB view signals
        self.pcb_view.selection_changed.connect(self._on_selection_changed)
        
        # Connect thickness controls signals
        self.thickness_controls.thickness_changed.connect(self._on_thickness_changed)
        self.thickness_controls.selection_mode_changed.connect(self.pcb_view.set_selection_mode)
        
    def load_gerber_file(self):
        """Open a file dialog and load the selected Gerber file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Gerber File",
            "",
            "Gerber Files (*.gbr *.gtl *.gbl *.gto *.gbo *.gts *.gbs *.gtp *.gbp);;All Files (*.*)"
        )
        
        if file_name:
            logging.info(f"Loading Gerber file: {file_name}")
            try:
                # Stage 1: Parse Gerber file
                logging.info("=== Stage 1: Parsing Gerber file ===")
                parser = GerberParser()
                pads = parser.parse_file(file_name)
                
                if not pads:
                    logging.warning("No pads found in Gerber file")
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "No pads were found in the Gerber file. Please check if this is the correct file."
                    )
                    return
                    
                logging.info(f"Stage 1 complete: Successfully loaded {len(pads)} pads")
                
                # Stage 2: Reset application state
                logging.info("=== Stage 2: Resetting application state ===")
                try:
                    self.thickness_manager.clear()
                    self.thickness_controls.reset()
                    logging.info("Stage 2 complete: Application state reset")
                except Exception as e:
                    logging.error(f"Stage 2 failed: Error resetting application state: {str(e)}")
                    logging.error("Stack trace:", exc_info=True)
                    raise
                
                # Stage 3: Update PCB view
                logging.info("=== Stage 3: Updating PCB view ===")
                try:
                    self.pcb_view.set_pads(pads)
                    # Validate PCB view state
                    if not self.pcb_view.ctx:
                        raise RuntimeError("OpenGL context not initialized")
                    if not self.pcb_view.vao:
                        raise RuntimeError("Vertex Array Object not created")
                    if not self.pcb_view.mvp:
                        raise RuntimeError("MVP matrix not initialized")
                    logging.info("Stage 3 complete: PCB view updated")
                except Exception as e:
                    logging.error(f"Stage 3 failed: Error updating PCB view: {str(e)}")
                    logging.error("Stack trace:", exc_info=True)
                    raise Exception(f"Failed to display PCB: {str(e)}")
                
                # Stage 4: Update volume table
                logging.info("=== Stage 4: Updating volume table ===")
                try:
                    self.volume_table.update_pads(pads)
                    # Validate table state
                    if self.volume_table.rowCount() != len(pads):
                        raise RuntimeError(f"Table row count mismatch: {self.volume_table.rowCount()} != {len(pads)}")
                    logging.info("Stage 4 complete: Volume table updated")
                except Exception as e:
                    logging.error(f"Stage 4 failed: Error updating volume table: {str(e)}")
                    logging.error("Stack trace:", exc_info=True)
                    raise Exception(f"Failed to update volume table: {str(e)}")
                
                # Stage 5: Final setup
                logging.info("=== Stage 5: Completing setup ===")
                try:
                    # Enable thickness controls
                    self.thickness_controls.setEnabled(True)
                    logging.info("Stage 5 complete: Setup finished")
                    logging.info("=== All stages completed successfully ===")
                except Exception as e:
                    logging.error(f"Stage 5 failed: Error in final setup: {str(e)}")
                    logging.error("Stack trace:", exc_info=True)
                    raise
                
            except FileNotFoundError:
                msg = "The selected file could not be found. It may have been moved or deleted."
                logging.error(msg)
                QMessageBox.critical(self, "Error", msg)
            except PermissionError:
                msg = "Permission denied accessing the file. Please check file permissions."
                logging.error(msg)
                QMessageBox.critical(self, "Error", msg)
            except Exception as e:
                logging.error(f"Error loading Gerber file: {str(e)}")
                logging.error("Stack trace:", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load Gerber file: {str(e)}\n\nPlease check if the file is valid."
                )
                
    def _on_selection_changed(self, selected_pads: set):
        self.thickness_controls.update_selection(selected_pads)
        
    def _on_thickness_changed(self, pad_ids: set, thickness: float):
        """Handle thickness changes"""
        # Update thickness manager
        self.thickness_manager.set_thickness(pad_ids, thickness)
        
        # Update PCB view
        for pad_id in pad_ids:
            self.pcb_view.update_pad_thickness_visual(pad_id, True)
            
        # Update volume table
        for pad_id in pad_ids:
            self.volume_table.update_pad_thickness(pad_id, thickness)
        
    def _update_volume_table(self):
        """Update the volume table with current pad data"""
        if not hasattr(self.pcb_view, 'pads'):
            return
            
        # Update volumes based on current thicknesses
        updated_pads = []
        for pad in self.pcb_view.pads:
            # Create a new PadInfo with updated thickness and volume
            thickness = self.thickness_manager.get_pad_thickness(pad.id)
            volume = pad.area * thickness / 1000  # Convert to mm³
            updated_pad = PadInfo(
                id=pad.id,
                coordinates=pad.coordinates,
                shape_type=pad.shape_type,
                geometry=pad.geometry,
                area=pad.area,
                thickness=thickness,
                volume=volume
            )
            updated_pads.append(updated_pad)
            
        # Update the table
        self.volume_table.update_data(updated_pads)
        
    def _on_save_settings(self):
        """Save thickness settings to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Thickness Settings",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            if self.thickness_manager.save_to_file(file_path):
                QMessageBox.information(
                    self,
                    "Success",
                    "Thickness settings saved successfully!"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to save thickness settings"
                )
                
    def _on_load_settings(self):
        """Load thickness settings from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Thickness Settings",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            if self.thickness_manager.load_from_file(file_path):
                # Update visuals for all modified pads
                for group in self.thickness_manager.groups.values():
                    for pad_id in group.pad_ids:
                        self.pcb_view.update_pad_thickness_visual(pad_id, True)
                        
                # Update volume calculations
                self._update_volume_table()
                
                QMessageBox.information(
                    self,
                    "Success",
                    "Thickness settings loaded successfully!"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to load thickness settings"
                )
                
    def _center_window(self):
        """Center the window on the screen"""
        frame_geometry = self.frameGeometry()
        screen = self.screen()
        center_point = screen.availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
