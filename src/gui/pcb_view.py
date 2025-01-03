from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
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
        
        # Enable mouse interaction
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
        
        # Pan and zoom state
        self._pan_start = None
        self._is_panning = False
        
        # Initialize view
        self._setup_plot()
        
    def _setup_plot(self):
        """Setup the plot with default settings"""
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle='--', alpha=0.5)
        # Remove margins around the plot
        self.figure.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        
    def set_pads(self, pads: List[PadInfo]):
        """Update the view with new pad data"""
        logging.info(f"Setting {len(pads)} pads in PCB view")
        self.pads = pads
        self._draw_pads()
        self.fit_view()
        
    def zoom_in(self):
        """Zoom in on the plot center"""
        self._zoom(0.95)
        
    def zoom_out(self):
        """Zoom out from the plot center"""
        self._zoom(1.05)
        
    def _zoom(self, factor, center=None):
        """Zoom the view by a factor, optionally around a center point"""
        if center is None or None in center:
            # Use current view center if no center point provided
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            center = ((xlim[1] + xlim[0]) / 2, (ylim[1] + ylim[0]) / 2)
            
        # Get the current view limits
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        
        # Calculate new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * factor
        
        # Calculate new limits while maintaining the center point
        x_center, y_center = center
        self.ax.set_xlim([x_center - new_width/2, x_center + new_width/2])
        self.ax.set_ylim([y_center - new_height/2, y_center + new_height/2])
        
        # Maintain aspect ratio
        self.ax.set_aspect('equal')
        self.figure.canvas.draw_idle()
        
    def _on_scroll(self, event):
        """Handle mouse wheel scrolling for zoom"""
        if event.inaxes != self.ax:
            return
            
        # Get the current mouse position in data coordinates
        center = (event.xdata, event.ydata)
        
        # More gradual zoom factors
        factor = 0.95 if event.button == 'up' else 1.05
        
        self._zoom(factor, center)
        
    def _on_mouse_press(self, event):
        """Handle mouse button press"""
        if event.inaxes != self.ax:
            return
            
        if event.button == 1:  # Left click
            self._is_panning = True
            self._pan_start = (event.xdata, event.ydata)
            
    def _on_mouse_move(self, event):
        """Handle mouse movement"""
        if not self._is_panning or event.inaxes != self.ax or self._pan_start is None:
            return
            
        # Calculate the movement
        dx = event.xdata - self._pan_start[0]
        dy = event.ydata - self._pan_start[1]
        
        # Update the view limits
        self.ax.set_xlim(self.ax.get_xlim() - dx)
        self.ax.set_ylim(self.ax.get_ylim() - dy)
        
        self.canvas.draw()
        
        # Update the start position for the next movement
        self._pan_start = (event.xdata, event.ydata)
        
    def _on_mouse_release(self, event):
        """Handle mouse button release"""
        self._is_panning = False
        self._pan_start = None
        
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
        
        # Create colorbar axes
        if hasattr(self, '_colorbar'):
            self._colorbar.remove()
        cax = self.figure.add_axes([0.92, 0.1, 0.02, 0.8])
        
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
                        radius = pad.geometry.buffer(0).boundary.distance(pad.geometry.centroid)
                    
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
        self._colorbar = self.figure.colorbar(sm, cax=cax, label='Volume (mm³)')
        
        # Ensure plot remains centered
        self.ax.set_aspect('equal')
        self.figure.tight_layout()
        
        logging.info("Drawing complete, updating canvas")
        self.canvas.draw()
