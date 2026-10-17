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

class Section4Scene(TeachingScene):
    def construct(self):
        self.setup_layout("Sec 4: Derivative as the Slope of the Tangent", ['Derivative is tangent slope.', 'For y=x², derivative is 2x.', 'At x=1, slope is 2.'])

        # --- Setup Coordinate System ---
        # We will draw a simple coordinate system on the right side
        # Center of the right side grid is roughly around x=3.5, y=0.2
        # Let's define a local coordinate system for the math plot
        # We'll use a small scale to fit in the grid area (A1-F6)
        
        # Define key points in scene coordinates
        # Let's map math (0,0) to grid 'D2' approx
        # Math (1,1) to grid 'C3' approx
        # Math (2,4) is too high, let's adjust scale or range.
        # Let's just draw the relevant part: x from 0 to 2, y from 0 to 4.
        
        # Grid positions:
        # D2: (1.5, 0.2) -> Let's use this as origin (0,0) for math plot? 
        # Actually, let's place the math plot centered in the right area.
        
        # Let's define the math plot elements relative to grid positions for consistency
        # Origin (0,0) at grid 'D2' (1.5, 0.2)
        # Point (1,1) at grid 'C3' (2.5, 1.2) -> dx=1, dy=1. Scale is 1 unit per grid unit.
        # Point (2,4) would be at (3.5, 4.2) which is off screen (max y is 2.2).
        # So we need to scale down the y-axis or just show the tangent part.
        
        # Let's use a simpler visual representation:
        # Draw the curve y=x^2 from x=0 to x=1.5
        # Draw the tangent at x=1.
        
        # Let's place the origin at 'D3' (2.5, 0.2)
        # Then (1,1) is at 'C4' (3.5, 1.2)
        # Tangent slope is 2.
        # Point (0.5, 0.25) on curve.
        # Point (1.5, 2.25) on curve.
        
        # Let's define the math coordinate system in scene space
        # Origin: (2.5, 0.2) [Grid D3]
        # Scale: 1 math unit = 1 scene unit in x, 0.5 scene units in y (to fit better)
        
        origin = np.array([2.5, 0.2, 0])
        scale_x = 1.0
        scale_y = 0.5
        
        def math_to_scene(x, y):
            return origin + np.array([x * scale_x, y * scale_y, 0])
        
        # Create the curve y = x^2
        def f(x):
            return x**2
            
        curve_points = [math_to_scene(x, f(x)) for x in np.linspace(0, 1.5, 50)]
        curve = VMobject()
        curve.set_points_as_corners(curve_points)
        curve.set_color(BLUE)
        curve.set_stroke(width=3)
        
        # Create the tangent line at x=1
        # Slope m = 2, point (1,1)
        # Line equation: y - 1 = 2(x - 1) => y = 2x - 1
        # Let's draw it from x=0.5 to x=1.5
        tangent_start = math_to_scene(0.5, 2*0.5 - 1)
        tangent_end = math_to_scene(1.5, 2*1.5 - 1)
        tangent_line = Line(tangent_start, tangent_end, color=ORANGE, stroke_width=3)
        
        # Point at (1,1)
        point_1_1 = Dot(math_to_scene(1, 1), color=WHITE, radius=0.05)
        
        # Add axes (simple lines)
        x_axis = Line(origin, math_to_scene(2, 0), color=GREY, stroke_width=1)
        y_axis = Line(origin, math_to_scene(0, 4), color=GREY, stroke_width=1)
        
        # Add labels for axes
        x_label = Text("x", font_size=16, color=GREY).next_to(x_axis, RIGHT, buff=0.1)
        y_label = Text("y", font_size=16, color=GREY).next_to(y_axis, UP, buff=0.1)
        
        # Add label for point (1,1)
        point_label = Text("(1, 1)", font_size=14, color=WHITE).next_to(point_1_1, DR, buff=0.2)
        
        # Group all static plot elements
        plot_group = VGroup(x_axis, y_axis, x_label, y_label, curve, tangent_line, point_1_1, point_label)
        
        # Position the plot group in the right side area
        # The plot is already defined in scene coordinates based on grid D3.
        # We just add it.
        
        self.add(plot_group)
        self.wait(1)

        # === Animation for Lecture Line 1 ===
        # "Derivative is tangent slope."
        # Highlight Lecture Line 1
        self.lecture[0].set_color(YELLOW)
        self.wait(0.5)
        
        # Animation Step 1: Display formula 'f'(x) = 2x' in #FFFFFF near the tangent line.
        formula = MathTex(r"f'(x) = 2x", color=WHITE, font_size=24)
        # Place it near the tangent line, maybe above it
        # Tangent midpoint is at x=1, y=1. Scene pos: (3.5, 0.7)
        # Let's place it at grid 'B4' or 'C4' area
        # Grid C4 is (3.5, 1.2). Point (1,1) is at (3.5, 0.7).
        # Let's place formula at (3.5, 1.8) which is grid 'B4'
        formula = self.place_at_grid(formula, 'B4', scale_factor=1.0)
        
        self.play(Write(formula), run_time=1)
        self.wait(1)

        # === Animation for Lecture Line 2 ===
        # "For y=x², derivative is 2x."
        # Highlight Lecture Line 2
        self.lecture[1].set_color(YELLOW)
        self.wait(0.5)
        
        # Animation Step 2: Draw a right triangle under the tangent line at (1,1) with run 1 (#4169E1) and rise 2 (#DC143C).
        # The tangent line passes through (1,1).
        # Let's define the triangle from x=1 to x=2? Or x=0.5 to x=1.5?
        # "Run 1" and "Rise 2".
        # Let's start from (0.5, 0) on the tangent line? No, tangent is y=2x-1.
        # At x=0.5, y=0. At x=1.5, y=2.
        # So the segment from (0.5, 0) to (1.5, 2) has run 1 and rise 2.
        # But the point of tangency is (1,1).
        # Let's draw the triangle with vertices:
        # P1: (0.5, 0) -> Scene: math_to_scene(0.5, 0) = (3.0, 0.2)
        # P2: (1.5, 0) -> Scene: math_to_scene(1.5, 0) = (4.0, 0.2)  (Run)
        # P3: (1.5, 2) -> Scene: math_to_scene(1.5, 2) = (4.0, 1.2)  (Rise)
        
        p1 = math_to_scene(0.5, 0)
        p2 = math_to_scene(1.5, 0)
        p3 = math_to_scene(1.5, 2)
        
        run_line = Line(p1, p2, color="#4169E1", stroke_width=3)
        rise_line = Line(p2, p3, color="#DC143C", stroke_width=3)
        
        # Labels for run and rise
        run_label = Text("1", font_size=16, color="#4169E1").next_to(run_line, DOWN, buff=0.1)
        rise_label = Text("2", font_size=16, color="#DC143C").next_to(rise_line, RIGHT, buff=0.1)
        
        triangle_group = VGroup(run_line, rise_line, run_label, rise_label)
        
        self.play(Create(run_line), Create(rise_line), run_time=1)
        self.play(FadeIn(run_label), FadeIn(rise_label), run_time=0.5)
        self.wait(1)

        # === Animation for Lecture Line 3 ===
        # "At x=1, slope is 2."
        # Highlight Lecture Line 3
        self.lecture[2].set_color(YELLOW)
        self.wait(0.5)
        
        # Animation Step 3: Label the slope '2' in #FFD700 at the midpoint of the tangent line.
        # Midpoint of the tangent segment we drew (0.5,0) to (1.5,2) is (1,1).
        # But we already have a point there.
        # Let's place the slope label clearly.
        slope_label = Text("Slope = 2", font_size=18, color="#FFD700")
        # Place it near the midpoint of the tangent line, maybe to the left
        # Midpoint scene pos: (3.5, 0.7)
        # Let's place it at grid 'C3' (2.5, 1.2) or 'D3' (2.5, 0.2)
        # Let's place it at (2.5, 1.2) which is grid 'C3'
        slope_label = self.place_at_grid(slope_label, 'C3', scale_factor=1.0)
        
        # Add an arrow from the label to the tangent line midpoint
        arrow = Arrow(slope_label.get_right(), math_to_scene(1, 1), buff=0.1, color="#FFD700")
        
        self.play(FadeIn(slope_label), GrowArrow(arrow), run_time=1)
        self.wait(2)
        
        # Final state
        self.wait(1)