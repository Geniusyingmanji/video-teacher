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
        # Setup colors for lecture lines
        self.lecture_colors = [
            "#FFD700",  # Gold for Line 1
            "#00FFFF",  # Cyan for Line 2
            "#FF69B4",  # Hot Pink for Line 3
            "#90EE90",  # Light Green for Line 4
            "#FFA500"   # Orange for Line 5
        ]

        self.setup_layout(
            "Sec 3: Handling Coefficients: The Constant Multiple Rule", 
            [
                'Constant multiplier stays in place.', 
                'Rule: d/dx [c * x^n].', 
                'Result: c * n * x^(n-1).', 
                "Coefficient 'c' is not affected.", 
                'Example: 4x^2 becomes 8x.'
            ]
        )

        # Initialize main animation area objects
        # We will build the equation step-by-step in the center-right area
        
        # === Animation for Lecture Line 1 ===
        # "Constant multiplier stays in place."
        self.lecture[0].set_color(self.lecture_colors[0])
        
        # Step 1: Display '4x^2' (color #00FFFF). The number '4' sits on a small grey (#888888) platform.
        # Let's create the components for the initial expression.
        # We'll place the main expression roughly in the center of the grid area (C3-D4)
        
        num_4 = Text("4", font_size=60, color="#00FFFF")
        var_x = Text("x", font_size=60, color="#00FFFF")
        exp_2 = Text("2", font_size=30, color="#00FFFF")
        
        # Positioning the initial "4x^2"
        # Let's use grid C3 as the anchor for the '4'
        self.place_at_grid(num_4, 'C3', scale_factor=1.0)
        
        # Position 'x' to the right of '4'
        var_x.move_to(num_4.get_right() + RIGHT * 0.3)
        
        # Position exponent '2' above and right of 'x'
        exp_2.move_to(var_x.get_top() + RIGHT * 0.2 + UP * 0.2)
        
        # Create the platform for '4'
        platform = Rectangle(width=0.8, height=0.1, color="#888888", fill_opacity=1, stroke_width=0)
        platform.move_to(num_4.get_bottom() + DOWN * 0.1)
        
        self.play(Write(num_4), run_time=0.5)
        self.play(FadeIn(platform, shift=UP*0.1), run_time=0.3)
        self.play(Write(var_x), run_time=0.5)
        self.play(Write(exp_2), run_time=0.5)
        
        initial_expr = VGroup(num_4, var_x, exp_2)
        
        # === Animation for Lecture Line 2 ===
        # "Rule: d/dx [c * x^n]."
        self.lecture[1].set_color(self.lecture_colors[1])
        
        # Step 2: Focus on 'x^2'. The exponent '2' drops down to join the '4', becoming '4 * 2'.
        # We need to animate the '2' moving down and adding a multiplication sign.
        
        # Create multiplication sign
        mult_sign_1 = Text("*", font_size=60, color="#00FFFF")
        
        # Target position for the dropped '2'
        # It should be to the right of '4', where 'x' was, but 'x' is still there? 
        # The description says: "The exponent '2' drops down to join the '4', becoming '4 * 2'."
        # Usually, this means the coefficient becomes c * n. So visually, we might rearrange.
        # Let's keep '4' and 'x' in place, but move '2' down next to '4'? 
        # Or better: Transform the structure.
        # Let's assume the standard pedagogical move: The 'n' comes down.
        # So '4' stays. 'x' stays. '2' moves down.
        # But the text says "becoming '4 * 2'". This implies a temporary state or a transformation.
        # Let's move the '2' down to the level of the base, next to the '4' or replacing 'x' temporarily?
        # Actually, a common animation is:
        # 4 x^2  -->  4 * 2 * x^(2-1)
        # Let's animate the '2' moving down to the baseline, to the right of '4'.
        
        # Let's clear the space or just move it.
        # Move exp_2 to the position to the right of num_4.
        target_pos_2 = num_4.get_right() + RIGHT * 0.5
        exp_2_new = exp_2.copy()
        
        # Insert multiplication sign between 4 and the moved 2?
        # Let's place mult_sign_1 between 4 and the new position of 2.
        mult_sign_1.move_to(num_4.get_right() + RIGHT * 0.25)
        
        # Animate:
        # 1. Fade in mult_sign
        # 2. Move exp_2 down to baseline, to the right of mult_sign
        # 3. The 'x' is still there. This might look cluttered: 4 * 2 x
        # Let's follow the description strictly: "The exponent '2' drops down to join the '4', becoming '4 * 2'."
        # This implies the focus is on the coefficient part.
        
        self.play(
            FadeIn(mult_sign_1, scale=0.5), 
            exp_2.animate.move_to(target_pos_2).scale(1.5), # Scale up to match base size
            run_time=1.0
        )
        
        # === Animation for Lecture Line 3 ===
        # "Result: c * n * x^(n-1)."
        self.lecture[2].set_color(self.lecture_colors[2])
        
        # Step 3: The exponent '2' changes to '1'. The term becomes '4 * 2 * x^1'.
        # Wait, the description says "The exponent '2' changes to '1'". 
        # This refers to the *remaining* exponent on x.
        # So we have: 4 * 2 (from the dropped exponent) and x^1 (the new exponent on x).
        # Currently we have: 4, *, 2 (moved), x, and the old position of 2 is empty? 
        # No, exp_2 was moved. The 'x' is still there.
        # We need to add a new exponent '1' to the 'x'.
        
        new_exp_1 = Text("1", font_size=30, color="#00FFFF")
        new_exp_1.move_to(var_x.get_top() + RIGHT * 0.2 + UP * 0.2)
        
        # Also, we need a multiplication sign between the '2' and 'x'?
        mult_sign_2 = Text("*", font_size=60, color="#00FFFF")
        mult_sign_2.move_to(exp_2.get_right() + RIGHT * 0.25)
        
        self.play(
            Write(new_exp_1),
            FadeIn(mult_sign_2, scale=0.5),
            run_time=1.0
        )
        
        # Current state: 4 * 2 * x^1
        
        # === Animation for Lecture Line 4 ===
        # "Coefficient 'c' is not affected."
        self.lecture[3].set_color(self.lecture_colors[3])
        
        # Step 4: Simplify '4 * 2' to '8'. The 'x^1' simplifies to 'x'. Result '8x' appears.
        
        # Create the simplified result parts
        num_8 = Text("8", font_size=60, color="#FFA500") # Orange for final result
        var_x_final = Text("x", font_size=60, color="#FFA500")
        
        # Position '8' where '4' was
        num_8.move_to(num_4.get_center())
        # Position 'x' where 'x' was
        var_x_final.move_to(var_x.get_center())
        
        # Animate the simplification
        # 1. Transform 4 * 2 into 8
        # 2. Transform x^1 into x (remove the 1)
        
        # Group the parts to be replaced
        coeff_group = VGroup(num_4, mult_sign_1, exp_2)
        
        self.play(
            Transform(coeff_group, num_8),
            FadeOut(new_exp_1),
            FadeOut(mult_sign_2),
            run_time=1.5
        )
        
        # Now we have 8 and x. Let's align them nicely.
        # 8 is at C3. x is at its original spot.
        # Let's move x to be right next to 8.
        var_x_final.next_to(num_8, RIGHT, buff=0.1)
        
        self.play(
            var_x.animate.become(var_x_final), # Or just move the original x
            run_time=0.5
        )
        
        # Actually, it's cleaner to just replace the whole expression group.
        # Let's restart the final state construction for clarity.
        # We have num_8 at C3.
        # We have var_x (original) and var_x_final.
        # Let's just use var_x_final and remove the old ones.
        
        self.remove(num_4, mult_sign_1, exp_2, var_x, mult_sign_2, new_exp_1)
        self.play(
            Write(num_8),
            Write(var_x_final),
            run_time=0.5
        )
        
        # === Animation for Lecture Line 5 ===
        # "Example: 4x^2 becomes 8x."
        self.lecture[4].set_color(self.lecture_colors[4])
        
        # Step 5: Highlight the original '4' and the final '8' with a connecting line, showing the coefficient remained constant.
        # Since we replaced '4' with '8', we need to show the connection.
        # We can draw a line from the position where '4' was (which is now '8') to... well, it's the same spot.
        # The prompt says: "Highlight the original '4' and the final '8'".
        # Since '4' is gone, maybe we should have kept a ghost or just highlight the '8' and mention the '4'.
        # Or, better, draw a line from the *concept* of the constant.
        # Let's draw a bracket or line under the '8' and label it "Constant".
        # Or, since the prompt asks for a connecting line between original 4 and final 8, and they are in the same place,
        # perhaps we should have animated the '4' moving to '8' or kept the '4' visible briefly.
        
        # Let's add a visual cue: A circle around the '8' and a text "c stays".
        # Or, let's draw a line from the platform (where 4 was) to the 8.
        
        highlight_circle = Circle(radius=0.5, color="#FFA500", stroke_width=2)
        highlight_circle.move_to(num_8.get_center())
        
        # Let's also add a small text annotation
        annotation = Text("c is constant", font_size=20, color="#FFA500")
        annotation.next_to(highlight_circle, DOWN, buff=0.2)
        
        self.play(
            Create(highlight_circle),
            Write(annotation),
            run_time=1.0
        )
        
        # To strictly follow "connecting line", let's draw a line from the platform to the 8
        # The platform is still there.
        line = Line(platform.get_center(), num_8.get_center(), color="#FFA500", stroke_width=2)
        self.play(Create(line), run_time=0.5)
        
        # Hold for a moment
        self.wait(1)
        
        # Cleanup
        self.play(
            FadeOut(num_8),
            FadeOut(var_x_final),
            FadeOut(highlight_circle),
            FadeOut(annotation),
            FadeOut(line),
            FadeOut(platform),
            run_time=1.0
        )