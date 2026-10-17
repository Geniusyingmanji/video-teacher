from manim import *
import numpy as np

class TeachingScene(Scene):
    def setup_layout(self, title_text, lecture_lines):
        # BASE
        self.camera.background_color = "#000000"
        self.title = Text(title_text, font_size=28, color=WHITE).to_edge(UP)
        self.add(self.title)

        # Left-side lecture content (bullets with "-")
        lecture_texts = [Text(line, font_size=22, color=WHITE) for line in lecture_lines]
        self.lecture = VGroup(*lecture_texts).arrange(DOWN, aligned_edge=LEFT).scale(0.8)
        self.lecture.to_edge(LEFT, buff=0.2)
        self.add(self.lecture)

        # Define fine-grained animation grid (4x4 grid on right side)
        self.grid = {}
        rows = ["A", "B", "C", "D", "E", "F"]  # Top to bottom
        cols = ["1", "2", "3", "4", "5", "6"]  # Left to right

        for i, row in enumerate(rows):
            for j, col in enumerate(cols):
                x = 0.5 + j * 1
                y = 2.2 - i * 1
                self.grid[f"{row}{col}"] = np.array([x, y, 0])

    def place_at_grid(self, mobject, grid_pos, scale_factor=1.0):
        mobject.scale(scale_factor)
        mobject.move_to(self.grid[grid_pos])
        return mobject

    def place_in_area(self, mobject, top_left, bottom_right, scale_factor=1.0):
        tl_pos = self.grid[top_left]
        br_pos = self.grid[bottom_right]
        
        # Calculate center of the area
        center_x = (tl_pos[0] + br_pos[0]) / 2
        center_y = (tl_pos[1] + br_pos[1]) / 2
        center = np.array([center_x, center_y, 0])
        
        mobject.scale(scale_factor)
        mobject.move_to(center)
        return mobject

class Section5Scene(TeachingScene):
    def construct(self):
        self.setup_layout("Sec 5: Dynamic Application: The Moving Point", ['Point moves along the curve.', 'Tangent rotates continuously.', 'Slope updates in real-time.'])
        
        # Setup coordinate system for the right side of the screen
        # We will place the coordinate system in the area B2 to E5
        # This gives us a good central area for the graph
        
        # Create axes
        axes = Axes(
            x_range=[-2.5, 2.5, 1],
            y_range=[-0.5, 5, 1],
            x_length=8,
            y_length=6,
            axis_config={"color": GRAY}
        )
        
        # Place the axes in the grid area
        self.place_in_area(axes, "B2", "E5", scale_factor=1.0)
        
        # Create the parabola y = x^2
        parabola = axes.plot(lambda x: x**2, color=YELLOW, stroke_width=3)
        
        # Add axes and parabola
        self.play(Create(axes), Create(parabola))
        
        # === Animation for Lecture Line 1 ===
        # Point moves along the curve.
        # Highlight lecture line 1
        self.lecture[0].set_color(BLUE)
        
        # Create a moving dot
        dot = Dot(radius=0.1, color="#FFD700")
        
        # Define the path for the dot along the parabola
        # We need to create a path that follows y = x^2 from x=-2 to x=2
        # We'll use a parametric function
        
        def parabola_path(t):
            # t goes from 0 to 1, mapping to x from -2 to 2
            x_val = -2 + 4 * t
            y_val = x_val ** 2
            return axes.c2p(x_val, y_val)
        
        # Create a VMobject for the path
        path = VMobject()
        path.set_points_as_corners([parabola_path(t/50) for t in range(51)])
        
        # Position the dot at the start
        dot.move_to(parabola_path(0))
        self.add(dot)
        
        # Animate the dot moving along the path
        # We'll use MoveAlongPath
        self.play(MoveAlongPath(dot, path), run_time=3)
        
        # === Animation for Lecture Line 2 ===
        # Tangent rotates continuously.
        # Highlight lecture line 2
        self.lecture[1].set_color(GREEN)
        
        # Create a tangent line
        tangent_line = Line(ORIGIN, RIGHT, color="#00FF00", stroke_width=3)
        
        # We need to animate the tangent line sticking to the dot and rotating
        # The slope of y=x^2 at x is 2x
        # We'll create a function that updates the tangent line position and angle
        
        def update_tangent(mobject, t):
            # t is the parameter from 0 to 1
            x_val = -2 + 4 * t
            y_val = x_val ** 2
            slope = 2 * x_val
            
            # Position the line at the point on the curve
            point = axes.c2p(x_val, y_val)
            
            # Calculate the angle of the tangent
            angle = np.arctan(slope)
            
            # Set the line's position and rotation
            mobject.set_angle(angle)
            mobject.move_to(point)
            
        # Initialize the tangent line
        update_tangent(tangent_line, 0)
        self.add(tangent_line)
        
        # Animate the dot and tangent line together
        # We need to reset the dot to the start and animate both
        dot.move_to(parabola_path(0))
        update_tangent(tangent_line, 0)
        
        # Create a combined animation
        self.play(
            MoveAlongPath(dot, path),
            UpdateFromAlphaFunc(tangent_line, lambda m, t: update_tangent(m, t)),
            run_time=3
        )
        
        # === Animation for Lecture Line 3 ===
        # Slope updates in real-time.
        # Highlight lecture line 3
        self.lecture[2].set_color(WHITE)
        
        # Create a text display for the slope
        slope_text = Text("Slope: -4.0", font_size=24, color=WHITE)
        
        # Place the slope text near the top of the graph area
        self.place_at_grid(slope_text, "A3", scale_factor=0.8)
        self.add(slope_text)
        
        # We need to animate the slope text updating as the dot moves
        # We'll reset the dot and tangent line and animate again with the text update
        
        def update_slope_text(mobject, t):
            x_val = -2 + 4 * t
            slope = 2 * x_val
            mobject.set_text(f"Slope: {slope:.1f}")
        
        # Reset positions
        dot.move_to(parabola_path(0))
        update_tangent(tangent_line, 0)
        slope_text.set_text("Slope: -4.0")
        
        # Animate all three together
        self.play(
            MoveAlongPath(dot, path),
            UpdateFromAlphaFunc(tangent_line, lambda m, t: update_tangent(m, t)),
            UpdateFromAlphaFunc(slope_text, update_slope_text),
            run_time=3
        )
        
        # Hold for a moment
        self.wait(1)
        
        # Clean up
        self.remove(dot, tangent_line, slope_text)
        self.wait(0.5)