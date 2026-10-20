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

class Section4Scene(TeachingScene):
    def construct(self):
        self.setup_layout(
            "Sec 4: Applying the Rules: Step-by-Step Differentiation",
            [
                "Function: f(x) = x^3 + 2x.",
                "Differentiate each term separately.",
                "Term 1: x^3 becomes 3x^2.",
                "Term 2: 2x becomes 2.",
                "Sum: f'(x) = 3x^2 + 2."
            ]
        )
        
        # Colors for lecture lines
        color1 = "#FFD700"  # Gold for line 1
        color2 = "#87CEEB"  # Light blue for line 2
        color3 = "#98FB98"  # Pale green for line 3
        color4 = "#FFA07A"  # Light salmon for line 4
        color5 = "#FFFFFF"  # White for line 5
        
        # === Animation for Lecture Line 1 ===
        # Highlight lecture line 1
        self.lecture[0].set_color(color1)
        
        # Display f(x) = x^3 + 2x
        func_text = Text("f(x) = x^3 + 2x", font_size=36, color=WHITE)
        self.place_at_grid(func_text, "B3", scale_factor=0.9)
        self.play(Write(func_text), run_time=1.5)
        self.wait(0.5)
        
        # Split into two groups: 'x^3' (blue) and '2x' (red)
        x3_term = Text("x^3", font_size=36, color="#0000FF")
        self.place_at_grid(x3_term, "B2", scale_factor=0.9)
        
        twox_term = Text("2x", font_size=36, color="#FF0000")
        self.place_at_grid(twox_term, "B4", scale_factor=0.9)
        
        # Show the split terms
        self.play(
            FadeIn(x3_term, shift=LEFT * 0.5),
            FadeIn(twox_term, shift=RIGHT * 0.5),
            run_time=1.0
        )
        self.wait(0.5)
        
        # === Animation for Lecture Line 2 ===
        # Highlight lecture line 2
        self.lecture[1].set_color(color2)
        
        # Show differentiation instruction
        diff_text = Text("Differentiate each term", font_size=28, color="#87CEEB")
        self.place_at_grid(diff_text, "C3", scale_factor=0.8)
        self.play(FadeIn(diff_text), run_time=1.0)
        self.wait(0.5)
        
        # === Animation for Lecture Line 3 ===
        # Highlight lecture line 3
        self.lecture[2].set_color(color3)
        
        # Animate x^3 transforming to 3x^2 using power rule
        # Show power rule steps
        power_rule_text = Text("Power Rule: x^n -> n*x^(n-1)", font_size=24, color="#98FB98")
        self.place_at_grid(power_rule_text, "D2", scale_factor=0.7)
        self.play(FadeIn(power_rule_text), run_time=1.0)
        
        # Show transformation: x^3 -> 3x^2
        x3_result = Text("3x^2", font_size=36, color="#0000FF")
        self.place_at_grid(x3_result, "D3", scale_factor=0.9)
        
        # Animate the transformation
        self.play(
            TransformFromCopy(x3_term, x3_result),
            run_time=1.5
        )
        self.wait(0.5)
        
        # === Animation for Lecture Line 4 ===
        # Highlight lecture line 4
        self.lecture[3].set_color(color4)
        
        # Animate 2x transforming to 2
        # Show that 2x = 2*x^1
        twox_expanded = Text("2*x^1", font_size=28, color="#FFA07A")
        self.place_at_grid(twox_expanded, "D4", scale_factor=0.8)
        self.play(FadeIn(twox_expanded), run_time=1.0)
        
        # Show transformation: 2x^1 -> 2*1*x^0 = 2
        twox_result = Text("2", font_size=36, color="#FF0000")
        self.place_at_grid(twox_result, "D5", scale_factor=0.9)
        
        self.play(
            TransformFromCopy(twox_term, twox_result),
            run_time=1.5
        )
        self.wait(0.5)
        
        # === Animation for Lecture Line 5 ===
        # Highlight lecture line 5
        self.lecture[4].set_color(color5)
        
        # Clean up previous elements
        self.play(
            FadeOut(func_text),
            FadeOut(x3_term),
            FadeOut(twox_term),
            FadeOut(diff_text),
            FadeOut(power_rule_text),
            FadeOut(twox_expanded),
            run_time=1.0
        )
        
        # Combine results: 3x^2 + 2
        sum_text = Text("f'(x) = 3x^2 + 2", font_size=36, color="#FFFFFF")
        self.place_at_grid(sum_text, "E3", scale_factor=0.9)
        self.play(Write(sum_text), run_time=1.5)
        self.wait(0.5)
        
        # Add checkmark
        checkmark = Text("✓", font_size=48, color="#00FF00")
        self.place_at_grid(checkmark, "E4", scale_factor=0.8)
        self.play(Create(checkmark), run_time=1.0)
        self.wait(1.0)
        
        # Final hold
        self.wait(1.0)