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

class Section3Scene(TeachingScene):
    def construct(self):
        self.setup_layout(
            "Sec 3: Visualizing the Tangent Line", 
            [
                'Start with a secant line.', 
                'Move the second point closer.', 
                'Secant becomes the tangent line.', 
                'Tangent is the limit position.', 
                'This defines the local slope.'
            ]
        )
        
        # Define colors for lecture lines
        color1 = "#FF9999"  # Light Red
        color2 = "#99FFFF"  # Light Cyan
        color3 = "#99FF99"  # Light Green
        color4 = "#FFFF99"  # Light Yellow
        color5 = "#FF99FF"  # Light Magenta

        # Setup Coordinate System in the right side area (B2 to E5)
        # We will use a custom coordinate system centered in the grid area
        # Grid area center is roughly around (3, 0.2)
        # Let's define a coordinate system for the math plot
        # The plot area should be clear. Let's use B2-E5 area.
        # Center of B2-E5:
        # B2: (1.5, 1.2), E5: (4.5, -1.8) -> Center (3, -0.3)
        
        # Instead of standard axes which might be cluttered, let's just draw the curve and lines
        # We need to map math coordinates to screen coordinates.
        # Let's define a helper to convert math (x,y) to screen position
        # Math range: x in [0, 2], y in [0, 4]
        # Screen area: Let's use the center of the right grid, roughly 3x3 units
        # Let's place the origin of the math plot at grid C3 (2.5, 0.2)
        # Scale: 1 math unit = 0.8 screen units
        
        math_origin_screen = self.grid['C3']
        scale = 0.8

        def math_to_screen(x, y):
            return math_origin_screen + np.array([x * scale, y * scale, 0])

        # Create the curve y = x^2
        # Points from x=0 to x=1.5
        t_values = np.linspace(0, 1.5, 100)
        curve_points = [math_to_screen(t, t**2) for t in t_values]
        curve = VMobject()
        curve.set_points_as_corners(curve_points)
        curve.set_color(BLUE)
        curve.set_stroke(width=3)

        # Point P1 at (1, 1)
        p1_math = np.array([1, 1])
        p1_screen = math_to_screen(1, 1)
        dot1 = Dot(p1_screen, color=WHITE, radius=0.05)
        label1 = Text("P1", font_size=16, color=WHITE).next_to(dot1, DL, buff=0.1)

        # Point P2 at (1.1, 1.21)
        p2_math_initial = np.array([1.1, 1.21])
        p2_screen_initial = math_to_screen(1.1, 1.21)
        dot2 = Dot(p2_screen_initial, color=WHITE, radius=0.05)
        label2 = Text("P2", font_size=16, color=WHITE).next_to(dot2, UR, buff=0.1)

        # Secant Line connecting P1 and P2
        # Extend the line slightly for visibility
        vec = p2_screen_initial - p1_screen
        line_start = p1_screen - vec * 0.2
        line_end = p2_screen_initial + vec * 0.2
        secant_line = Line(line_start, line_end, color=RED, stroke_width=3)

        # Add curve and points to scene
        self.play(Create(curve), FadeIn(dot1), FadeIn(label1), FadeIn(dot2), FadeIn(label2), run_time=1)
        
        # === Animation for Lecture Line 1 ===
        # "Start with a secant line."
        self.play(Write(secant_line), run_time=1)
        self.lecture[0].set_color(color1)
        self.wait(1)

        # === Animation for Lecture Line 2 ===
        # "Move the second point closer."
        # Animate P2 moving towards P1
        # Let's move it to (1.05, 1.1025)
        p2_math_mid = np.array([1.05, 1.1025])
        p2_screen_mid = math_to_screen(1.05, 1.1025)
        
        # Update line to connect new P2
        vec_mid = p2_screen_mid - p1_screen
        line_start_mid = p1_screen - vec_mid * 0.2
        line_end_mid = p2_screen_mid + vec_mid * 0.2
        secant_line_mid = Line(line_start_mid, line_end_mid, color=RED, stroke_width=3)

        self.play(
            MoveAlongPath(dot2, Line(p2_screen_initial, p2_screen_mid)),
            MoveAlongPath(label2, Line(p2_screen_initial + np.array([0.2, 0.2, 0]), p2_screen_mid + np.array([0.2, 0.2, 0]))),
            Transform(secant_line, secant_line_mid),
            run_time=2
        )
        self.lecture[1].set_color(color2)
        self.wait(1)

        # === Animation for Lecture Line 3 ===
        # "Secant becomes the tangent line."
        # Move P2 very close to P1, e.g., (1.01, 1.0201)
        p2_math_close = np.array([1.01, 1.0201])
        p2_screen_close = math_to_screen(1.01, 1.0201)
        
        vec_close = p2_screen_close - p1_screen
        line_start_close = p1_screen - vec_close * 0.5 # Extend more as it gets flatter
        line_end_close = p2_screen_close + vec_close * 0.5
        secant_line_close = Line(line_start_close, line_end_close, color=RED, stroke_width=3)

        self.play(
            MoveAlongPath(dot2, Line(p2_screen_mid, p2_screen_close)),
            MoveAlongPath(label2, Line(p2_screen_mid + np.array([0.2, 0.2, 0]), p2_screen_close + np.array([0.2, 0.2, 0]))),
            Transform(secant_line, secant_line_close),
            run_time=2
        )
        
        # Change color to green
        self.play(secant_line.animate.set_color(GREEN), run_time=1)
        self.lecture[2].set_color(color3)
        self.wait(1)

        # === Animation for Lecture Line 4 ===
        # "Tangent is the limit position."
        # Fade out P2 and its label
        # Create the final tangent line at x=1 for y=x^2. Slope = 2x = 2.
        # Equation: y - 1 = 2(x - 1) => y = 2x - 1
        # Let's draw a proper tangent line segment
        x1, y1 = 0.5, 2*0.5 - 1 # (0.5, 0)
        x2, y2 = 1.5, 2*1.5 - 1 # (1.5, 2)
        t_start = math_to_screen(x1, y1)
        t_end = math_to_screen(x2, y2)
        tangent_line = Line(t_start, t_end, color=GREEN, stroke_width=3)
        
        # Transform the current secant to the true tangent
        self.play(
            Transform(secant_line, tangent_line),
            FadeOut(dot2),
            FadeOut(label2),
            run_time=2
        )
        
        # Add label "Tangent"
        tangent_label = Text("Tangent", font_size=18, color=GREEN).next_to(tangent_line, UR, buff=0.2)
        self.play(FadeIn(tangent_label), run_time=1)
        self.lecture[3].set_color(color4)
        self.wait(1)

        # === Animation for Lecture Line 5 ===
        # "This defines the local slope."
        # Highlight the point P1 again to emphasize the local slope
        self.play(Indicate(dot1, scale_factor=1.2), run_time=1)
        self.lecture[4].set_color(color5)
        self.wait(2)