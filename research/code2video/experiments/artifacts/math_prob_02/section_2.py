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
        self.setup_layout("Sec 2: Prerequisite: The Power Rule Formula", ['Power Rule: f(x) = x^n.', "Derivative: f'(x) = n*x^(n-1).", 'Step 1: Bring exponent down front.', 'Step 2: Subtract 1 from exponent.', 'Example: x^5 becomes 5x^4.'])
        
        # === Animation for Lecture Line 1 ===
        # Display formula 'f(x) = x^n' (color #00FFFF) in center. Animate the 'n' turning yellow (#FFFF00).
        self.lecture[0].set_color("#00FFFF")
        
        # Create the base formula components
        f_x = MathTex("f(x)", color="#00FFFF").scale(0.8)
        eq_sign = MathTex("=", color="#00FFFF").scale(0.8)
        x_n_base = MathTex("x", color="#00FFFF").scale(0.8)
        n_exp = MathTex("n", color="#00FFFF").scale(0.8)
        
        # Position n as exponent
        n_exp.next_to(x_n_base, UP, buff=0.05)
        x_n = VGroup(x_n_base, n_exp).arrange(RIGHT, buff=0)
        
        formula1 = VGroup(f_x, eq_sign, x_n).arrange(RIGHT, buff=0.2)
        self.place_in_area(formula1, "B2", "D4", scale_factor=1.0)
        
        self.play(Write(f_x), Write(eq_sign), Write(x_n_base), Write(n_exp), run_time=1.5)
        
        # Animate 'n' turning yellow
        self.play(n_exp.animate.set_color("#FFFF00"), run_time=1.0)
        
        self.wait(1)
        
        # === Animation for Lecture Line 2 ===
        # Transform formula to 'f'(x) = n*x^(n-1)'. The 'n' moves from exponent position to front multiplier position.
        self.lecture[1].set_color("#00FFFF")
        
        # Create derivative formula components
        f_prime_x = MathTex("f'(x)", color="#00FFFF").scale(0.8)
        eq_sign2 = MathTex("=", color="#00FFFF").scale(0.8)
        n_front = MathTex("n", color="#FFFF00").scale(0.8)
        x_base2 = MathTex("x", color="#00FFFF").scale(0.8)
        n_minus_1 = MathTex("n-1", color="#00FFFF").scale(0.8)
        
        # Position n-1 as exponent
        n_minus_1.next_to(x_base2, UP, buff=0.05)
        x_n_minus_1 = VGroup(x_base2, n_minus_1).arrange(RIGHT, buff=0)
        
        formula2 = VGroup(f_prime_x, eq_sign2, n_front, x_n_minus_1).arrange(RIGHT, buff=0.2)
        self.place_in_area(formula2, "B2", "D4", scale_factor=1.0)
        
        # Animate transition from formula1 to formula2
        self.play(
            Transform(f_x, f_prime_x),
            Transform(eq_sign, eq_sign2),
            Transform(x_n_base, x_base2),
            Transform(n_exp, n_minus_1),
            Write(n_front),
            run_time=2.0
        )
        
        self.wait(1)
        
        # === Animation for Lecture Line 3 ===
        # The exponent 'n' changes to 'n-1'. Highlight the subtraction with a red (#FF0000) flash on the '-1'.
        self.lecture[2].set_color("#FF0000")
        
        # Create highlight for the -1 part
        minus_1_part = MathTex("-1", color="#FF0000").scale(0.8)
        
        # We need to isolate the -1 from n-1 for highlighting
        # Since n_minus_1 is a single MathTex, we'll create a visual effect
        # by adding a red circle or box around the -1 part
        
        # Create a red indicator near the exponent
        red_flash = Circle(color="#FF0000", stroke_width=2, radius=0.3)
        # Position it near the -1 part of the exponent
        # The exponent is at the top right of x_base2
        exp_center = n_minus_1.get_center()
        # The -1 is the right part of n-1
        minus_1_pos = n_minus_1.get_right() + np.array([-0.1, 0, 0])
        red_flash.move_to(minus_1_pos)
        
        self.play(FadeIn(red_flash), run_time=0.5)
        self.wait(0.5)
        self.play(FadeOut(red_flash), run_time=0.5)
        
        self.wait(1)
        
        # === Animation for Lecture Line 4 ===
        # Show specific example 'x^5'. Animate the '5' dropping down to become '5' in front.
        self.lecture[3].set_color("#FFFF00")
        
        # Create example formula
        x_5_base = MathTex("x", color="#FFFF00").scale(0.8)
        five_exp = MathTex("5", color="#FFFF00").scale(0.8)
        
        # Position 5 as exponent
        five_exp.next_to(x_5_base, UP, buff=0.05)
        x_5 = VGroup(x_5_base, five_exp).arrange(RIGHT, buff=0)
        
        self.place_in_area(x_5, "C2", "E4", scale_factor=1.0)
        
        # Clear previous formulas
        self.play(FadeOut(formula2), FadeOut(f_prime_x), FadeOut(eq_sign2), FadeOut(n_front), FadeOut(x_n_minus_1), run_time=1.0)
        
        self.play(Write(x_5_base), Write(five_exp), run_time=1.0)
        
        # Animate the '5' moving from exponent to front
        five_front = MathTex("5", color="#FFFF00").scale(0.8)
        
        # Position five_front to the left of x_5_base
        five_front.next_to(x_5_base, LEFT, buff=0.2)
        
        self.play(
            Transform(five_exp, five_front),
            run_time=1.5
        )
        
        self.wait(1)
        
        # === Animation for Lecture Line 5 ===
        # The exponent '5' changes to '4'. Final result '5x^4' glows green (#00FF00) briefly.
        self.lecture[4].set_color("#00FF00")
        
        # Create the final result
        four_exp = MathTex("4", color="#FFFF00").scale(0.8)
        
        # Position 4 as exponent
        four_exp.next_to(x_5_base, UP, buff=0.05)
        
        # Transform the exponent from 5 to 4
        self.play(
            Transform(five_exp, four_exp),
            run_time=1.0
        )
        
        # Now we have 5 in front and x^4
        # Create the complete final expression
        final_result = VGroup(five_front, x_5_base, four_exp).arrange(RIGHT, buff=0.1)
        
        # Make it glow green
        self.play(
            five_front.animate.set_color("#00FF00"),
            x_5_base.animate.set_color("#00FF00"),
            four_exp.animate.set_color("#00FF00"),
            run_time=1.0
        )
        
        # Add a glow effect
        glow_circle = Circle(color="#00FF00", stroke_width=2, radius=1.0)
        glow_circle.set_stroke(opacity=0.3)
        glow_circle.move_to(final_result.get_center())
        
        self.play(FadeIn(glow_circle), run_time=0.5)
        self.wait(1)
        self.play(FadeOut(glow_circle), run_time=0.5)
        
        self.wait(2)