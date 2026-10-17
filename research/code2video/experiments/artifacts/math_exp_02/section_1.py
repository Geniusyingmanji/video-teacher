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
        self.setup_layout("Sec 1: The Mystery of the Missing Piece", 
                         ['Look at this triangle.', 
                          'We have three colored angles.', 
                          'What happens if we cut them?', 
                          "Let's put the corners together.", 
                          'They form a straight line.'])
        
        # Define colors
        red = "#FF5733"
        blue = "#33A1FF"
        green = "#33FF57"
        
        # === Animation for Lecture Line 1 ===
        # Fade in a triangle with vertices labeled A, B, C
        triangle = Polygon([-2, -1.5, 0], [2, -1.5, 0], [0, 1.5, 0], 
                          stroke_color=WHITE, stroke_width=3, fill_opacity=0.1)
        self.place_in_area(triangle, 'B2', 'D4', scale_factor=1.0)
        
        # Add vertex labels
        label_a = Text("A", font_size=24, color=WHITE)
        label_b = Text("B", font_size=24, color=WHITE)
        label_c = Text("C", font_size=24, color=WHITE)
        
        # Position labels near vertices
        label_a.next_to(triangle.get_vertices()[0], DOWN, buff=0.2)
        label_b.next_to(triangle.get_vertices()[1], DOWN, buff=0.2)
        label_c.next_to(triangle.get_vertices()[2], UP, buff=0.2)
        
        self.play(FadeIn(triangle), run_time=1)
        self.play(FadeIn(label_a), FadeIn(label_b), FadeIn(label_c), run_time=0.5)
        
        # Color lecture line 1
        self.lecture[0].set_color(YELLOW)
        
        # === Animation for Lecture Line 2 ===
        # Highlight the three angles with colored arcs
        # Create angle indicators at each vertex
        angle_a = Arc(radius=0.3, start_angle=0, angle=PI/3, stroke_color=red, stroke_width=4)
        angle_b = Arc(radius=0.3, start_angle=2*PI/3, angle=PI/3, stroke_color=blue, stroke_width=4)
        angle_c = Arc(radius=0.3, start_angle=4*PI/3, angle=PI/3, stroke_color=green, stroke_width=4)
        
        # Position angles at vertices
        angle_a.move_to(triangle.get_vertices()[0] + np.array([0, 0.2, 0]))
        angle_b.move_to(triangle.get_vertices()[1] + np.array([0, 0.2, 0]))
        angle_c.move_to(triangle.get_vertices()[2] + np.array([0, -0.2, 0]))
        
        self.play(FadeIn(angle_a), FadeIn(angle_b), FadeIn(angle_c), run_time=1)
        
        # Pulsing glow effect
        self.play(
            angle_a.animate.set_stroke(width=6),
            angle_b.animate.set_stroke(width=6),
            angle_c.animate.set_stroke(width=6),
            run_time=0.3
        )
        self.play(
            angle_a.animate.set_stroke(width=4),
            angle_b.animate.set_stroke(width=4),
            angle_c.animate.set_stroke(width=4),
            run_time=0.3
        )
        
        # Color lecture line 2
        self.lecture[1].set_color(YELLOW)
        
        # === Animation for Lecture Line 3 ===
        # Animate 'cuts' separating the three corner sectors
        # Create simplified corner pieces
        corner_a = Polygon(
            triangle.get_vertices()[0],
            triangle.get_vertices()[0] + np.array([0.3, 0.2, 0]),
            triangle.get_vertices()[0] + np.array([-0.2, 0.3, 0]),
            stroke_color=red, stroke_width=2, fill_color=red, fill_opacity=0.3
        )
        corner_b = Polygon(
            triangle.get_vertices()[1],
            triangle.get_vertices()[1] + np.array([-0.3, 0.2, 0]),
            triangle.get_vertices()[1] + np.array([0.2, 0.3, 0]),
            stroke_color=blue, stroke_width=2, fill_color=blue, fill_opacity=0.3
        )
        corner_c = Polygon(
            triangle.get_vertices()[2],
            triangle.get_vertices()[2] + np.array([0.2, -0.3, 0]),
            triangle.get_vertices()[2] + np.array([-0.2, -0.3, 0]),
            stroke_color=green, stroke_width=2, fill_color=green, fill_opacity=0.3
        )
        
        # Fade out original triangle and show corners
        self.play(FadeOut(triangle), FadeOut(label_a), FadeOut(label_b), FadeOut(label_c), 
                  FadeOut(angle_a), FadeOut(angle_b), FadeOut(angle_c), run_time=0.5)
        self.play(FadeIn(corner_a), FadeIn(corner_b), FadeIn(corner_c), run_time=0.5)
        
        # Color lecture line 3
        self.lecture[2].set_color(YELLOW)
        
        # === Animation for Lecture Line 4 ===
        # The three separated angle sectors float and rotate to align adjacent to each other
        # Move corners to form a line
        target_pos_a = np.array([1.0, 0.5, 0])
        target_pos_b = np.array([2.0, 0.5, 0])
        target_pos_c = np.array([3.0, 0.5, 0])
        
        self.play(
            corner_a.animate.move_to(target_pos_a),
            corner_b.animate.move_to(target_pos_b),
            corner_c.animate.move_to(target_pos_c),
            run_time=1.5
        )
        
        # Color lecture line 4
        self.lecture[3].set_color(YELLOW)
        
        # === Animation for Lecture Line 5 ===
        # The three angles snap together to form a straight horizontal line
        # Label '180°' appears below
        line_indicator = Line(
            np.array([0.5, 0.5, 0]),
            np.array([3.5, 0.5, 0]),
            stroke_color=WHITE, stroke_width=2
        )
        angle_label = Text("180°", font_size=28, color=WHITE)
        angle_label.move_to(np.array([2.0, -0.2, 0]))
        
        self.play(FadeIn(line_indicator), FadeIn(angle_label), run_time=0.5)
        
        # Color lecture line 5
        self.lecture[4].set_color(YELLOW)
        
        # Hold the final scene
        self.wait(2)