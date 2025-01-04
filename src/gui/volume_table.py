from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from typing import List, Dict
from src.gerber_parser import PadInfo
import logging

class VolumeTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.pads: List[PadInfo] = []
        self.pad_volumes: Dict[int, float] = {}
        
    def _init_ui(self):
        """Initialize the table UI"""
        # Set up columns
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels([
            "Pad ID",
            "Area (mm²)",
            "Thickness (µm)",
            "Volume (mm³)"
        ])
        
        # Set column stretching
        header = self.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            
        # Make table read-only
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
    def update_pads(self, pads: List[PadInfo]):
        """Update the table with new pad data"""
        self.pads = pads
        self._refresh_table()
        
    def update_pad_thickness(self, pad_id: int, thickness: float):
        """Update the thickness and volume for a specific pad"""
        # Find the pad in our data
        for row in range(self.rowCount()):
            if int(self.item(row, 0).text()) == pad_id:
                # Update thickness
                self.setItem(row, 2, QTableWidgetItem(f"{thickness:.1f}"))
                
                # Update volume
                area = float(self.item(row, 1).text())
                volume = (area * thickness) / 1000  # Convert to mm³
                self.setItem(row, 3, QTableWidgetItem(f"{volume:.3f}"))
                self.pad_volumes[pad_id] = volume
                break
                
    def _refresh_table(self):
        """Refresh the entire table with current pad data"""
        try:
            logging.info(f"Refreshing table with {len(self.pads)} pads")
            self.setRowCount(len(self.pads))
            self.pad_volumes.clear()
            
            for row, pad in enumerate(self.pads):
                try:
                    # Pad ID
                    self.setItem(row, 0, QTableWidgetItem(str(pad.id)))
                    
                    # Area (mm²)
                    try:
                        area = float(pad.geometry.area)
                        if not area > 0:  # Check for valid area
                            logging.warning(f"Invalid area for pad {pad.id}: {area}")
                            area = 0.0
                    except Exception as e:
                        logging.error(f"Error calculating area for pad {pad.id}: {str(e)}")
                        area = 0.0
                        
                    self.setItem(row, 1, QTableWidgetItem(f"{area:.3f}"))
                    
                    # Default thickness (µm)
                    thickness = 150.0  # Default thickness
                    self.setItem(row, 2, QTableWidgetItem(f"{thickness:.1f}"))
                    
                    # Volume (mm³)
                    try:
                        volume = (area * thickness) / 1000
                        if not volume >= 0:  # Check for valid volume
                            logging.warning(f"Invalid volume for pad {pad.id}: {volume}")
                            volume = 0.0
                    except Exception as e:
                        logging.error(f"Error calculating volume for pad {pad.id}: {str(e)}")
                        volume = 0.0
                        
                    self.setItem(row, 3, QTableWidgetItem(f"{volume:.3f}"))
                    self.pad_volumes[pad.id] = volume
                    
                except Exception as e:
                    logging.error(f"Error processing pad {pad.id} at row {row}: {str(e)}")
                    continue
                    
            try:
                self.sortItems(0, Qt.SortOrder.AscendingOrder)
            except Exception as e:
                logging.error(f"Error sorting table: {str(e)}")
                
            logging.info("Table refresh completed successfully")
            
        except Exception as e:
            logging.error(f"Error refreshing table: {str(e)}")
            logging.error("Stack trace:", exc_info=True)
            raise
            
    def get_total_volume(self) -> float:
        """Calculate total volume of all pads"""
        try:
            total = sum(self.pad_volumes.values())
            if not total >= 0:  # Check for valid total
                logging.warning(f"Invalid total volume: {total}")
                return 0.0
            return total
        except Exception as e:
            logging.error(f"Error calculating total volume: {str(e)}")
            return 0.0
            
    def reset(self):
        """Clear the table and reset all data"""
        self.setRowCount(0)
        self.pads.clear()
        self.pad_volumes.clear()
