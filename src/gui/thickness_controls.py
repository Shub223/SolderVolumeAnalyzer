from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QLineEdit, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import Set, Optional, Dict
import logging

class ThicknessControls(QWidget):
    thickness_changed = pyqtSignal(set, float)  # pad_ids, new_thickness
    selection_mode_changed = pyqtSignal(bool)  # is_selection_mode
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Selection Controls
        selection_group = QGroupBox("Selection Tools")
        selection_layout = QHBoxLayout()
        
        self.select_mode_btn = QPushButton("Selection Mode")
        self.select_mode_btn.setCheckable(True)
        self.select_mode_btn.toggled.connect(self._on_selection_mode_changed)
        
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self._on_clear_selection)
        
        selection_layout.addWidget(self.select_mode_btn)
        selection_layout.addWidget(self.clear_selection_btn)
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # Thickness Controls
        thickness_group = QGroupBox("Thickness Controls")
        thickness_layout = QVBoxLayout()
        
        # Current Selection Info
        info_layout = QHBoxLayout()
        self.selection_count_label = QLabel("Selected: 0 pads")
        info_layout.addWidget(self.selection_count_label)
        thickness_layout.addLayout(info_layout)
        
        # Thickness Input
        thickness_input_layout = QHBoxLayout()
        thickness_input_layout.addWidget(QLabel("Thickness:"))
        
        self.thickness_input = QSpinBox()
        self.thickness_input.setRange(1, 1000)
        self.thickness_input.setValue(150)
        self.thickness_input.setSuffix(" µm")
        thickness_input_layout.addWidget(self.thickness_input)
        
        self.apply_thickness_btn = QPushButton("Apply")
        self.apply_thickness_btn.clicked.connect(self._on_apply_thickness)
        thickness_input_layout.addWidget(self.apply_thickness_btn)
        thickness_layout.addLayout(thickness_input_layout)
        
        # Quick Presets
        presets_layout = QHBoxLayout()
        presets = [70, 100, 150, 200]
        for preset in presets:
            btn = QPushButton(f"{preset}µm")
            btn.clicked.connect(lambda checked, t=preset: self.thickness_input.setValue(t))
            presets_layout.addWidget(btn)
        thickness_layout.addLayout(presets_layout)
        
        # Modified Areas Table
        self.areas_table = QTableWidget(0, 4)
        self.areas_table.setHorizontalHeaderLabels(["Name", "Pads", "Thickness", "Actions"])
        header = self.areas_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.areas_table.setColumnWidth(1, 60)
        self.areas_table.setColumnWidth(2, 80)
        self.areas_table.setColumnWidth(3, 100)
        thickness_layout.addWidget(self.areas_table)
        
        # New Area Controls
        new_area_layout = QHBoxLayout()
        self.area_name_input = QLineEdit()
        self.area_name_input.setPlaceholderText("Area Name")
        new_area_layout.addWidget(self.area_name_input)
        
        self.save_area_btn = QPushButton("Save Area")
        self.save_area_btn.clicked.connect(self._on_save_area)
        new_area_layout.addWidget(self.save_area_btn)
        thickness_layout.addLayout(new_area_layout)
        
        thickness_group.setLayout(thickness_layout)
        layout.addWidget(thickness_group)
        
        self.setLayout(layout)
        
        # Initialize state
        self._selected_pads: Set[int] = set()
        self._modified_areas: Dict[str, Dict] = {}
        self._update_ui_state()
        
    def _on_selection_mode_changed(self, enabled: bool):
        """Handle selection mode toggle"""
        self.selection_mode_changed.emit(enabled)
        
    def _on_clear_selection(self):
        """Clear the current selection"""
        self._selected_pads.clear()
        self._update_ui_state()
        
    def _on_apply_thickness(self):
        """Apply the current thickness to selected pads"""
        if self._selected_pads:
            thickness = self.thickness_input.value()
            self.thickness_changed.emit(self._selected_pads, thickness)
            
    def _on_save_area(self):
        """Save the current selection as a named area"""
        name = self.area_name_input.text().strip()
        if not name:
            return
            
        if not self._selected_pads:
            return
            
        # Save the area
        self._modified_areas[name] = {
            'pads': self._selected_pads.copy(),
            'thickness': self.thickness_input.value()
        }
        
        # Update the table
        self._update_areas_table()
        
        # Clear the name input
        self.area_name_input.clear()
        
    def _update_areas_table(self):
        """Update the modified areas table"""
        self.areas_table.setRowCount(len(self._modified_areas))
        
        for row, (name, data) in enumerate(self._modified_areas.items()):
            # Name
            self.areas_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Pad count
            self.areas_table.setItem(row, 1, QTableWidgetItem(str(len(data['pads']))))
            
            # Thickness
            self.areas_table.setItem(row, 2, QTableWidgetItem(f"{data['thickness']}µm"))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, n=name: self._edit_area(n))
            
            del_btn = QPushButton("Del")
            del_btn.clicked.connect(lambda checked, n=name: self._delete_area(n))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(del_btn)
            self.areas_table.setCellWidget(row, 3, actions_widget)
            
    def _edit_area(self, name: str):
        """Load an area for editing"""
        if name in self._modified_areas:
            area = self._modified_areas[name]
            self._selected_pads = area['pads'].copy()
            self.thickness_input.setValue(area['thickness'])
            self.area_name_input.setText(name)
            self._update_ui_state()
            
    def _delete_area(self, name: str):
        """Delete a modified area"""
        if name in self._modified_areas:
            del self._modified_areas[name]
            self._update_areas_table()
            
    def update_selection(self, selected_pads: Set[int]):
        """Update the current selection"""
        self._selected_pads = selected_pads
        self._update_ui_state()
        
    def _update_ui_state(self):
        """Update UI elements based on current state"""
        # Update selection count
        self.selection_count_label.setText(f"Selected: {len(self._selected_pads)} pads")
        
        # Enable/disable controls based on selection
        has_selection = len(self._selected_pads) > 0
        self.apply_thickness_btn.setEnabled(has_selection)
        self.save_area_btn.setEnabled(has_selection)
        self.area_name_input.setEnabled(has_selection)
        
    def get_modified_areas(self) -> Dict[str, Dict]:
        """Get all modified areas"""
        return self._modified_areas.copy()
        
    def load_modified_areas(self, areas: Dict[str, Dict]):
        """Load modified areas from saved data"""
        self._modified_areas = areas.copy()
        self._update_areas_table()

    def reset(self):
        """Reset all controls to their initial state"""
        self.thickness_input.setValue(150)  # Default thickness
        self.select_mode_btn.setChecked(False)
        self.areas_table.setRowCount(0)
        self.setEnabled(False)
