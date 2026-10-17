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
        # Colors for each lecture line
        line_colors = [
            "#FFFFFF",  # Line 1: Mass represents inertia.
            "#FF0000",  # Line 2: Force is a vector push.
            "#ADD8E6",  # Line 3: Frictionless means no resistance.
            "#00FF00",  # Line 4: Net force equals applied force.
            "#FFFF00"   # Line 5: Simpler calculations result.
        ]
        
        self.setup_layout(
            "Sec 1: Prerequisite: Understanding Force and Mass", 
            ['Mass represents inertia.', 
             'Force is a vector push.', 
             'Frictionless means no resistance.', 
             'Net force equals applied force.', 
             'Simpler calculations result.']
        )
        
        # === Animation for Lecture Line 1 ===
        # "Mass represents inertia."
        # Color: #FFFFFF
        
        # Highlight lecture line 1
        self.lecture[0].set_color(line_colors[0])
        
        # Animation step 1: A white square block (2kg) fades in at center. Label 'm = 2 kg' in #FFFFFF appears above it.
        # Position: Center of the right grid area, around C3-D3
        block = Square(side_length=1.0, color=WHITE, fill_opacity=1.0, fill_color=WHITE)
        self.place_at_grid(block, 'C3', scale_factor=1.0)
        
        mass_label = Text("m = 2 kg", font_size=24, color=line_colors[0])
        self.place_at_grid(mass_label, 'B3', scale_factor=1.0)
        
        self.play(FadeIn(block), FadeIn(mass_label), run_time=1.5)
        self.wait(0.5)
        
        # === Animation for Lecture Line 2 ===
        # "Force is a vector push."
        # Color: #FF0000
        
        # Highlight lecture line 2
        self.lecture[1].set_color(line_colors[1])
        
        # Animation step 2: A red arrow (#FF0000) labeled 'F' slides in from the left, pointing at the block. Label 'F = 10 N' appears next to it.
        # Arrow pointing right towards the block at C3
        force_arrow = Arrow(
            start=np.array([-2, 0, 0]) + self.grid['C3'], 
            end=np.array([0.5, 0, 0]) + self.grid['C3'] - np.array([0.5, 0, 0]), 
            buff=0.1,
            color=line_colors[1],
            stroke_width=5
        )
        # Recalculate arrow to point at block from left
        block_center = self.grid['C3']
        arrow_start = block_center + np.array([-2, 0, 0])
        arrow_end = block_center + np.array([-0.6, 0, 0])
        force_arrow = Arrow(
            start=arrow_start, 
            end=arrow_end, 
            buff=0.1,
            color=line_colors[1],
            stroke_width=5
        )
        
        force_label = Text("F", font_size=24, color=line_colors[1])
        force_label.next_to(force_arrow, UP, buff=0.2)
        
        force_value_label = Text("F = 10 N", font_size=24, color=line_colors[1])
        force_value_label.next_to(force_arrow, DOWN, buff=0.3)
        
        # Slide in from left
        force_arrow.animate.shift(RIGHT * 0.5)
        self.play(
            Write(force_arrow),
            FadeIn(force_label),
            FadeIn(force_value_label),
            run_time=1.5
        )
        self.wait(0.5)
        
        # === Animation for Lecture Line 3 ===
        # "Frictionless means no resistance."
        # Color: #ADD8E6
        
        # Highlight lecture line 3
        self.lecture[2].set_color(line_colors[3])  # Using line_colors[2]
        self.lecture[2].set_color(line_colors[2])
        
        # Animation step 3: The background surface turns a light icy blue (#ADD8E6) to signify 'frictionless'. Text 'Friction = 0' fades in below.
        # Create a surface rectangle below the block
        surface = Rectangle(
            width=4, 
            height=0.2, 
            color=line_colors[2], 
            fill_opacity=0.5, 
            fill_color=line_colors[2]
        )
        surface.move_to(self.grid['D3'] + np.array([0, -0.5, 0]))
        
        friction_text = Text("Friction = 0", font_size=24, color=line_colors[2])
        self.place_at_grid(friction_text, 'E3', scale_factor=1.0)
        
        self.play(FadeIn(surface), FadeIn(friction_text), run_time=1.5)
        self.wait(0.5)
        
        # === Animation for Lecture Line 4 ===
        # "Net force equals applied force."
        # Color: #00FF00
        
        # Highlight lecture line 4
        self.lecture[3].set_color(line_colors[3])
        
        # Animation step 4: The red arrow pulses slightly to emphasize the push. The block remains stationary initially.
        # Pulse the arrow
        self.play(
            force_arrow.animate.scale(1.1),
            run_time=0.3
        )
        self.play(
            force_arrow.animate.scale(1/1.1),
            run_time=0.3
        )
        
        # Animation step 5: A green checkmark (#00FF00) appears next to 'Net Force = F', confirming the simplification.
        net_force_text = Text("Net Force = F", font_size=24, color=line_colors[3])
        self.place_at_grid(net_force_text, 'F3', scale_factor=1.0)
        
        checkmark = Text("✓", font_size=32, color=line_colors[3])
        checkmark.next_to(net_force_text, RIGHT, buff=0.2)
        
        self.play(FadeIn(net_force_text), FadeIn(checkmark), run_time=1.0)
        self.wait(0.5)
        
        # === Animation for Lecture Line 5 ===
        # "Simpler calculations result."
        # Color: #FFFF00
        
        # Highlight lecture line 5
        self.lecture[4].set_color(line_colors[4])
        
        # Brief pause to show final state
        self.wait(1.0)
        
        # Clean up
        self.clear()