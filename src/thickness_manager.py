from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import json
from datetime import datetime

@dataclass
class ThicknessGroup:
    """Represents a group of pads with the same thickness"""
    name: str
    pad_ids: Set[int]
    thickness: float
    created_at: datetime

class ThicknessChange:
    """Represents a change in thickness for undo/redo"""
    def __init__(self, pad_ids: Set[int], old_thickness: Dict[int, float], new_thickness: float):
        self.pad_ids = pad_ids
        self.old_thickness = old_thickness
        self.new_thickness = new_thickness
        self.timestamp = datetime.now()

class ThicknessManager:
    def __init__(self):
        self.groups: Dict[str, ThicknessGroup] = {}
        self.pad_to_group: Dict[int, str] = {}
        self.undo_stack: List[ThicknessChange] = []
        self.redo_stack: List[ThicknessChange] = []
        
    def create_group(self, name: str, pad_ids: Set[int], thickness: float) -> bool:
        """Create a new group with specified thickness"""
        if name in self.groups:
            return False
            
        # Remove pads from their current groups
        old_thicknesses = {}
        for pad_id in pad_ids:
            if pad_id in self.pad_to_group:
                old_group = self.groups[self.pad_to_group[pad_id]]
                old_thicknesses[pad_id] = old_group.thickness
                old_group.pad_ids.remove(pad_id)
                if not old_group.pad_ids:
                    del self.groups[old_group.name]
                    
        # Create new group
        self.groups[name] = ThicknessGroup(
            name=name,
            pad_ids=pad_ids,
            thickness=thickness,
            created_at=datetime.now()
        )
        
        # Update pad to group mapping
        for pad_id in pad_ids:
            self.pad_to_group[pad_id] = name
            
        # Add to undo stack
        self.undo_stack.append(ThicknessChange(pad_ids, old_thicknesses, thickness))
        self.redo_stack.clear()  # Clear redo stack when new change is made
        
        return True
        
    def get_pad_thickness(self, pad_id: int, default_thickness: float = 150.0) -> float:
        """Get the thickness for a specific pad"""
        if pad_id in self.pad_to_group:
            return self.groups[self.pad_to_group[pad_id]].thickness
        return default_thickness
        
    def get_pad_group(self, pad_id: int) -> Optional[ThicknessGroup]:
        """Get the group a pad belongs to"""
        if pad_id in self.pad_to_group:
            return self.groups[self.pad_to_group[pad_id]]
        return None
        
    def remove_group(self, name: str) -> bool:
        """Remove a group and reset its pads to default thickness"""
        if name not in self.groups:
            return False
            
        group = self.groups[name]
        old_thicknesses = {pad_id: group.thickness for pad_id in group.pad_ids}
        
        # Remove pad mappings
        for pad_id in group.pad_ids:
            del self.pad_to_group[pad_id]
            
        # Remove group
        del self.groups[name]
        
        # Add to undo stack
        self.undo_stack.append(ThicknessChange(
            group.pad_ids,
            old_thicknesses,
            None  # None indicates reset to default
        ))
        self.redo_stack.clear()
        
        return True
        
    def undo(self) -> Optional[Set[int]]:
        """Undo last thickness change, returns affected pad IDs"""
        if not self.undo_stack:
            return None
            
        change = self.undo_stack.pop()
        affected_pads = set()
        
        for pad_id in change.pad_ids:
            if pad_id in self.pad_to_group:
                # Remove from current group
                group_name = self.pad_to_group[pad_id]
                self.groups[group_name].pad_ids.remove(pad_id)
                if not self.groups[group_name].pad_ids:
                    del self.groups[group_name]
                del self.pad_to_group[pad_id]
                affected_pads.add(pad_id)
            
            if pad_id in change.old_thickness:
                # Restore old thickness
                group_name = f"Restored_{datetime.now().strftime('%H%M%S')}"
                self.groups[group_name] = ThicknessGroup(
                    name=group_name,
                    pad_ids={pad_id},
                    thickness=change.old_thickness[pad_id],
                    created_at=datetime.now()
                )
                self.pad_to_group[pad_id] = group_name
                affected_pads.add(pad_id)
                
        self.redo_stack.append(change)
        return affected_pads
        
    def redo(self) -> Optional[Set[int]]:
        """Redo last undone change, returns affected pad IDs"""
        if not self.redo_stack:
            return None
            
        change = self.redo_stack.pop()
        group_name = f"Redone_{datetime.now().strftime('%H%M%S')}"
        
        # Store old thicknesses for undo
        old_thicknesses = {}
        for pad_id in change.pad_ids:
            if pad_id in self.pad_to_group:
                old_thicknesses[pad_id] = self.groups[self.pad_to_group[pad_id]].thickness
                
        if change.new_thickness is not None:
            # Create new group with redone thickness
            self.groups[group_name] = ThicknessGroup(
                name=group_name,
                pad_ids=change.pad_ids,
                thickness=change.new_thickness,
                created_at=datetime.now()
            )
            
            # Update pad mappings
            for pad_id in change.pad_ids:
                self.pad_to_group[pad_id] = group_name
                
        else:
            # Reset pads to default
            for pad_id in change.pad_ids:
                if pad_id in self.pad_to_group:
                    del self.pad_to_group[pad_id]
                    
        self.undo_stack.append(ThicknessChange(
            change.pad_ids,
            old_thicknesses,
            change.new_thickness
        ))
        
        return change.pad_ids
        
    def clear(self):
        """Clear all thickness modifications and reset to initial state"""
        self.groups = {}
        self.pad_to_group = {}
        self.undo_stack = []
        self.redo_stack = []
        
    def save_to_file(self, filename: str) -> bool:
        """Save thickness settings to a file"""
        try:
            data = {
                'groups': {
                    name: {
                        'pad_ids': list(group.pad_ids),
                        'thickness': group.thickness,
                        'created_at': group.created_at.isoformat()
                    }
                    for name, group in self.groups.items()
                }
            }
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
            
    def load_from_file(self, filename: str) -> bool:
        """Load thickness settings from a file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            self.groups.clear()
            self.pad_to_group.clear()
            
            for name, group_data in data['groups'].items():
                self.groups[name] = ThicknessGroup(
                    name=name,
                    pad_ids=set(group_data['pad_ids']),
                    thickness=group_data['thickness'],
                    created_at=datetime.fromisoformat(group_data['created_at'])
                )
                
                for pad_id in group_data['pad_ids']:
                    self.pad_to_group[pad_id] = name
                    
            return True
        except Exception:
            return False

    def set_thickness(self, pad_ids: set, thickness: float):
        """Set thickness for a group of pads"""
        # Create a group name based on thickness
        group_name = f"Group_{thickness}um_{len(self.groups)}"
        
        # Record the change for undo/redo
        old_thicknesses = {}
        for pad_id in pad_ids:
            if pad_id in self.pad_to_group:
                old_group = self.groups[self.pad_to_group[pad_id]]
                old_thicknesses[pad_id] = old_group.thickness
                old_group.pad_ids.remove(pad_id)
                if not old_group.pad_ids:
                    del self.groups[old_group.name]
                    
        change = ThicknessChange(
            pad_ids=list(pad_ids),
            old_thickness=old_thicknesses,
            new_thickness=thickness
        )
        
        # Apply the change
        self.groups[group_name] = ThicknessGroup(
            name=group_name,
            pad_ids=pad_ids,
            thickness=thickness,
            created_at=datetime.now()
        )
        
        for pad_id in pad_ids:
            self.pad_to_group[pad_id] = group_name
            
        # Add to undo stack
        self.undo_stack.append(change)
        self.redo_stack.clear()  # Clear redo stack when new change is made
