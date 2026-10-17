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

class Section1Scene(TeachingScene):
    def construct(self):
        self.setup_layout(
            "Sec 1: Prerequisite: The Concept of Slope",
            [
                "Slope is rise over run.",
                "Straight lines have constant slope.",
                "Slope measures steepness."
            ]
        )

        # Define colors for lecture lines
        color_line1 = "#FFD700"  # Gold
        color_line2 = "#4169E1"  # Royal Blue
        color_line3 = "#DC143C"  # Crimson

        # === Animation for Lecture Line 1 ===
        # "Slope is rise over run."
        # Animation step 1: Fade in a straight line from #000000 to #FFFFFF with two points marked in #FFD700.
        
        # Highlight Lecture Line 1
        self.lecture[0].set_color(color_line1)
        self.play(
            Write(self.lecture[0]),
            run_time=1
        )

        # Create the line and points
        # Place line in area B2-D4
        line_start = self.grid["B2"] + np.array([-0.5, -0.5, 0])
        line_end = self.grid["D4"] + np.array([0.5, 0.5, 0])
        
        # Adjust to fit nicely in the grid area
        line = Line(line_start, line_end, color=WHITE, stroke_width=3)
        
        # Points on the line
        point1 = Dot(line_start, color=color_line1, radius=0.1)
        point2 = Dot(line_end, color=color_line1, radius=0.1)
        
        # Group line and points
        line_group = VGroup(line, point1, point2)
        
        # Position the group in the grid
        self.place_in_area(line_group, "B2", "D4", scale_factor=1.0)
        
        # Animate
        self.play(
            FadeIn(line, color=WHITE),
            FadeIn(point1),
            FadeIn(point2),
            run_time=1.5
        )

        # Animation step 2: Draw a right triangle under the line with base #4169E1 and height #DC143C, labeling 'run' and 'rise'.
        
        # Calculate triangle vertices based on line endpoints
        # Let's use the current positions of point1 and point2
        p1_pos = point1.get_center()
        p2_pos = point2.get_center()
        
        # The third vertex of the right triangle (corner)
        # If line goes from bottom-left to top-right, the corner is at (x2, y1) or (x1, y2)
        # Assuming standard slope visualization:
        # p1 is lower-left, p2 is upper-right
        # Corner is at (p2.x, p1.y)
        corner_pos = np.array([p2_pos[0], p1_pos[1], 0])
        
        # Create the triangle sides
        base_line = Line(p1_pos, corner_pos, color=color_line2, stroke_width=3)  # Horizontal (run)
        height_line = Line(corner_pos, p2_pos, color=color_line3, stroke_width=3)  # Vertical (rise)
        
        # Labels for run and rise
        run_label = Text("run", font_size=20, color=color_line2)
        rise_label = Text("rise", font_size=20, color=color_line3)
        
        # Position labels near the lines
        run_label.move_to(base_line.get_center() + DOWN * 0.3)
        rise_label.move_to(height_line.get_center() + RIGHT * 0.3)
        
        # Animate drawing the triangle
        self.play(
            Create(base_line),
            Create(height_line),
            Write(run_label),
            Write(rise_label),
            run_time=1.5
        )

        # === Animation for Lecture Line 2 ===
        # "Straight lines have constant slope."
        # Highlight Lecture Line 2
        self.lecture[1].set_color(color_line2)
        self.play(
            Write(self.lecture[1]),
            run_time=1
        )

        # Animation step 3: Display text 'Slope = Δy/Δx' in #FFFFFF near the triangle, then fade out the triangle.
        
        # Create the formula
        formula = Text("Slope = Δy/Δx", font_size=28, color=WHITE)
        
        # Place formula near the triangle (e.g., above it)
        self.place_at_grid(formula, "C3", scale_factor=0.8)
        
        # Animate formula appearance
        self.play(
            FadeIn(formula),
            run_time=1
        )

        # Fade out the triangle and labels
        self.play(
            FadeOut(base_line),
            FadeOut(height_line),
            FadeOut(run_label),
            FadeOut(rise_label),
            run_time=1
        )

        # === Animation for Lecture Line 3 ===
        # "Slope measures steepness."
        # Highlight Lecture Line 3
        self.lecture[2].set_color(color_line3)
        self.play(
            Write(self.lecture[2]),
            run_time=1
        )

        # Optional: Add a visual cue for steepness (e.g., a steeper line)
        # But the description only asks for the previous steps.
        # We can just leave the formula and line visible.
        
        # Hold for a moment
        self.wait(2)