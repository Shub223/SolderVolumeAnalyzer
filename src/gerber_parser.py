from dataclasses import dataclass
from typing import List, Tuple, Union, Optional
from shapely.geometry import Polygon, Point, box
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
    length: float = 0.0      # longest dimension
    width: float = 0.0       # shortest dimension
    
    def calculate_dimensions(self):
        """Calculate pad dimensions based on geometry"""
        if self.shape_type == 'circle':
            # For circles, length and width are the diameter
            self.length = self.width = 2 * self.geometry.buffer(0).boundary.distance(self.geometry.centroid)
        else:
            # For rectangles and polygons, calculate using bounds
            minx, miny, maxx, maxy = self.geometry.bounds
            self.length = max(maxx - minx, maxy - miny)
            self.width = min(maxx - minx, maxy - miny)

class GerberParser:
    def __init__(self):
        self.pads: List[PadInfo] = []
        self.apertures = {}
        self._scale = 1.0  # For unit conversion

    def parse_file(self, file_path: str) -> List[PadInfo]:
        """Parse a Gerber file and return a list of pad information"""
        logging.info(f"Starting to parse Gerber file: {file_path}")
        
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                
            pads = []
            self.apertures = {}
            current_aperture = None
            pad_count = 0
            
            for line_num, line in enumerate(lines, 1):
                try:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Process aperture definitions
                    if line.startswith('%ADD'):
                        aperture = self._parse_aperture_definition(line)
                        if aperture:
                            self.apertures[aperture['id']] = aperture
                            logging.info(f"Added aperture {aperture['id']}: type={aperture['type']}, size={aperture['size']}")
                            
                    # Process aperture selection
                    elif line.startswith('D') and line.endswith('*'):
                        d_code = int(line[1:-1])
                        if d_code in self.apertures:
                            current_aperture = self.apertures[d_code]
                            logging.debug(f"Selected aperture D{d_code}")
                            
                    # Process draw commands
                    elif line.startswith('X') or line.startswith('Y'):
                        if current_aperture:
                            try:
                                pad = self._create_pad_from_command(line, current_aperture)
                                if pad:
                                    pads.append(pad)
                                    pad_count += 1
                                    if pad_count % 500 == 0:  # Log progress every 500 pads
                                        logging.info(f"Created {pad_count} pads...")
                            except Exception as e:
                                logging.error(f"Error creating pad from line {line_num}: {line}")
                                logging.error(f"Error details: {str(e)}")
                                
                except Exception as e:
                    logging.error(f"Error processing line {line_num}: {line}")
                    logging.error(f"Error details: {str(e)}")
                    
            if not pads:
                logging.warning("No pads were found in the Gerber file")
                if not self.apertures:
                    logging.error("No aperture definitions found in file")
                else:
                    logging.info(f"Found {len(self.apertures)} aperture definitions but no pad operations")
                    
            logging.info(f"Successfully parsed {len(pads)} pads from Gerber file")
            return pads
            
        except FileNotFoundError:
            logging.error(f"Gerber file not found: {file_path}")
            raise
        except PermissionError:
            logging.error(f"Permission denied accessing file: {file_path}")
            raise
        except Exception as e:
            logging.error(f"Failed to parse Gerber file: {str(e)}")
            logging.error("Stack trace:", exc_info=True)
            raise
            
    def _parse_aperture_definition(self, line: str) -> dict:
        """Parse an aperture definition line"""
        try:
            # Format: %ADDnnT,P1[X P2]*%
            # Example: %ADD10C,0.25400*%
            match = re.match(r'%ADD(\d+)([CR]),([0-9.]+)(?:X([0-9.]+))?', line)
            if not match:
                logging.warning(f"Invalid aperture definition: {line}")
                return None
                
            aperture_id = int(match.group(1))
            aperture_type = match.group(2)
            size = float(match.group(3))
            
            aperture = {
                'id': aperture_id,
                'type': aperture_type,
                'size': size
            }
            
            if match.group(4):  # Second dimension for rectangles
                aperture['size_y'] = float(match.group(4))
                
            return aperture
            
        except Exception as e:
            logging.error(f"Error parsing aperture definition: {line}")
            logging.error(f"Error details: {str(e)}")
            return None
            
    def _create_pad_from_command(self, line: str, aperture: dict) -> Optional[PadInfo]:
        """Create a pad from a draw command"""
        try:
            # Parse coordinates
            x_match = re.search(r'X([+-]?\d+)', line)
            y_match = re.search(r'Y([+-]?\d+)', line)
            
            if not (x_match or y_match):
                return None
                
            x = float(x_match.group(1)) / 1000000 if x_match else 0  # Convert to mm
            y = float(y_match.group(1)) / 1000000 if y_match else 0  # Convert to mm
            
            try:
                # Create pad geometry based on aperture type
                if aperture['type'] == 'C':  # Circle
                    radius = float(aperture['size']) / 2
                    if radius <= 0:
                        logging.warning(f"Invalid circle radius: {radius}")
                        return None
                        
                    geometry = Point(x, y).buffer(radius)
                    if not geometry.is_valid:
                        logging.warning(f"Invalid circle geometry at ({x}, {y}) with radius {radius}")
                        return None
                        
                    shape_type = 'circle'
                    
                else:  # Rectangle
                    width = float(aperture['size'])
                    height = float(aperture.get('size_y', width))
                    
                    if width <= 0 or height <= 0:
                        logging.warning(f"Invalid rectangle dimensions: {width}x{height}")
                        return None
                        
                    geometry = box(x - width/2, y - height/2, x + width/2, y + height/2)
                    if not geometry.is_valid:
                        logging.warning(f"Invalid rectangle geometry at ({x}, {y}) with size {width}x{height}")
                        return None
                        
                    shape_type = 'rectangle'
                    
                # Verify geometry
                if geometry.area <= 0:
                    logging.warning(f"Zero or negative area geometry created")
                    return None
                    
                pad = PadInfo(
                    id=len(self.pads) + 1,
                    shape_type=shape_type,
                    coordinates=(x, y),
                    geometry=geometry,
                    area=geometry.area,
                    volume=geometry.area * 0.15  # Default thickness
                )
                
                return pad
                
            except Exception as e:
                logging.error(f"Error creating geometry: {str(e)}")
                return None
                
        except Exception as e:
            logging.error(f"Error creating pad from command: {line}")
            logging.error(f"Error details: {str(e)}")
            return None
