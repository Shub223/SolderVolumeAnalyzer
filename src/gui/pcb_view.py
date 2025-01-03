from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, Polygon
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import numpy as np
from typing import List, Optional
import logging
from src.gerber_parser import PadInfo

class PCBView(QWidget):
    def __init__(self):
        super().__init__()
        self.pads: List[PadInfo] = []
        self.selected_pad: Optional[int] = None
        
        # Setup matplotlib figure
        self.figure = Figure(figsize=(8, 8))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Setup widget layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        # Initialize view
        self._setup_plot()
        
    def _setup_plot(self):
        """Setup the plot with default settings"""
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.figure.tight_layout()
        
    def set_pads(self, pads: List[PadInfo]):
        """Update the view with new pad data"""
        logging.info(f"Setting {len(pads)} pads in PCB view")
        self.pads = pads
        self._draw_pads()
        self.fit_view()
        
    def zoom_in(self):
        """Zoom in on the plot"""
        self.ax.set_xlim(self.ax.get_xlim()[0] * 0.8, self.ax.get_xlim()[1] * 0.8)
        self.ax.set_ylim(self.ax.get_ylim()[0] * 0.8, self.ax.get_ylim()[1] * 0.8)
        self.canvas.draw()
        
    def zoom_out(self):
        """Zoom out on the plot"""
        self.ax.set_xlim(self.ax.get_xlim()[0] * 1.2, self.ax.get_xlim()[1] * 1.2)
        self.ax.set_ylim(self.ax.get_ylim()[0] * 1.2, self.ax.get_ylim()[1] * 1.2)
        self.canvas.draw()
        
    def fit_view(self):
        """Fit the view to show all pads"""
        if not self.pads:
            return
            
        x_coords = []
        y_coords = []
        
        for pad in self.pads:
            bounds = pad.geometry.bounds
            x_coords.extend([bounds[0], bounds[2]])
            y_coords.extend([bounds[1], bounds[3]])
            
        if x_coords and y_coords:
            padding = 0.1 * (max(x_coords) - min(x_coords))
            self.ax.set_xlim(min(x_coords) - padding, max(x_coords) + padding)
            self.ax.set_ylim(min(y_coords) - padding, max(y_coords) + padding)
            self.canvas.draw()
        
    def _draw_pads(self):
        """Draw all pads on the plot"""
        logging.info("Drawing pads...")
        self.ax.clear()
        self._setup_plot()
        
        if not self.pads:
            logging.warning("No pads to draw")
            self.canvas.draw()
            return
        
        # Calculate volume range for color mapping
        volumes = [pad.volume for pad in self.pads]
        min_volume = min(volumes)
        max_volume = max(volumes)
        norm = mcolors.Normalize(vmin=min_volume, vmax=max_volume)
        cmap = mcolors.LinearSegmentedColormap.from_list("", ["lightblue", "darkblue"])
        
        for pad in self.pads:
            try:
                logging.debug(f"Drawing pad {pad.id} of type {pad.shape_type}")
                # Get color based on volume
                color = cmap(norm(pad.volume))
                
                if pad.shape_type == 'circle':
                    # For circles, we need to get the radius from the geometry buffer
                    if hasattr(pad.geometry, 'radius'):
                        radius = pad.geometry.radius
                    else:
                        # If geometry is a buffer, get its radius
                        radius = pad.geometry.boundary.distance(pad.geometry.centroid)
                    
                    circle = Circle(
                        pad.coordinates,
                        radius,
                        fill=True,
                        alpha=0.6,
                        fc=color
                    )
                    self.ax.add_patch(circle)
                    
                elif pad.shape_type in ['rectangle', 'polygon']:
                    bounds = pad.geometry.bounds
                    if pad.shape_type == 'rectangle':
                        patch = Rectangle(
                            (bounds[0], bounds[1]),
                            bounds[2] - bounds[0],
                            bounds[3] - bounds[1],
                            fill=True,
                            alpha=0.6,
                            fc=color
                        )
                    else:
                        coords = np.array(pad.geometry.exterior.coords)
                        patch = Polygon(
                            coords,
                            fill=True,
                            alpha=0.6,
                            fc=color
                        )
                    self.ax.add_patch(patch)
                    
            except Exception as e:
                logging.error(f"Error drawing pad {pad.id}: {str(e)}")
        
        # Add colorbar
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        self.figure.colorbar(sm, ax=self.ax, label='Volume (mm³)')
        
        logging.info("Drawing complete, updating canvas")
        self.canvas.draw()
