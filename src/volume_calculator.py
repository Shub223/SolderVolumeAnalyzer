from typing import List, Dict
from src.gerber_parser import PadInfo

class VolumeCalculator:
    def __init__(self):
        self.stepped_areas: Dict[int, float] = {}  # pad_id -> thickness

    def calculate_pad_volume(self, pad: PadInfo) -> float:
        """Calculate volume for a single pad"""
        thickness = self.stepped_areas.get(pad.id, pad.thickness)
        return pad.area * thickness

    def calculate_total_volume(self, pads: List[PadInfo]) -> float:
        """Calculate total volume for all pads"""
        return sum(self.calculate_pad_volume(pad) for pad in pads)

    def set_stepped_area(self, pad_ids: List[int], thickness: float):
        """Set custom thickness for specific pads"""
        for pad_id in pad_ids:
            self.stepped_areas[pad_id] = thickness

    def reset_stepped_area(self, pad_ids: List[int]):
        """Reset thickness to default for specific pads"""
        for pad_id in pad_ids:
            if pad_id in self.stepped_areas:
                del self.stepped_areas[pad_id]

    def get_pad_summary(self, pad: PadInfo) -> dict:
        """Get summary information for a pad"""
        volume = self.calculate_pad_volume(pad)
        thickness = self.stepped_areas.get(pad.id, pad.thickness)
        
        return {
            'id': pad.id,
            'type': pad.shape_type,
            'area': pad.area,
            'thickness': thickness,
            'volume': volume,
            'coordinates': pad.coordinates,
            'is_stepped': pad.id in self.stepped_areas
        }
