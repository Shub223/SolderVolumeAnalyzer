from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, Polygon, PathPatch
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import matplotlib.path as mpath
import numpy as np
from typing import List, Optional, Set, Dict, Tuple
import logging
from src.gerber_parser import PadInfo

class PCBView(QWidget):
    # Signals
    selection_changed = pyqtSignal(set)  # Emits set of selected pad IDs
    
    def __init__(self):
        super().__init__()
        self.pads: List[PadInfo] = []
        self.pad_patches: Dict[int, PathPatch] = {}  # Map pad ID to its patch
        self.selected_pads: Set[int] = set()
        self.selection_start: Optional[QPointF] = None
        self.selection_rect: Optional[Rectangle] = None
        self.is_selecting = False
        self.ctrl_pressed = False
        
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
        self.canvas.mpl_connect('key_press_event', self._on_key_press)
        self.canvas.mpl_connect('key_release_event', self._on_key_release)
        
        # Selection mode
        self.selection_mode = False
        
        # Initialize view
        self._setup_plot()
        
    def set_selection_mode(self, enabled: bool):
        """Enable or disable selection mode"""
        self.selection_mode = enabled
        self.canvas.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        
    def _create_striped_pattern(self, base_color):
        """Create a striped pattern for modified pads"""
        pattern = mpath.Path(
            vertices=[(0., 0.), (1., 0.), (1., 1.), (0., 1.), (0., 0.)],
            codes=[mpath.Path.MOVETO, mpath.Path.LINETO, 
                   mpath.Path.LINETO, mpath.Path.LINETO, 
                   mpath.Path.CLOSEPOLY]
        )
        
        # Add diagonal stripes
        for i in range(-5, 15, 2):
            pattern.vertices = np.vstack((pattern.vertices,
                [(i/10-0.2, 0.), (i/10+0.8, 1.)]))
            pattern.codes = np.hstack((pattern.codes,
                [mpath.Path.MOVETO, mpath.Path.LINETO]))
            
        return PathPatch(pattern, facecolor=base_color, alpha=0.6,
                        hatch='///', edgecolor='gray')
        
    def _draw_pads(self):
        """Draw all pads on the plot"""
        logging.info("Drawing pads...")
        self.ax.clear()
        self._setup_plot()
        self.pad_patches.clear()
        
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
                    if hasattr(pad.geometry, 'radius'):
                        radius = pad.geometry.radius
                    else:
                        radius = pad.geometry.buffer(0).boundary.distance(pad.geometry.centroid)
                    
                    patch = Circle(
                        pad.coordinates,
                        radius,
                        fill=True,
                        alpha=0.6,
                        fc=color
                    )
                    
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
                
                # Store the patch
                self.pad_patches[pad.id] = patch
                self.ax.add_patch(patch)
                
                # Add selection highlight if needed
                if pad.id in self.selected_pads:
                    patch.set_edgecolor('red')
                    patch.set_linewidth(2)
                
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
        
    def _on_mouse_press(self, event):
        """Handle mouse button press"""
        if event.inaxes != self.ax:
            return
            
        if event.button == 1:  # Left click
            if self.selection_mode:
                self.selection_start = QPointF(event.xdata, event.ydata)
                self.is_selecting = True
                
                # Clear selection if Ctrl is not pressed
                if not self.ctrl_pressed:
                    self.selected_pads.clear()
                    self._update_selection_visuals()
                    
                # Create selection rectangle
                if self.selection_rect:
                    self.selection_rect.remove()
                self.selection_rect = Rectangle(
                    (event.xdata, event.ydata),
                    0, 0,
                    fill=False,
                    color='red',
                    linestyle='--'
                )
                self.ax.add_patch(self.selection_rect)
            else:
                self._pan_start = (event.xdata, event.ydata)
                self._is_panning = True
                
    def _on_mouse_move(self, event):
        """Handle mouse movement"""
        if event.inaxes != self.ax:
            return
            
        if self.is_selecting and self.selection_start and event.button == 1:
            # Update selection rectangle
            x = min(self.selection_start.x(), event.xdata)
            y = min(self.selection_start.y(), event.ydata)
            w = abs(event.xdata - self.selection_start.x())
            h = abs(event.ydata - self.selection_start.y())
            
            self.selection_rect.set_bounds(x, y, w, h)
            self.canvas.draw()
            
        elif self._is_panning and self._pan_start:
            # Handle panning
            dx = event.xdata - self._pan_start[0]
            dy = event.ydata - self._pan_start[1]
            
            self.ax.set_xlim(self.ax.get_xlim() - dx)
            self.ax.set_ylim(self.ax.get_ylim() - dy)
            
            self.canvas.draw()
            self._pan_start = (event.xdata, event.ydata)
            
    def _on_mouse_release(self, event):
        """Handle mouse button release"""
        if event.button == 1 and self.is_selecting:
            self.is_selecting = False
            
            if self.selection_rect and self.selection_start:
                # Get selection bounds
                x1, y1 = self.selection_start.x(), self.selection_start.y()
                x2, y2 = event.xdata, event.ydata
                selection_bounds = QRectF(
                    min(x1, x2),
                    min(y1, y2),
                    abs(x2 - x1),
                    abs(y2 - y1)
                )
                
                # Find pads in selection
                for pad in self.pads:
                    bounds = pad.geometry.bounds
                    pad_rect = QRectF(
                        bounds[0],
                        bounds[1],
                        bounds[2] - bounds[0],
                        bounds[3] - bounds[1]
                    )
                    
                    if selection_bounds.contains(pad_rect):
                        self.selected_pads.add(pad.id)
                
                # Remove selection rectangle
                self.selection_rect.remove()
                self.selection_rect = None
                
                # Update visuals
                self._update_selection_visuals()
                
                # Emit selection changed signal
                self.selection_changed.emit(self.selected_pads)
                
        elif event.button == 1 and self._is_panning:
            self._is_panning = False
            self._pan_start = None
            
    def _on_key_press(self, event):
        """Handle key press"""
        if event.key == 'control':
            self.ctrl_pressed = True
        elif event.key == 'escape':
            self.selected_pads.clear()
            self._update_selection_visuals()
            self.selection_changed.emit(self.selected_pads)
            
    def _on_key_release(self, event):
        """Handle key release"""
        if event.key == 'control':
            self.ctrl_pressed = False
            
    def _update_selection_visuals(self):
        """Update the visual appearance of selected pads"""
        for pad_id, patch in self.pad_patches.items():
            if pad_id in self.selected_pads:
                patch.set_edgecolor('red')
                patch.set_linewidth(2)
            else:
                patch.set_edgecolor('none')
                patch.set_linewidth(1)
        self.canvas.draw()
        
    def update_pad_thickness_visual(self, pad_id: int, is_modified: bool):
        """Update the visual appearance of a pad to show modified thickness"""
        if pad_id in self.pad_patches:
            patch = self.pad_patches[pad_id]
            if is_modified:
                # Create striped pattern
                new_patch = self._create_striped_pattern(patch.get_facecolor())
                new_patch.set_transform(patch.get_transform())
                patch.remove()
                self.ax.add_patch(new_patch)
                self.pad_patches[pad_id] = new_patch
            self.canvas.draw()
            
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
