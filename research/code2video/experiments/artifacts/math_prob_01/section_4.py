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
        self.setup_layout("Sec 4: Verification and Conclusion", [
            'Check: Substitute x with 6.', 
            'Calculate: 2 times 6 plus 5.', 
            'Result: 12 plus 5 is 17.', 
            '17 equals 17, balance holds.', 
            'Solution verified: x equals 6.'
        ])
        
        # Define colors for lecture lines
        self.line_colors = [
            "#FFD700",  # Gold for line 1
            "#4FC3F7",  # Light blue for line 2
            "#81C784",  # Light green for line 3
            "#FFB74D",  # Light orange for line 4
            "#E1BEE7"   # Light purple for line 5
        ]
        
        # === Animation for Lecture Line 1 ===
        # Highlight lecture line 1
        self.lecture[0].set_color(self.line_colors[0])
        self.wait(0.5)
        
        # Create balance scale visualization
        # Left pan with x block
        left_pan = Rectangle(width=2, height=0.3, color=WHITE, fill_opacity=0.3)
        self.place_at_grid(left_pan, "B3", scale_factor=0.8)
        
        # x block on left pan
        x_block = Text("x", font_size=36, color="#2196F3")
        self.place_at_grid(x_block, "B3", scale_factor=0.8)
        
        # Right pan with 17 block
        right_pan = Rectangle(width=2, height=0.3, color=WHITE, fill_opacity=0.3)
        self.place_at_grid(right_pan, "B5", scale_factor=0.8)
        
        # 17 block on right pan
        right_block = Text("17", font_size=36, color="#4CAF50")
        self.place_at_grid(right_block, "B5", scale_factor=0.8)
        
        # Balance beam
        beam = Line(ORIGIN, RIGHT * 4, color=WHITE, stroke_width=4)
        beam.move_to(np.array([3.0, 1.2, 0]))
        self.add(beam)
        
        # Support
        support = Triangle(color=WHITE, fill_opacity=0.5)
        support.scale(0.5)
        support.move_to(np.array([3.0, 0.5, 0]))
        self.add(support)
        
        self.add(left_pan, x_block, right_pan, right_block)
        self.wait(1)
        
        # Replace x with 6
        six_block = Text("6", font_size=36, color="#4CAF50")
        self.place_at_grid(six_block, "B3", scale_factor=0.8)
        
        self.play(ReplacementTransform(x_block, six_block), run_time=1)
        
        # Show 2(6) label
        label_26 = Text("2(6)", font_size=24, color="#4FC3F7")
        self.place_at_grid(label_26, "A3", scale_factor=0.8)
        self.play(FadeIn(label_26), run_time=0.8)
        self.wait(1)
        
        # === Animation for Lecture Line 2 ===
        # Highlight lecture line 2
        self.lecture[1].set_color(self.line_colors[1])
        self.wait(0.5)
        
        # Calculate 12 + 5
        calc_text = Text("12 + 5", font_size=28, color="#4FC3F7")
        self.place_at_grid(calc_text, "A3", scale_factor=0.8)
        
        self.play(ReplacementTransform(label_26, calc_text), run_time=0.8)
        self.wait(1)
        
        # Show sum 17
        sum_text = Text("= 17", font_size=28, color="#81C784")
        self.place_at_grid(sum_text, "A4", scale_factor=0.8)
        self.play(FadeIn(sum_text), run_time=0.8)
        self.wait(1)
        
        # === Animation for Lecture Line 3 ===
        # Highlight lecture line 3
        self.lecture[2].set_color(self.line_colors[2])
        self.wait(0.5)
        
        # Replace 6 block with 17 block on left
        left_17_block = Text("17", font_size=36, color="#4CAF50")
        self.place_at_grid(left_17_block, "B3", scale_factor=0.8)
        
        self.play(
            ReplacementTransform(six_block, left_17_block),
            FadeOut(calc_text),
            FadeOut(sum_text),
            run_time=1
        )
        self.wait(1)
        
        # === Animation for Lecture Line 4 ===
        # Highlight lecture line 4
        self.lecture[3].set_color(self.line_colors[3])
        self.wait(0.5)
        
        # Balance beam glows gold
        beam_gold = Line(ORIGIN, RIGHT * 4, color="#FFD700", stroke_width=6)
        beam_gold.move_to(np.array([3.0, 1.2, 0]))
        
        self.play(ReplacementTransform(beam, beam_gold), run_time=1)
        self.wait(1)
        
        # === Animation for Lecture Line 5 ===
        # Highlight lecture line 5
        self.lecture[4].set_color(self.line_colors[4])
        self.wait(0.5)
        
        # Create confetti particles
        confetti_colors = ["#FF5722", "#2196F3", "#4CAF50"]
        confetti_dots = VGroup()
        
        for i in range(15):
            dot = Circle(radius=0.05, color=confetti_colors[i % 3], fill_opacity=1)
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.uniform(0.5, 2.0)
            x = 3.0 + radius * np.cos(angle)
            y = 1.5 + radius * np.sin(angle)
            dot.move_to(np.array([x, y, 0]))
            confetti_dots.add(dot)
        
        self.add(confetti_dots)
        
        # Animate confetti falling
        for dot in confetti_dots:
            self.play(dot.animate.shift(DOWN * 2), run_time=1.5)
        
        self.wait(1)
        
        # Final message
        final_text = Text("Solution Verified!", font_size=32, color="#FFD700")
        self.place_in_area(final_text, "E2", "F5", scale_factor=0.8)
        self.play(FadeIn(final_text), run_time=1)
        self.wait(2)
        
        # Cleanup
        self.play(
            FadeOut(final_text),
            FadeOut(confetti_dots),
            FadeOut(beam_gold),
            FadeOut(support),
            FadeOut(left_pan),
            FadeOut(left_17_block),
            FadeOut(right_pan),
            FadeOut(right_block),
            run_time=1
        )