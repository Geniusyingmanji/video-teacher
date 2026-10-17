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

class Section2Scene(TeachingScene):
    def construct(self):
        self.setup_layout("Sec 2: The Problem: Changing Steepness on a Curve", 
                          ['Curves change steepness constantly.', 
                           'What is slope at one point?', 
                           'Tangent lines match curve direction.'])
        
        # Define colors for lecture lines
        color_line1 = "#FFA07A"  # Light Salmon
        color_line2 = "#87CEFA"  # Light Sky Blue
        color_line3 = "#98FB98"  # Pale Green

        # === Animation for Lecture Line 1 ===
        # "Curves change steepness constantly."
        # Change color of first lecture line
        self.lecture[0].set_color(color_line1)
        
        # Animation step 1: Draw the parabola y=x² in #FFFFFF, highlighting the vertex at (0,0).
        # We will use a coordinate system centered in the right grid area
        # The grid area is roughly x: 0.5 to 5.5, y: -3.8 to 2.2
        # Let's place the origin of our math coordinate system at grid D3 (center-ish)
        # D3 is at x = 0.5 + 2*1 = 2.5, y = 2.2 - 3*1 = -0.8
        # Actually, let's use a standard axes setup but positioned via place_in_area
        
        axes = Axes(
            x_range=[-2, 2],
            y_range=[0, 4],
            x_length=6,
            y_length=4,
            axis_config={"color": WHITE, "stroke_width": 2}
        )
        # Place axes in the center of the right grid area (B2 to E5)
        self.place_in_area(axes, 'B2', 'E5', scale_factor=1.0)
        
        parabola = axes.plot(lambda x: x**2, x_range=[-1.5, 1.5], color=WHITE, stroke_width=3)
        
        # Highlight vertex at (0,0)
        vertex_dot = Dot(axes.c2p(0, 0), color=WHITE, radius=0.05)
        
        self.play(Create(axes), run_time=1)
        self.play(Create(parabola), run_time=2)
        self.play(FadeIn(vertex_dot), run_time=0.5)
        
        # === Animation for Lecture Line 2 ===
        # "What is slope at one point?"
        # Change color of second lecture line
        self.lecture[1].set_color(color_line2)
        
        # Animation step 2: Place a glowing dot #FFD700 at (1,1) on the curve.
        point_on_curve = axes.c2p(1, 1)
        glowing_dot = Dot(point_on_curve, color="#FFD700", radius=0.08)
        
        # Add a glow effect (simplified with a larger, transparent circle)
        glow_circle = Circle(
            radius=0.15, 
            color="#FFD700", 
            fill_opacity=0.3, 
            stroke_width=0
        ).move_to(point_on_curve)
        
        self.play(FadeIn(glow_circle), FadeIn(glowing_dot), run_time=1)
        
        # === Animation for Lecture Line 3 ===
        # "Tangent lines match curve direction."
        # Change color of third lecture line
        self.lecture[2].set_color(color_line3)
        
        # Animation step 3: Flash the dot and display text 'Slope at x=1?' in #FFFFFF.
        # Flash the dot
        self.play(
            Indicate(glowing_dot, color="#FFD700", scale_factor=1.5),
            run_time=1
        )
        
        # Display text 'Slope at x=1?'
        slope_text = Text("Slope at x=1?", font_size=24, color=WHITE)
        # Place text near the dot, slightly above and to the right
        # Dot is at axes.c2p(1,1). Let's place text at grid C4 or similar
        # Let's place it relative to the axes point
        text_pos = point_on_curve + np.array([0.5, 0.5, 0])
        slope_text.move_to(text_pos)
        
        self.play(FadeIn(slope_text, shift=UP * 0.2), run_time=1)
        
        # Hold for a moment
        self.wait(2)
        
        # Clean up (optional, usually not needed in final scene unless looping)
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.title and m is not self.lecture], run_time=1)