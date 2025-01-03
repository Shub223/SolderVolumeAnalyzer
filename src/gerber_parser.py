from dataclasses import dataclass
from typing import List, Tuple, Union, Optional
from shapely.geometry import Polygon, Point
import numpy as np
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class PadInfo:
    """Represents a pad with its properties and calculated volumes"""
    id: int
    shape_type: str  # 'circle', 'rectangle', 'polygon'
    coordinates: Tuple[float, float]
    geometry: Union[Point, Polygon]
    area: float
    volume: float
    thickness: float = 0.15  # default 150 microns

class GerberParser:
    def __init__(self):
        self.pads: List[PadInfo] = []
        self._pad_counter = 0
        self._current_aperture = None
        self._apertures = {}  # Dictionary to store aperture definitions
        self._scale = 1.0  # For unit conversion
        self._current_x = 0.0
        self._current_y = 0.0

    def parse_file(self, filepath: str) -> List[PadInfo]:
        """Parse a Gerber file and extract pad information"""
        try:
            logging.info(f"Starting to parse Gerber file: {filepath}")
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            logging.info(f"Read {len(lines)} lines from file")

            # Process each line in the file
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                logging.debug(f"Processing line {line_num}: {line}")

                # Parse format specification
                if line.startswith('%FSLAX'):
                    logging.info(f"Found format specification: {line}")
                    self._parse_format(line)
                # Parse aperture definition
                elif line.startswith('%ADD'):
                    logging.info(f"Found aperture definition: {line}")
                    self._parse_aperture(line)
                # Parse operation
                elif line.startswith('D'):
                    logging.debug(f"Found operation: {line}")
                    self._parse_operation(line)
                # Parse coordinate
                elif re.match(r'^[XY]', line):
                    logging.debug(f"Found coordinate: {line}")
                    self._parse_coordinate(line)

            logging.info(f"Finished parsing. Found {len(self.pads)} pads.")
            return self.pads
        except Exception as e:
            logging.error(f"Error parsing Gerber file: {str(e)}", exc_info=True)
            raise Exception(f"Error parsing Gerber file: {str(e)}")

    def _parse_format(self, line: str):
        """Parse format specification (e.g., %FSLAX36Y36*%)"""
        match = re.match(r'%FSLAX(\d)(\d)Y(\d)(\d)', line)
        if match:
            x_int, x_dec, y_int, y_dec = map(int, match.groups())
            self._scale = 10 ** -x_dec  # Use X decimal places for scaling
            logging.info(f"Set scale to {self._scale} (x_int={x_int}, x_dec={x_dec}, y_int={y_int}, y_dec={y_dec})")
        else:
            logging.warning(f"Could not parse format specification: {line}")

    def _parse_aperture(self, line: str):
        """Parse aperture definition (e.g., %ADD10C,0.0100*%)"""
        match = re.match(r'%ADD(\d+)([A-Z]),([\d.]+)', line)
        if match:
            number, type_, size = match.groups()
            self._apertures[number] = {
                'type': type_,
                'size': float(size)
            }
            logging.info(f"Added aperture {number}: type={type_}, size={size}")
        else:
            logging.warning(f"Could not parse aperture definition: {line}")

    def _parse_operation(self, line: str):
        """Parse operation code (e.g., D03*)"""
        if not line.startswith('D'):
            return
            
        # Extract the operation code (remove trailing *)
        code = line[1:].rstrip('*')
        
        if code.isdigit():
            # Aperture selection
            self._current_aperture = code
            logging.debug(f"Selected aperture: {code}")
        elif code == '03':
            # Flash (create pad)
            logging.info(f"Creating pad at ({self._current_x}, {self._current_y}) with aperture {self._current_aperture}")
            self._create_pad()
        elif code == '02':
            # Move operation (no pad creation)
            logging.debug("Move operation")
        elif code == '01':
            # Linear interpolation (no pad creation)
            logging.debug("Linear interpolation")

    def _parse_coordinate(self, line: str):
        """Parse coordinate (e.g., X7550Y3850D03*)"""
        # Remove any trailing operations (D01, D02, D03)
        coord_part = re.sub(r'D\d+\*?$', '', line)
        
        x_match = re.search(r'X([-\d]+)', coord_part)
        y_match = re.search(r'Y([-\d]+)', coord_part)
        
        old_x, old_y = self._current_x, self._current_y
        
        if x_match:
            self._current_x = float(x_match.group(1)) * self._scale
        if y_match:
            self._current_y = float(y_match.group(1)) * self._scale
            
        if old_x != self._current_x or old_y != self._current_y:
            logging.debug(f"Updated coordinates: ({self._current_x}, {self._current_y})")
            
        # Check if this coordinate includes a flash operation
        if 'D03' in line:
            logging.info(f"Coordinate includes flash operation")
            self._create_pad()

    def _create_pad(self):
        """Create a pad at the current position using current aperture"""
        if not self._current_aperture:
            logging.warning("No aperture selected, cannot create pad")
            return
        if self._current_aperture not in self._apertures:
            logging.warning(f"Selected aperture {self._current_aperture} not found in definitions")
            return

        aperture = self._apertures[self._current_aperture]
        logging.info(f"Creating pad with aperture {self._current_aperture} ({aperture['type']})")

        if aperture['type'] == 'C':  # Circle
            # Create circular pad
            radius = aperture['size'] / 2
            point = Point(self._current_x, self._current_y)
            area = np.pi * radius * radius
            volume = area * 0.15  # Default thickness

            self._pad_counter += 1
            pad = PadInfo(
                id=self._pad_counter,
                shape_type='circle',
                coordinates=(self._current_x, self._current_y),
                geometry=point.buffer(radius),
                area=area,
                volume=volume
            )
            self.pads.append(pad)
            logging.info(f"Created circular pad {self._pad_counter} at ({self._current_x}, {self._current_y})")

        elif aperture['type'] == 'R':  # Rectangle
            # Create rectangular pad
            size = aperture['size']
            half_size = size / 2
            coords = [
                (self._current_x - half_size, self._current_y - half_size),
                (self._current_x + half_size, self._current_y - half_size),
                (self._current_x + half_size, self._current_y + half_size),
                (self._current_x - half_size, self._current_y + half_size),
            ]
            geometry = Polygon(coords)
            area = size * size
            volume = area * 0.15  # Default thickness

            self._pad_counter += 1
            pad = PadInfo(
                id=self._pad_counter,
                shape_type='rectangle',
                coordinates=(self._current_x, self._current_y),
                geometry=geometry,
                area=area,
                volume=volume
            )
            self.pads.append(pad)
            logging.info(f"Created rectangular pad {self._pad_counter} at ({self._current_x}, {self._current_y})")
        else:
            logging.warning(f"Unsupported aperture type: {aperture['type']}")
