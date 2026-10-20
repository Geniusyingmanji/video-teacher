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
        self.setup_layout("Sec 1: The pH Scale and Logarithms", [
            'pH measures acidity from zero to fourteen.', 
            'Red means high hydrogen ion concentration.', 
            'Blue means low hydrogen ion concentration.', 
            'pH equals negative log base ten.', 
            'Logarithms shrink small numbers easily.'
        ])
        
        # Define colors for lecture lines
        line1_color = "#FF9999"  # Light Red
        line2_color = "#FF6666"  # Stronger Red
        line3_color = "#6699FF"  # Light Blue
        line4_color = "#FFFF99"  # Light Yellow
        line5_color = "#99FF99"  # Light Green

        # === Animation for Lecture Line 1 ===
        # "pH measures acidity from zero to fourteen."
        self.lecture[0].set_color(line1_color)
        self.play(Write(self.lecture[0]), run_time=1)
        
        # Animation step 1: A horizontal gradient bar fades in, transitioning from #FF0000 (left) to #0000FF (right). Labels '0' and '14' appear at ends in #FFFFFF.
        # Create a gradient bar using a Rectangle with a gradient fill (approximated by multiple thin rectangles or just a simple bar for simplicity in Manim CE)
        # Since Manim CE doesn't have direct gradient fill for shapes easily without shaders, we'll use a simple Rectangle and color it, or create a visual representation.
        # Let's create a simple bar.
        bar = Rectangle(width=4, height=0.2, color=WHITE)
        # To simulate gradient, we can use a VMobject with a gradient, but standard Rectangle is easier.
        # Let's use a simple bar and label it.
        bar = self.place_in_area(bar, 'B2', 'B5', scale_factor=1.0)
        
        # Create labels for 0 and 14
        label_0 = Text("0", color=WHITE, font_size=20)
        label_14 = Text("14", color=WHITE, font_size=20)
        
        # Position labels near the ends of the bar
        # Bar is in area B2-B5. Center is B3.5.
        # Let's place label 0 at B2 and 14 at B5 roughly.
        label_0 = self.place_at_grid(label_0, 'B2', scale_factor=1.0)
        label_14 = self.place_at_grid(label_14, 'B5', scale_factor=1.0)
        
        # Adjust label positions to be just below the bar
        label_0.shift(DOWN * 0.3)
        label_14.shift(DOWN * 0.3)
        
        self.play(FadeIn(bar), FadeIn(label_0), FadeIn(label_14), run_time=1.5)
        
        # === Animation for Lecture Line 2 ===
        # "Red means high hydrogen ion concentration."
        self.lecture[1].set_color(line2_color)
        self.play(Write(self.lecture[1]), run_time=1)
        
        # Animation step 2: A red dot pulses at the left end. Text '[H+] = 1' appears in #FF0000 next to it.
        red_dot = Dot(color="#FF0000", radius=0.1)
        # Place at left end of bar (near B2)
        red_dot = self.place_at_grid(red_dot, 'B2', scale_factor=1.0)
        red_dot.shift(DOWN * 0.1) # Align with bar
        
        text_h_plus_red = Text("[H+] = 1", color="#FF0000", font_size=18)
        text_h_plus_red = self.place_at_grid(text_h_plus_red, 'B3', scale_factor=1.0)
        text_h_plus_red.shift(DOWN * 0.5) # Below the dot/bar
        
        self.play(FadeIn(red_dot), run_time=0.5)
        self.play(Indicate(red_dot, color="#FF0000"), run_time=1)
        self.play(FadeIn(text_h_plus_red), run_time=1)
        
        # === Animation for Lecture Line 3 ===
        # "Blue means low hydrogen ion concentration."
        self.lecture[2].set_color(line3_color)
        self.play(Write(self.lecture[2]), run_time=1)
        
        # Animation step 3: A blue dot pulses at the right end. Text '[H+] = 1e-14' appears in #0000FF next to it.
        blue_dot = Dot(color="#0000FF", radius=0.1)
        # Place at right end of bar (near B5)
        blue_dot = self.place_at_grid(blue_dot, 'B5', scale_factor=1.0)
        blue_dot.shift(DOWN * 0.1) # Align with bar
        
        text_h_plus_blue = Text("[H+] = 1e-14", color="#0000FF", font_size=18)
        text_h_plus_blue = self.place_at_grid(text_h_plus_blue, 'B4', scale_factor=1.0)
        text_h_plus_blue.shift(DOWN * 0.5) # Below the dot/bar
        
        self.play(FadeIn(blue_dot), run_time=0.5)
        self.play(Indicate(blue_dot, color="#0000FF"), run_time=1)
        self.play(FadeIn(text_h_plus_blue), run_time=1)
        
        # === Animation for Lecture Line 4 ===
        # "pH equals negative log base ten."
        self.lecture[3].set_color(line4_color)
        self.play(Write(self.lecture[3]), run_time=1)
        
        # Animation step 4: The formula 'pH = -log10[H+]' slides down from the top in #FFFF00. The term '[H+]' highlights in #FF0000.
        formula = MathTex("pH", "=", "-", "log_{10}", "[H^+]")
        formula.set_color("#FFFF00")
        # Highlight [H+] in red
        formula[4].set_color("#FF0000")
        
        # Place formula in area C2-C5
        formula = self.place_in_area(formula, 'C2', 'C5', scale_factor=1.0)
        
        # Start from top
        formula_start = formula.copy()
        formula_start.shift(UP * 3)
        
        self.play(Write(formula_start), run_time=1)
        self.play(formula_start.animate.move_to(formula.get_center()), run_time=1)
        
        # Highlight the [H+] part specifically
        self.play(Indicate(formula[4], color="#FF0000"), run_time=1)
        
        # === Animation for Lecture Line 5 ===
        # "Logarithms shrink small numbers easily."
        self.lecture[4].set_color(line5_color)
        self.play(Write(self.lecture[4]), run_time=1)
        
        # Animation step 5: A small number '0.0001' shrinks rapidly into a single digit '4' with a compression effect, illustrating the log concept.
        small_num = Text("0.0001", color="#99FF99", font_size=30)
        large_num = Text("4", color="#99FF99", font_size=30)
        
        # Place in area D2-D5
        small_num = self.place_in_area(small_num, 'D2', 'D5', scale_factor=1.0)
        
        self.play(FadeIn(small_num), run_time=0.5)
        
        # Animate shrinking
        self.play(small_num.animate.scale(0.2), run_time=1)
        
        # Replace with '4'
        self.play(FadeOut(small_num), FadeIn(large_num), run_time=0.5)
        large_num = self.place_in_area(large_num, 'D2', 'D5', scale_factor=1.0)
        
        # Keep everything on screen for a moment
        self.wait(2)