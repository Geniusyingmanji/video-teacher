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
        self.setup_layout("Sec 3: Dividing to Find x", ['Divide both sides by 2.', 'Split the two x blocks.', 'Split the 12 into two 6s.', 'One x equals one 6.', 'Solution: x is equal to 6.'])
        
        # Initialize colors for lecture lines
        colors = ["#FFA07A", "#87CEFA", "#98FB98", "#FFD700", "#FFFF00"]
        
        # === Animation for Lecture Line 1 ===
        # "Divide both sides by 2."
        self.lecture[0].set_color(colors[0])
        self.play(Write(self.lecture[0]), run_time=1)
        
        # Setup visual elements for the balance scale
        # Left pan: two blue 'x' blocks
        left_pan_center = self.grid['C3']
        left_pan = Rectangle(width=2.5, height=1.5, color=BLUE, fill_opacity=0.3, stroke_width=2)
        self.place_in_area(left_pan, 'B2', 'D4')
        
        x_block_1 = Text("x", font_size=36, color=BLUE)
        x_block_2 = Text("x", font_size=36, color=BLUE)
        self.place_at_grid(x_block_1, 'C2', scale_factor=0.8)
        self.place_at_grid(x_block_2, 'C4', scale_factor=0.8)
        
        # Right pan: one green '12' block
        right_pan_center = self.grid['C5']
        right_pan = Rectangle(width=2.5, height=1.5, color=GREEN, fill_opacity=0.3, stroke_width=2)
        self.place_in_area(right_pan, 'B5', 'D6')
        
        twelve_block = Text("12", font_size=36, color=GREEN)
        self.place_at_grid(twelve_block, 'C5', scale_factor=0.8)
        
        # Add initial visual elements
        self.play(FadeIn(left_pan), FadeIn(right_pan), FadeIn(x_block_1), FadeIn(x_block_2), FadeIn(twelve_block), run_time=1.5)
        
        # Draw vertical divider line through left pan
        left_divider = Line(start=np.array([left_pan.get_center()[0], left_pan.get_top()[1], 0]), 
                           end=np.array([left_pan.get_center()[0], left_pan.get_bottom()[1], 0]), 
                           color=WHITE, stroke_width=2)
        self.play(Create(left_divider), run_time=1)
        
        # === Animation for Lecture Line 2 ===
        # "Split the two x blocks."
        self.lecture[1].set_color(colors[1])
        self.play(Write(self.lecture[1]), run_time=1)
        
        # Visual representation of splitting x blocks (already shown by divider)
        # Add subtle animation to show separation
        x_block_1.animate.shift(LEFT * 0.2)
        x_block_2.animate.shift(RIGHT * 0.2)
        self.play(x_block_1.animate.shift(LEFT * 0.2), x_block_2.animate.shift(RIGHT * 0.2), run_time=1)
        
        # === Animation for Lecture Line 3 ===
        # "Split the 12 into two 6s."
        self.lecture[2].set_color(colors[2])
        self.play(Write(self.lecture[2]), run_time=1)
        
        # Draw vertical divider line through right pan
        right_divider = Line(start=np.array([right_pan.get_center()[0], right_pan.get_top()[1], 0]), 
                            end=np.array([right_pan.get_center()[0], right_pan.get_bottom()[1], 0]), 
                            color=WHITE, stroke_width=2)
        self.play(Create(right_divider), run_time=1)
        
        # Replace 12 block with two 6 blocks
        six_block_1 = Text("6", font_size=36, color=GREEN)
        six_block_2 = Text("6", font_size=36, color=GREEN)
        self.place_at_grid(six_block_1, 'C4', scale_factor=0.8)
        self.place_at_grid(six_block_2, 'C6', scale_factor=0.8)
        
        self.play(FadeOut(twelve_block), FadeIn(six_block_1), FadeIn(six_block_2), run_time=1.5)
        
        # === Animation for Lecture Line 4 ===
        # "One x equals one 6."
        self.lecture[3].set_color(colors[3])
        self.play(Write(self.lecture[3]), run_time=1)
        
        # Fade out the right 'x' block and the right '6' block
        self.play(FadeOut(x_block_2), FadeOut(six_block_2), run_time=1.5)
        
        # Highlight the remaining blue 'x' and green '6' with a glowing pulse
        x_highlight = SurroundingRectangle(x_block_1, color=YELLOW, buff=0.1, stroke_width=3)
        six_highlight = SurroundingRectangle(six_block_1, color=YELLOW, buff=0.1, stroke_width=3)
        self.place_at_grid(x_highlight, 'C2', scale_factor=0.8)
        self.place_at_grid(six_highlight, 'C4', scale_factor=0.8)
        
        self.play(Create(x_highlight), Create(six_highlight), run_time=1)
        self.play(Indicate(x_block_1, scale_factor=1.2), Indicate(six_block_1, scale_factor=1.2), run_time=1.5)
        self.play(FadeOut(x_highlight), FadeOut(six_highlight), run_time=0.5)
        
        # === Animation for Lecture Line 5 ===
        # "Solution: x is equal to 6."
        self.lecture[4].set_color(colors[4])
        self.play(Write(self.lecture[4]), run_time=1)
        
        # Update the equation label to 'x = 6' in bright yellow
        equation_label = Text("x = 6", font_size=48, color="#FFFF00")
        self.place_in_area(equation_label, 'E3', 'F5', scale_factor=1.0)
        
        self.play(FadeIn(equation_label), run_time=1.5)
        
        # Final pause
        self.wait(2)