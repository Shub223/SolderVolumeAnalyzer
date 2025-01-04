from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QMatrix4x4, QVector3D
import moderngl
import numpy as np
from typing import List, Optional, Set, Dict, Tuple
import logging
from src.gerber_parser import PadInfo

class GLPCBView(QOpenGLWidget):
    # Signals
    selection_changed = pyqtSignal(set)  # Emits set of selected pad IDs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # OpenGL context and program
        self.ctx = None
        self.prog = None
        self.vao = None
        self.vbo = None
        self.ibo = None
        
        # View state
        self.model_matrix = QMatrix4x4()
        self.view_matrix = QMatrix4x4()
        self.proj_matrix = QMatrix4x4()
        self.mvp = None
        
        # Interaction state
        self.last_pos = QPointF()
        self.zoom_level = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        
        # Selection state
        self.selection_start = None
        self.selection_active = False
        self.selected_pads: Set[int] = set()
        self.selection_mode = False
        self.ctrl_pressed = False
        
        # Data
        self.pads: List[PadInfo] = []
        self.pad_vertices = None
        self.pad_indices = None
        self.vertex_data = None
        
    def initializeGL(self):
        """Initialize OpenGL"""
        try:
            self.ctx = moderngl.create_context(standalone=False)
            
            # Basic setup
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.BLEND)
            
            # Simple shaders
            vertex_shader = '''
                #version 330
                in vec3 in_position;
                uniform mat4 mvp;
                void main() {
                    gl_Position = mvp * vec4(in_position, 1.0);
                }
            '''
            
            fragment_shader = '''
                #version 330
                out vec4 f_color;
                void main() {
                    f_color = vec4(0.0, 1.0, 0.0, 1.0);
                }
            '''
            
            self.prog = self.ctx.program(
                vertex_shader=vertex_shader,
                fragment_shader=fragment_shader
            )
            
            # Create test triangle
            vertices = np.array([
                -0.5, -0.5, 0.0,
                0.5, -0.5, 0.0,
                0.0, 0.5, 0.0
            ], dtype='f4')
            
            self.vbo = self.ctx.buffer(vertices.tobytes())
            self.vao = self.ctx.vertex_array(
                self.prog,
                [(self.vbo, '3f', 'in_position')]
            )
            
            # Initialize view
            self.model_matrix = QMatrix4x4()
            self.view_matrix = QMatrix4x4()
            self.proj_matrix = QMatrix4x4()
            self.proj_matrix.ortho(-1, 1, -1, 1, -10, 10)
            
            self.pan_x = 0.0
            self.pan_y = 0.0
            self.zoom_level = 1.0
            self.last_pos = None
            
            self._update_mvp()
            
        except Exception as e:
            logging.error(f"Error in initializeGL: {str(e)}")
            raise
            
    def _update_mvp(self):
        """Update MVP matrix"""
        try:
            self.view_matrix.setToIdentity()
            self.view_matrix.translate(self.pan_x, self.pan_y, 0)
            self.view_matrix.scale(self.zoom_level)
            
            mvp = self.proj_matrix * self.view_matrix * self.model_matrix
            self.mvp = np.array(mvp.data(), dtype='f4').tobytes()
            self.prog['mvp'].write(self.mvp)
            
        except Exception as e:
            logging.error(f"Error updating MVP: {str(e)}")
            
    def paintGL(self):
        """Render the scene"""
        try:
            if not self.ctx or not self.vao:
                return
                
            self.ctx.clear(0.2, 0.3, 0.3, 1.0)
            self.vao.render()
            
        except Exception as e:
            logging.error(f"Error in paintGL: {str(e)}")
            
    def resizeGL(self, width, height):
        """Handle resize"""
        if not self.ctx:
            return
            
        self.ctx.viewport = (0, 0, width, height)
        aspect = width / height if height != 0 else 1.0
        self.proj_matrix.setToIdentity()
        self.proj_matrix.ortho(-aspect, aspect, -1, 1, -10, 10)
        self._update_mvp()
        
    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        
    def mouseMoveEvent(self, event):
        if not self.last_pos:
            return
            
        delta = event.pos() - self.last_pos
        self.last_pos = event.pos()
        
        self.pan_x += delta.x() * 0.005
        self.pan_y -= delta.y() * 0.005
        
        self._update_mvp()
        self.update()
        
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        self.zoom_level *= zoom_factor
        self.zoom_level = max(0.1, min(10.0, self.zoom_level))
        
        self._update_mvp()
        self.update()

    def set_pads(self, pads: List[PadInfo]):
        """Set the pads to be displayed"""
        try:
            logging.info(f"Creating geometry for {len(pads)} pads")
            
            # Create vertex and index data
            vertices = []
            indices = []
            current_index = 0
            
            # First, create a test triangle
            test_vertices = [
                -0.5, -0.5, 0.0,  # Bottom left
                0.5, -0.5, 0.0,   # Bottom right
                0.0, 0.5, 0.0     # Top center
            ]
            test_indices = [0, 1, 2]
            
            vertices.extend(test_vertices)
            indices.extend(test_indices)
            current_index += 3
            
            logging.info("Added test triangle")
            
            # Then add pad geometry
            for pad in pads:
                try:
                    # Get polygon coordinates
                    if not hasattr(pad.geometry, 'exterior'):
                        logging.error(f"Invalid geometry for pad {pad.id}: no exterior")
                        continue
                        
                    coords = list(pad.geometry.exterior.coords)
                    if len(coords) < 3:
                        logging.error(f"Invalid geometry for pad {pad.id}: not enough vertices")
                        continue
                        
                    # Log first pad geometry for debugging
                    if current_index == 3:  # After test triangle
                        logging.debug(f"First pad geometry: {coords}")
                        
                    # Add vertices (x, y, z)
                    for x, y in coords[:-1]:  # Skip last point (same as first)
                        # Scale down coordinates to fit in view
                        x_scaled = float(x) / 100.0  # Scale factor to make pads visible
                        y_scaled = float(y) / 100.0
                        vertices.extend([x_scaled, y_scaled, 0.0])
                        
                    # Add indices for triangle fan
                    vertex_count = len(coords) - 1
                    for i in range(1, vertex_count - 1):
                        indices.extend([
                            current_index,  # Center
                            current_index + i,  # Current
                            current_index + i + 1  # Next
                        ])
                        
                    current_index += vertex_count
                    
                except Exception as e:
                    logging.error(f"Error creating geometry for pad {pad.id}: {str(e)}")
                    continue
                    
            # Validate geometry data
            if not vertices:
                raise ValueError("No valid vertices generated")
            if not indices:
                raise ValueError("No valid indices generated")
                
            # Log vertex data statistics
            vertex_count = len(vertices) // 3
            triangle_count = len(indices) // 3
            logging.info(f"Generated {vertex_count} vertices and {triangle_count} triangles")
            logging.debug(f"First 9 vertices: {vertices[:9]}")
            logging.debug(f"First 3 triangles: {indices[:9]}")
            
            # Convert to numpy arrays with proper data types
            try:
                vertices = np.array(vertices, dtype='f4')
                indices = np.array(indices, dtype='i4')
                
                if vertices.size == 0:
                    raise ValueError("Empty vertex array")
                if indices.size == 0:
                    raise ValueError("Empty index array")
                    
                if vertices.size % 3 != 0:
                    raise ValueError(f"Invalid vertex count: {vertices.size}")
                if indices.size % 3 != 0:
                    raise ValueError(f"Invalid index count: {indices.size}")
                    
                # Validate index bounds
                max_index = np.max(indices)
                if max_index >= vertex_count:
                    raise ValueError(f"Index out of bounds: {max_index} >= {vertex_count}")
                    
                # Log array information
                logging.debug(f"Vertex array: shape={vertices.shape}, dtype={vertices.dtype}")
                logging.debug(f"Index array: shape={indices.shape}, dtype={indices.dtype}")
                
            except Exception as e:
                logging.error(f"Error creating numpy arrays: {str(e)}")
                raise
                
            # Create vertex buffer
            try:
                if hasattr(self, 'vbo') and self.vbo:
                    self.vbo.release()
                    
                # Create buffer with proper stride and offset
                self.vbo = self.ctx.buffer(vertices.tobytes())
                
                if not self.vbo:
                    raise RuntimeError("Failed to create vertex buffer")
                    
                logging.debug(f"Created VBO: size={self.vbo.size}, stride={3 * 4}")  # 3 floats * 4 bytes
                
            except Exception as e:
                logging.error(f"Error creating vertex buffer: {str(e)}")
                raise
                
            # Create index buffer
            try:
                if hasattr(self, 'ibo') and self.ibo:
                    self.ibo.release()
                    
                self.ibo = self.ctx.buffer(indices.tobytes())
                
                if not self.ibo:
                    raise RuntimeError("Failed to create index buffer")
                    
                logging.debug(f"Created IBO: size={self.ibo.size}")
                
            except Exception as e:
                logging.error(f"Error creating index buffer: {str(e)}")
                raise
                
            # Create vertex array object
            try:
                if hasattr(self, 'vao') and self.vao:
                    self.vao.release()
                    
                self.vao = self.ctx.vertex_array(
                    self.prog,
                    [
                        # Format: (buffer, format, attribute_name)
                        (self.vbo, '3f', 'in_position'),  # 3 floats per vertex
                    ],
                    self.ibo
                )
                
                if not self.vao:
                    raise RuntimeError("Failed to create vertex array object")
                    
                # Validate VAO
                if not hasattr(self.vao, 'render'):
                    raise RuntimeError("Invalid VAO: missing render method")
                    
                logging.debug(f"Created VAO: {self.vao}")
                
            except Exception as e:
                logging.error(f"Error creating vertex array object: {str(e)}")
                raise
                
            logging.info("Successfully created pad geometry")
            self._update_mvp()
            
            # Force a redraw
            self.update()
            
        except Exception as e:
            logging.error(f"Failed to create geometry: {str(e)}")
            logging.error("Stack trace:", exc_info=True)
            raise
        
    def _screen_to_world(self, pos: QPointF) -> QPointF:
        """Convert screen coordinates to world coordinates"""
        # Normalize screen coordinates to [-1, 1]
        x = (2.0 * pos.x() / self.width()) - 1.0
        y = 1.0 - (2.0 * pos.y() / self.height())
        
        # Apply inverse MVP transformation
        mvp_inv = self.mvp.inverted()[0]
        world_pos = mvp_inv.map(QVector3D(x, y, 0.0))
        return QPointF(world_pos.x(), world_pos.y())
        
    def _finish_selection(self, current_pos: QPointF):
        """Complete the selection operation"""
        if not self.selection_start:
            return
            
        # Get selection rectangle in world coordinates
        current = self._screen_to_world(current_pos)
        rect = QRectF(
            self.selection_start,
            current
        ).normalized()
        
        # Find pads in selection
        for pad in self.pads:
            bounds = pad.geometry.bounds
            pad_rect = QRectF(
                bounds[0],
                bounds[1],
                bounds[2] - bounds[0],
                bounds[3] - bounds[1]
            )
            
            if rect.contains(pad_rect):
                self.selected_pads.add(pad.id)
                
        # Update vertex data for selected pads
        self._update_selection_visuals()
        
        # Emit selection changed signal
        self.selection_changed.emit(self.selected_pads)
        
    def _update_selection_visuals(self):
        """Update vertex data to show selected pads"""
        if not self.vertex_data is None:
            # Update selected flag in vertex data
            vertex_data = self.vertex_data.reshape(-1, 8)  # 8 components per vertex
            for i, pad in enumerate(self.pads):
                selected = 1.0 if pad.id in self.selected_pads else 0.0
                vertex_data[i::len(self.pads), 6] = selected
                
            # Update vertex buffer
            self.vbo.write(vertex_data.tobytes())
            self.update()
            
    def _draw_selection_rect(self):
        """Draw the selection rectangle"""
        if not self.selection_start:
            return
            
        # Create and use a simple program for the rectangle
        if not hasattr(self, 'rect_prog'):
            self.rect_prog = self.ctx.program(
                vertex_shader="""
                #version 330
                uniform mat4 mvp;
                in vec2 in_position;
                void main() {
                    gl_Position = mvp * vec4(in_position, 0.0, 1.0);
                }
                """,
                fragment_shader="""
                #version 330
                out vec4 f_color;
                void main() {
                    f_color = vec4(0.0, 0.0, 1.0, 0.3);
                }
                """
            )
            
        current = self._screen_to_world(self.last_pos)
        vertices = np.array([
            self.selection_start.x(), self.selection_start.y(),
            current.x(), self.selection_start.y(),
            current.x(), current.y(),
            self.selection_start.x(), current.y()
        ], dtype='f4')
        
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(self.rect_prog, [(vbo, '2f', 'in_position')])
        
        self.rect_prog['mvp'].write(self.mvp)
        vao.render(moderngl.LINE_LOOP)
        
    def set_selection_mode(self, enabled: bool):
        """Enable or disable selection mode"""
        self.selection_mode = enabled
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        
    def update_pad_thickness_visual(self, pad_id: int, is_modified: bool):
        """Update the visual appearance of a pad to show modified thickness"""
        if self.vertex_data is None or not self.ctx:
            return
            
        # Find the pad index
        pad_index = None
        for i, pad in enumerate(self.pads):
            if pad.id == pad_id:
                pad_index = i
                break
                
        if pad_index is None:
            return
            
        # Update modified flag in vertex data
        vertex_data = self.vertex_data.reshape(-1, 8)  # 8 components per vertex
        vertices_per_pad = len(vertex_data) // len(self.pads)
        start_idx = pad_index * vertices_per_pad
        end_idx = start_idx + vertices_per_pad
        
        vertex_data[start_idx:end_idx, 7] = float(is_modified)  # Set modified flag
        
        # Update vertex buffer
        if self.vbo:
            self.vbo.write(vertex_data.tobytes())
            self.update()

    def _create_test_geometry(self):
        """Create a test triangle to verify rendering"""
        try:
            # Create test triangle vertices
            vertices = np.array([
                # x, y, z
                -0.5, -0.5, 0.0,  # Bottom left
                0.5, -0.5, 0.0,   # Bottom right
                0.0, 0.5, 0.0     # Top center
            ], dtype='f4')
            
            indices = np.array([0, 1, 2], dtype='i4')
            
            # Create vertex buffer
            if hasattr(self, 'vbo') and self.vbo:
                self.vbo.release()
            self.vbo = self.ctx.buffer(vertices.tobytes())
            
            # Create index buffer
            if hasattr(self, 'ibo') and self.ibo:
                self.ibo.release()
            self.ibo = self.ctx.buffer(indices.tobytes())
            
            # Create vertex array object
            if hasattr(self, 'vao') and self.vao:
                self.vao.release()
                
            self.vao = self.ctx.vertex_array(
                self.prog,
                [
                    (self.vbo, '3f', 'in_position'),  # 3 floats per vertex
                ],
                self.ibo
            )
            
            logging.info("Created test triangle geometry")
            logging.debug(f"Test vertices: {vertices}")
            logging.debug(f"Test indices: {indices}")
            
        except Exception as e:
            logging.error(f"Error creating test geometry: {str(e)}")
            raise
