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
        self.setup_layout("Sec 2: Isolating the Variable Group", [
            'We need to isolate the x.', 
            'Subtract 5 from both sides.', 
            'Left side: 5 cancels with -5.', 
            'Right side: 17 minus 5 is 12.', 
            'New equation: 2x equals 12.'
        ])

        # Define colors for consistency
        YELLOW = "#FFEB3B"
        RED = "#F44336"
        GREEN = "#8BC34A"
        CYAN = "#00FFFF"
        GRAY = "#9E9E9E"
        WHITE = "#FFFFFF"

        # Create the balance scale structure
        # Base
        base = Rectangle(width=4, height=0.2, color=GRAY, fill_opacity=1, fill_color=GRAY)
        self.place_in_area(base, 'E4', 'F4', scale_factor=1.0)
        
        # Pillar
        pillar = Rectangle(width=0.2, height=1.5, color=GRAY, fill_opacity=1, fill_color=GRAY)
        self.place_in_area(pillar, 'D4', 'E4', scale_factor=1.0)
        
        # Beam
        beam = Rectangle(width=6, height=0.1, color=GRAY, fill_opacity=1, fill_color=GRAY)
        self.place_in_area(beam, 'D4', 'D4', scale_factor=1.0)
        
        # Hangers (simple lines)
        left_hanger = Line(ORIGIN, DOWN * 0.5, color=GRAY)
        right_hanger = Line(ORIGIN, DOWN * 0.5, color=GRAY)
        
        # Position hangers relative to beam ends
        beam_center = self.grid['D4']
        left_hanger.move_to(beam_center + LEFT * 2.5)
        right_hanger.move_to(beam_center + RIGHT * 2.5)
        
        # Pans (circles)
        left_pan = Circle(radius=0.8, color=GRAY, fill_opacity=0.2, fill_color=GRAY)
        right_pan = Circle(radius=0.8, color=GRAY, fill_opacity=0.2, fill_color=GRAY)
        
        left_pan.move_to(left_hanger.get_end())
        right_pan.move_to(right_hanger.get_end())
        
        scale_group = VGroup(base, pillar, beam, left_hanger, right_hanger, left_pan, right_pan)
        self.add(scale_group)

        # Create blocks
        # Left Pan: 2x and 5
        block_2x = Square(side_length=0.6, color=BLUE, fill_opacity=1, fill_color=BLUE)
        text_2x = Text("2x", font_size=20, color=WHITE)
        block_2x.add(text_2x)
        block_2x.move_to(left_pan.get_center() + LEFT * 0.3 + DOWN * 0.2)
        
        block_5 = Square(side_length=0.6, color=YELLOW, fill_opacity=1, fill_color=YELLOW)
        text_5 = Text("5", font_size=20, color=WHITE)
        block_5.add(text_5)
        block_5.move_to(left_pan.get_center() + RIGHT * 0.3 + DOWN * 0.2)
        
        # Right Pan: 17
        block_17 = Square(side_length=0.6, color=GREEN, fill_opacity=1, fill_color=GREEN)
        text_17 = Text("17", font_size=20, color=WHITE)
        block_17.add(text_17)
        block_17.move_to(right_pan.get_center() + DOWN * 0.2)
        
        self.add(block_2x, block_5, block_17)

        # Equation Label
        eq_label = Text("2x + 5 = 17", font_size=28, color=WHITE)
        self.place_in_area(eq_label, 'A4', 'B4', scale_factor=0.8)
        self.add(eq_label)

        # === Animation for Lecture Line 1 ===
        # "We need to isolate the x."
        self.lecture[0].set_color(CYAN)
        self.play(Write(self.lecture[0]), run_time=1)
        
        # Highlight 2x block to show what we want to isolate
        highlight_2x = SurroundingRectangle(block_2x, color=CYAN, buff=0.1)
        self.play(Create(highlight_2x), run_time=1)
        self.wait(1)
        self.play(FadeOut(highlight_2x), run_time=0.5)

        # === Animation for Lecture Line 2 ===
        # "Subtract 5 from both sides."
        self.lecture[1].set_color(CYAN)
        self.play(Write(self.lecture[1]), run_time=1)
        
        # Highlight the '5' block on the left with a red outline
        outline_5 = SurroundingRectangle(block_5, color=RED, buff=0.05, stroke_width=3)
        self.play(Create(outline_5), run_time=1)
        self.wait(1)
        self.play(FadeOut(outline_5), run_time=0.5)

        # === Animation for Lecture Line 3 ===
        # "Left side: 5 cancels with -5."
        self.lecture[2].set_color(CYAN)
        self.play(Write(self.lecture[2]), run_time=1)
        
        # Spawn -5 blocks on both pans
        block_neg5_left = Square(side_length=0.6, color=RED, fill_opacity=1, fill_color=RED)
        text_neg5_left = Text("-5", font_size=20, color=WHITE)
        block_neg5_left.add(text_neg5_left)
        block_neg5_left.move_to(left_pan.get_center() + RIGHT * 0.8 + DOWN * 0.2)
        
        block_neg5_right = Square(side_length=0.6, color=RED, fill_opacity=1, fill_color=RED)
        text_neg5_right = Text("-5", font_size=20, color=WHITE)
        block_neg5_right.add(text_neg5_right)
        block_neg5_right.move_to(right_pan.get_center() + RIGHT * 0.8 + DOWN * 0.2)
        
        self.play(GrowFromCenter(block_neg5_left), GrowFromCenter(block_neg5_right), run_time=1)
        self.wait(1)
        
        # Merge and fade out the 5 and -5 on the left
        # Create smoke effect (simple fade out with scale)
        self.play(
            FadeOut(block_5, shift=UP * 0.5),
            FadeOut(block_neg5_left, shift=UP * 0.5),
            run_time=1.5
        )

        # === Animation for Lecture Line 4 ===
        # "Right side: 17 minus 5 is 12."
        self.lecture[3].set_color(CYAN)
        self.play(Write(self.lecture[3]), run_time=1)
        
        # Fade out the -5 on the right
        self.play(FadeOut(block_neg5_right), run_time=0.5)
        
        # Change 17 to 12
        block_12 = Square(side_length=0.6, color=GREEN, fill_opacity=1, fill_color=GREEN)
        text_12 = Text("12", font_size=20, color=WHITE)
        block_12.add(text_12)
        block_12.move_to(block_17.get_center())
        
        self.play(
            Transform(block_17, block_12),
            run_time=1
        )
        self.wait(1)

        # === Animation for Lecture Line 5 ===
        # "New equation: 2x equals 12."
        self.lecture[4].set_color(CYAN)
        self.play(Write(self.lecture[4]), run_time=1)
        
        # Update equation label
        new_eq_label = Text("2x = 12", font_size=28, color=CYAN)
        self.place_in_area(new_eq_label, 'A4', 'B4', scale_factor=0.8)
        
        self.play(
            Transform(eq_label, new_eq_label),
            run_time=1
        )
        self.wait(2)
        
        # Final cleanup
        self.play(FadeOut(self.lecture), FadeOut(eq_label), FadeOut(scale_group), FadeOut(block_2x), FadeOut(block_12), run_time=1)