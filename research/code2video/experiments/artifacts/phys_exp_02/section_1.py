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
        self.setup_layout("Sec 1: Understanding Refraction", ['Light travels straight until it hits water.', 'It slows down and bends at the boundary.', 'This bending is called refraction.', 'The angle determines how much it bends.', 'Understanding this is key to lenses.'])
        
        # === Animation for Lecture Line 1 ===
        # Highlight lecture line 1
        self.lecture[0].set_color("#FFDD00")
        
        # Draw a straight white line representing light traveling from left to right
        # Start point: left side of the grid area, e.g., A1 area
        # End point: middle of the grid area, e.g., C3 area (boundary)
        start_point = np.array([0.5, 0.7, 0])  # Approx A1-C1 area, slightly right of lecture
        end_point = np.array([3.5, 0.7, 0])    # Approx C3 area, boundary
        
        light_ray = Line(start_point, end_point, color="#FFFFFF", stroke_width=4)
        self.play(Create(light_ray), run_time=1.5)
        
        # === Animation for Lecture Line 2 ===
        # Highlight lecture line 2
        self.lecture[1].set_color("#FF6600")
        
        # Fade in a blue rectangle on the right side to represent water
        # Water area: from C3 to F6 roughly
        water_rect = Rectangle(width=3.5, height=4.5, color="#4488CC", fill_opacity=0.3, stroke_width=2)
        # Position water rect to start at the boundary (x=3.5) and go right
        water_rect.move_to(np.array([5.25, -0.5, 0]))  # Center of right half
        
        self.play(FadeIn(water_rect), run_time=1.0)
        
        # The light line stops at the boundary (already done by ending at boundary)
        
        # === Animation for Lecture Line 3 ===
        # Highlight lecture line 3
        self.lecture[2].set_color("#00CCFF")
        
        # Animate the light line bending downwards as it enters the blue rectangle
        # New end point: inside the water, bent downwards
        refracted_end_point = np.array([5.5, -0.5, 0])  # Inside water, lower
        
        # Create the refracted ray
        refracted_ray = Line(end_point, refracted_end_point, color="#FFFF99", stroke_width=4)
        
        # Animate the change: fade out original end, create new ray
        self.play(
            Create(refracted_ray),
            run_time=1.5
        )
        
        # === Animation for Lecture Line 4 ===
        # Highlight lecture line 4
        self.lecture[3].set_color("#FF00FF")
        
        # Draw a dashed vertical line at the boundary labeled 'Normal'
        normal_line = DashedLine(
            np.array([3.5, 2.0, 0]), 
            np.array([3.5, -2.0, 0]), 
            color="#888888", 
            stroke_width=2
        )
        normal_label = Text("Normal", font_size=18, color="#888888")
        normal_label.next_to(normal_line, UP, buff=0.2)
        
        self.play(Create(normal_line), Write(normal_label), run_time=1.5)
        
        # Show the angle between the incoming ray and normal
        # Incoming ray angle: from start_point to end_point
        # Normal is vertical, so angle is with vertical
        # Create an arc for incidence angle
        incidence_arc = Arc(
            radius=0.5, 
            start_angle=PI/2, 
            angle=-PI/6, 
            color="#FFDD00", 
            stroke_width=2
        )
        incidence_arc.move_to(end_point)
        
        # Show the angle between the refracted ray and normal
        # Refracted ray angle: from end_point to refracted_end_point
        refraction_arc = Arc(
            radius=0.5, 
            start_angle=-PI/2, 
            angle=PI/8, 
            color="#FFFF99", 
            stroke_width=2
        )
        refraction_arc.move_to(end_point)
        
        self.play(Create(incidence_arc), Create(refraction_arc), run_time=1.5)
        
        # === Animation for Lecture Line 5 ===
        # Highlight lecture line 5
        self.lecture[4].set_color("#00FF00")
        
        # Flash the word 'Refraction' in bright cyan at the center of the screen
        refraction_text = Text("Refraction", font_size=48, color="#00FFFF")
        refraction_text.move_to(np.array([3.5, 0, 0]))  # Center of the grid area
        
        self.play(Write(refraction_text), run_time=1.0)
        self.play(Indicate(refraction_text, color="#00FFFF"), run_time=1.0)
        
        # Hold for a moment
        self.wait(2)
        
        # Clean up
        self.play(*[FadeIn(mob) for mob in self.mobjects], run_time=0.5)