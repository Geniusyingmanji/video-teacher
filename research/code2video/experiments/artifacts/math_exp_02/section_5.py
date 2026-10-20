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
        self.setup_layout("Sec 5: Real-World Application: The Bridge Builder", ['Engineers use this for bridges.', 'One angle is 60 degrees.', 'Another angle is 70 degrees.', 'Find the missing third angle.', '180 minus 60 minus 70 is 50.'])
        
        # Define colors for lecture lines
        color_line1 = "#FFFFFF"  # White for general info
        color_line2 = "#FF5733"  # Red for 60 degrees
        color_line3 = "#33A1FF"  # Blue for 70 degrees
        color_line4 = "#FFFF00"  # Yellow for finding missing angle
        color_line5 = "#33FF57"  # Green for result

        # Create the triangular truss structure
        # Triangle vertices
        A = np.array([1.5, 0.5, 0])  # Bottom left
        B = np.array([4.5, 0.5, 0])  # Bottom right
        C = np.array([3.0, 3.0, 0])  # Top
        
        # Create triangle
        triangle = Polygon(A, B, C, color=WHITE, fill_opacity=0.1, stroke_width=3)
        
        # Create additional truss elements for bridge appearance
        mid_ab = (A + B) / 2
        truss_lines = VGroup(
            Line(A, C, color=WHITE, stroke_width=2),
            Line(B, C, color=WHITE, stroke_width=2),
            Line(A, B, color=WHITE, stroke_width=2),
            Line(mid_ab, C, color=WHITE, stroke_width=1.5),
            Line(A, mid_ab, color=WHITE, stroke_width=1.5),
            Line(mid_ab, B, color=WHITE, stroke_width=1.5)
        )
        
        bridge_structure = VGroup(triangle, truss_lines)
        
        # Position the bridge structure in the center-right area
        self.place_in_area(bridge_structure, 'B2', 'D5', scale_factor=1.0)
        
        # === Animation for Lecture Line 1 ===
        # "Engineers use this for bridges."
        # Fade in the triangular truss structure
        self.play(FadeIn(bridge_structure), run_time=1.5)
        
        # Highlight the central triangle
        central_triangle_highlight = Polygon(A, B, C, color="#FFFF00", fill_opacity=0.2, stroke_width=4)
        self.place_in_area(central_triangle_highlight, 'B2', 'D5', scale_factor=1.0)
        self.play(FadeIn(central_triangle_highlight), run_time=0.8)
        self.wait(0.5)
        self.play(FadeOut(central_triangle_highlight), run_time=0.5)
        
        # Change lecture line 1 color
        self.lecture[0].set_color(color_line1)
        
        # === Animation for Lecture Line 2 ===
        # "One angle is 60 degrees."
        # Label the bottom-left angle '60°' in Red
        angle_60_label = Text("60°", font_size=24, color=color_line2)
        # Position near bottom-left vertex A
        angle_60_label.move_to(A + np.array([0.3, -0.3, 0]))
        
        # Create angle arc for 60 degrees
        angle_60_arc = Arc(radius=0.4, start_angle=0, angle=PI/3, color=color_line2, stroke_width=3)
        angle_60_arc.move_to(A)
        
        self.play(Write(angle_60_arc), FadeIn(angle_60_label), run_time=1.0)
        
        # Change lecture line 2 color
        self.lecture[1].set_color(color_line2)
        
        # === Animation for Lecture Line 3 ===
        # "Another angle is 70 degrees."
        # Label the bottom-right angle '70°' in Blue
        angle_70_label = Text("70°", font_size=24, color=color_line3)
        # Position near bottom-right vertex B
        angle_70_label.move_to(B + np.array([-0.3, -0.3, 0]))
        
        # Create angle arc for 70 degrees
        angle_70_arc = Arc(radius=0.4, start_angle=PI, angle=-70*DEGREES, color=color_line3, stroke_width=3)
        angle_70_arc.move_to(B)
        
        self.play(Write(angle_70_arc), FadeIn(angle_70_label), run_time=1.0)
        
        # Change lecture line 3 color
        self.lecture[2].set_color(color_line3)
        
        # === Animation for Lecture Line 4 ===
        # "Find the missing third angle."
        # The top angle pulses
        top_angle_label_placeholder = Text("?", font_size=28, color=color_line4)
        top_angle_label_placeholder.move_to(C + np.array([0, -0.4, 0]))
        
        # Create angle arc for top angle
        top_angle_arc = Arc(radius=0.4, start_angle=PI - 40*DEGREES, angle=80*DEGREES, color=color_line4, stroke_width=3)
        top_angle_arc.move_to(C)
        
        self.play(Write(top_angle_arc), FadeIn(top_angle_label_placeholder), run_time=1.0)
        
        # Pulse animation
        self.play(
            top_angle_arc.animate.scale(1.1).set_color("#FFFF99"),
            top_angle_label_placeholder.animate.scale(1.1),
            run_time=0.4
        )
        self.play(
            top_angle_arc.animate.scale(1.0).set_color(color_line4),
            top_angle_label_placeholder.animate.scale(1.0),
            run_time=0.4
        )
        
        # A calculation box appears: '180 - 60 - 70 = 50°'
        calc_box = Rectangle(width=3.5, height=0.8, color=WHITE, stroke_width=2, fill_opacity=0.1)
        calc_text = Text("180 - 60 - 70 = 50°", font_size=20, color=WHITE)
        calc_group = VGroup(calc_box, calc_text).arrange(DOWN, buff=0.1)
        
        # Position calculation box in upper right area
        self.place_in_area(calc_group, 'A4', 'B6', scale_factor=0.9)
        
        self.play(FadeIn(calc_group), run_time=1.0)
        
        # Change lecture line 4 color
        self.lecture[3].set_color(color_line4)
        
        # === Animation for Lecture Line 5 ===
        # "180 minus 60 minus 70 is 50."
        # The top angle fills with Green and is labeled '50°'
        angle_50_label = Text("50°", font_size=24, color=color_line5)
        angle_50_label.move_to(C + np.array([0, -0.4, 0]))
        
        # Replace the placeholder with the actual label
        self.play(
            FadeOut(top_angle_label_placeholder),
            FadeIn(angle_50_label),
            top_angle_arc.animate.set_color(color_line5).set_fill(color_line5, opacity=0.3),
            run_time=1.0
        )
        
        # The bridge structure stabilizes with a slight bounce
        self.play(
            bridge_structure.animate.scale(1.02),
            run_time=0.3
        )
        self.play(
            bridge_structure.animate.scale(1.0),
            run_time=0.3
        )
        
        # Change lecture line 5 color
        self.lecture[4].set_color(color_line5)
        
        # Final hold
        self.wait(2)