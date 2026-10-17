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
        self.setup_layout("Sec 3: Step-by-Step Calculation", ['Given concentration is one times ten power negative three.', 'Substitute this value into the formula.', 'Logarithm of ten power negative three is negative three.', 'Apply the negative sign to the result.', 'Final pH is three.'])
        
        # === Animation for Lecture Line 1 ===
        # Highlight Lecture Line 1
        self.lecture[0].set_color("#FFD700")
        
        # Create concentration text on the left side of the grid area
        # Place it around B1-C1 area
        conc_text = Text("[H+] = 1 × 10⁻³ M", font_size=30, color="#FFFFFF")
        self.place_in_area(conc_text, "B1", "C2", scale_factor=0.8)
        self.play(Write(conc_text), run_time=1.5)
        self.wait(0.5)

        # === Animation for Lecture Line 2 ===
        # Highlight Lecture Line 2
        self.lecture[1].set_color("#87CEEB")
        
        # Create the formula pH = -log10( ) in the center
        # Place it around C3-C4 area
        formula_text = Text("pH = -log₁₀( )", font_size=30, color="#FFFFFF")
        self.place_in_area(formula_text, "C3", "C4", scale_factor=0.9)
        self.play(Write(formula_text), run_time=1.5)
        
        # Move the value '1 × 10⁻³' into the formula
        # Extract the value part from conc_text or create a new one
        value_text = Text("1 × 10⁻³", font_size=28, color="#FFFFFF")
        self.place_at_grid(value_text, "B2", scale_factor=0.8)
        
        # Create a placeholder for the value inside the formula
        # We'll animate the value moving into the formula position
        # The formula is at C3-C4 center. The empty space is at the end.
        # Let's create a version of the formula with the value inserted
        formula_filled = Text("pH = -log₁₀(1 × 10⁻³)", font_size=30, color="#FFFFFF")
        self.place_in_area(formula_filled, "C3", "C4", scale_factor=0.9)
        
        # Animate the value moving from its position to the formula
        # First, hide the original formula and show the filled one
        # But we need to show the movement. Let's use Transform or MoveTo.
        # Since we can't use Transform on the lecture lines, but we can on other objects.
        # Let's animate the value_text moving to the position inside the formula.
        
        # Calculate target position for the value inside the formula
        # The formula "pH = -log₁₀(1 × 10⁻³)" has the value at the end.
        # We'll just move the value_text to the approximate position where it fits in the formula.
        # For simplicity, we'll fade out the empty formula and the separate value,
        # and fade in the filled formula.
        
        self.play(value_text.animate.move_to(formula_text.get_center() + np.array([0.5, 0, 0])), run_time=1.0)
        self.play(FadeOut(formula_text), FadeOut(value_text), run_time=0.5)
        self.play(FadeIn(formula_filled), run_time=0.5)
        self.wait(0.5)

        # === Animation for Lecture Line 3 ===
        # Highlight Lecture Line 3
        self.lecture[2].set_color("#FF69B4")
        
        # Highlight the log term in the formula
        # We'll create a highlight box around "log₁₀(1 × 10⁻³)"
        log_term = Text("log₁₀(1 × 10⁻³)", font_size=30, color="#FFFFFF")
        self.place_in_area(log_term, "C3", "C4", scale_factor=0.9)
        
        # Create a highlight rectangle around the log term
        highlight_box = SurroundingRectangle(log_term, color="#FFFF00", buff=0.1)
        self.play(Create(highlight_box), run_time=1.0)
        
        # Show the result '-3' below the log term in red
        result_neg3 = Text("-3", font_size=30, color="#FF0000")
        self.place_at_grid(result_neg3, "D4", scale_factor=0.8)
        self.play(Write(result_neg3), run_time=1.0)
        self.wait(0.5)

        # === Animation for Lecture Line 4 ===
        # Highlight Lecture Line 4
        self.lecture[3].set_color("#9370DB")
        
        # Show the negative sign combining with '-3'
        # Create the expression '-(-3)'
        neg_neg3_text = Text("-(-3)", font_size=30, color="#FFFFFF")
        self.place_at_grid(neg_neg3_text, "D5", scale_factor=0.8)
        
        # Animate the negative sign from the formula to combine with -3
        # We'll just show the transformation
        self.play(FadeOut(result_neg3), FadeOut(highlight_box), run_time=0.5)
        self.play(Write(neg_neg3_text), run_time=1.0)
        
        # Transform '-(-3)' into '3' in green
        result_3 = Text("3", font_size=30, color="#00FF00")
        self.place_at_grid(result_3, "D5", scale_factor=0.8)
        self.play(Transform(neg_neg3_text, result_3), run_time=1.0)
        self.wait(0.5)

        # === Animation for Lecture Line 5 ===
        # Highlight Lecture Line 5
        self.lecture[4].set_color("#00FF00")
        
        # Show the final equation 'pH = 3'
        final_equation = Text("pH = 3", font_size=35, color="#00FF00")
        self.place_in_area(final_equation, "E3", "E4", scale_factor=1.0)
        
        # Animate the final equation appearing
        self.play(FadeIn(final_equation), run_time=1.0)
        
        # Scale up slightly for emphasis
        self.play(final_equation.animate.scale(1.2), run_time=0.5)
        
        # Add a glow effect (simulated with a bright color and slight scale)
        final_equation_glow = Text("pH = 3", font_size=35, color="#00FF00")
        self.place_in_area(final_equation_glow, "E3", "E4", scale_factor=1.2)
        
        self.play(FadeOut(final_equation), run_time=0.3)
        self.play(FadeIn(final_equation_glow), run_time=0.5)
        
        self.wait(2)