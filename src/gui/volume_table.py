from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
import pandas as pd
from typing import List
from src.gerber_parser import PadInfo
import logging

class VolumeTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self._setup_table()
        
    def _setup_table(self):
        """Setup the table structure"""
        # Set columns
        columns = ['Pad ID', 'Type', 'Area (mm²)', 'Thickness (µm)', 'Volume (mm³)']
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # Set column widths
        header = self.horizontalHeader()
        for i in range(len(columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            
        # Enable sorting
        self.setSortingEnabled(True)
        
    def update_data(self, pads: List[PadInfo]):
        """Update table with new pad data"""
        logging.info(f"Updating volume table with {len(pads)} pads")
        self.setSortingEnabled(False)
        self.setRowCount(0)
        
        for pad in pads:
            row = self.rowCount()
            self.insertRow(row)
            
            # Add items
            self.setItem(row, 0, QTableWidgetItem(str(pad.id)))
            self.setItem(row, 1, QTableWidgetItem(pad.shape_type))
            self.setItem(row, 2, QTableWidgetItem(f"{pad.area:.2f}"))
            self.setItem(row, 3, QTableWidgetItem(f"{pad.thickness*1000:.0f}"))
            self.setItem(row, 4, QTableWidgetItem(f"{pad.volume:.2f}"))
            
            # Set alignment
            for col in range(self.columnCount()):
                item = self.item(row, col)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
        self.setSortingEnabled(True)
        logging.info("Volume table update complete")
        
    def export_data(self, filepath: str):
        """Export table data to file"""
        try:
            logging.info(f"Exporting data to {filepath}")
            # Create DataFrame from table data
            data = []
            for row in range(self.rowCount()):
                row_data = {}
                for col in range(self.columnCount()):
                    header = self.horizontalHeaderItem(col).text()
                    item = self.item(row, col)
                    row_data[header] = item.text() if item else ""
                data.append(row_data)
                
            df = pd.DataFrame(data)
            
            # Export based on file extension
            if filepath.endswith('.xlsx'):
                df.to_excel(filepath, index=False)
            else:  # Default to CSV
                df.to_csv(filepath, index=False)
                
            logging.info("Data export complete")
        except Exception as e:
            logging.error(f"Error exporting data: {str(e)}")
            raise
