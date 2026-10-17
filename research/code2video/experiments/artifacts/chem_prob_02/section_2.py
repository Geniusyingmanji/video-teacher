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
        self.setup_layout("Sec 2: The Core Formula", ['The formula is pH equals negative log.', 'Concentration is measured in moles per liter.', 'Logarithms act like a compression tool.', 'Negative sign flips the result positive.', 'Higher acidity yields lower pH values.'])

        # Define colors for each lecture line
        color_line1 = "#FFD700"  # Gold
        color_line2 = "#00FFFF"  # Cyan
        color_line3 = "#FF69B4"  # Hot Pink
        color_line4 = "#00FF00"  # Lime Green
        color_line5 = "#FF4500"  # Orange Red

        # === Animation for Lecture Line 1 ===
        # Change color of first lecture line
        self.lecture[0].set_color(color_line1)
        self.play(Write(self.lecture[0]), run_time=1)
        
        # Animation step 1: A central card appears with 'pH = -log10[H+]' in #FFFFFF. The '[H+]' part glows #FF0000.
        formula_text = Text("pH = -log", font_size=36, color=WHITE)
        h_plus_text = Text("[H+]", font_size=36, color="#FF0000")
        formula_group = VGroup(formula_text, h_plus_text).arrange(RIGHT, buff=0.1)
        
        # Place in center of grid area B2-D4
        self.place_in_area(formula_group, 'B2', 'D4', scale_factor=1.0)
        
        # Add a card background
        card_bg = RoundedRectangle(corner_radius=0.2, width=formula_group.width + 0.5, height=formula_group.height + 0.5, color=GRAY, fill_opacity=0.3)
        card_bg.move_to(formula_group)
        
        self.play(Create(card_bg), Write(formula_group), run_time=1.5)
        
        # Make [H+] glow
        glow_effect = SurroundingRectangle(h_plus_text, color="#FF0000", buff=0.05)
        self.play(Create(glow_effect), run_time=0.5)
        self.wait(0.5)
        self.play(FadeOut(glow_effect), run_time=0.5)
        
        self.wait(1)
        self.play(FadeOut(card_bg), FadeOut(formula_group), run_time=0.5)
        self.wait(0.5)

        # === Animation for Lecture Line 2 ===
        # Change color of second lecture line
        self.lecture[1].set_color(color_line2)
        self.play(Write(self.lecture[1]), run_time=1)
        
        # Animation step 2: Text 'mol/L' appears below '[H+]' in #00FFFF to indicate units.
        # Re-create formula for context
        formula_text2 = Text("pH = -log", font_size=36, color=WHITE)
        h_plus_text2 = Text("[H+]", font_size=36, color="#FF0000")
        formula_group2 = VGroup(formula_text2, h_plus_text2).arrange(RIGHT, buff=0.1)
        self.place_in_area(formula_group2, 'B2', 'D4', scale_factor=1.0)
        
        card_bg2 = RoundedRectangle(corner_radius=0.2, width=formula_group2.width + 0.5, height=formula_group2.height + 0.5, color=GRAY, fill_opacity=0.3)
        card_bg2.move_to(formula_group2)
        
        self.play(Create(card_bg2), Write(formula_group2), run_time=1)
        
        # Add mol/L below [H+]
        mol_l_text = Text("mol/L", font_size=24, color="#00FFFF")
        mol_l_text.next_to(h_plus_text2, DOWN, buff=0.3)
        
        self.play(Write(mol_l_text), run_time=0.8)
        self.wait(1)
        
        self.play(FadeOut(card_bg2), FadeOut(formula_group2), FadeOut(mol_l_text), run_time=0.5)
        self.wait(0.5)

        # === Animation for Lecture Line 3 ===
        # Change color of third lecture line
        self.lecture[2].set_color(color_line3)
        self.play(Write(self.lecture[2]), run_time=1)
        
        # Animation step 3: A zipper icon animates over the number '0.001', compressing it into '3' in #FFFF00.
        # Show the number 0.001
        num_text = Text("0.001", font_size=40, color=WHITE)
        self.place_at_grid(num_text, 'C3', scale_factor=1.0)
        
        # Create a simple zipper-like animation effect
        zipper_line = Line(start=num_text.get_left() + np.array([0, -0.3, 0]), end=num_text.get_right() + np.array([0, -0.3, 0]), color="#FF69B4", stroke_width=3)
        zipper_line.move_to(num_text.get_center() + np.array([0, -0.3, 0]))
        
        self.play(Write(num_text), Create(zipper_line), run_time=1)
        
        # Compress animation: transform 0.001 to 3
        compressed_text = Text("3", font_size=40, color="#FFFF00")
        compressed_text.move_to(num_text)
        
        self.play(ReplacementTransform(num_text, compressed_text), FadeOut(zipper_line), run_time=1)
        self.wait(1)
        
        self.play(FadeOut(compressed_text), run_time=0.5)
        self.wait(0.5)

        # === Animation for Lecture Line 4 ===
        # Change color of fourth lecture line
        self.lecture[3].set_color(color_line4)
        self.play(Write(self.lecture[3]), run_time=1)
        
        # Animation step 4: A minus sign appears before the '3', turning it to '-3', then the outer negative sign cancels it to show '3' in #00FF00.
        # Show -log(0.001) = -(-3) = 3
        log_result_text = Text("-(-3)", font_size=36, color=WHITE)
        self.place_at_grid(log_result_text, 'C3', scale_factor=1.0)
        
        self.play(Write(log_result_text), run_time=0.8)
        
        # Show cancellation
        cancel_line = Line(start=log_result_text.get_left(), end=log_result_text.get_right(), color=RED, stroke_width=4)
        cancel_line.move_to(log_result_text.get_center())
        
        self.play(Create(cancel_line), run_time=0.5)
        
        # Final result: 3 in green
        final_result = Text("3", font_size=40, color="#00FF00")
        final_result.move_to(log_result_text)
        
        self.play(ReplacementTransform(log_result_text, final_result), FadeOut(cancel_line), run_time=1)
        self.wait(1)
        
        self.play(FadeOut(final_result), run_time=0.5)
        self.wait(0.5)

        # === Animation for Lecture Line 5 ===
        # Change color of fifth lecture line
        self.lecture[4].set_color(color_line5)
        self.play(Write(self.lecture[4]), run_time=1)
        
        # Animation step 5: An arrow points from high [H+] (left) to low pH number (bottom), emphasizing the inverse relationship.
        # High [H+] label on left
        high_h_label = Text("High [H+]", font_size=28, color="#FF4500")
        self.place_at_grid(high_h_label, 'B2', scale_factor=0.8)
        
        # Low pH number on bottom
        low_ph_label = Text("Low pH", font_size=28, color="#00FF00")
        self.place_at_grid(low_ph_label, 'E4', scale_factor=0.8)
        
        # Create arrow from high [H+] to low pH
        arrow = Arrow(start=high_h_label.get_bottom(), end=low_ph_label.get_top(), buff=0.2, color="#FF4500", stroke_width=4)
        
        self.play(Write(high_h_label), Write(low_ph_label), Create(arrow), run_time=1.5)
        self.wait(2)
        
        # Final fade out
        self.play(FadeOut(high_h_label), FadeOut(low_ph_label), FadeOut(arrow), run_time=1)
        self.wait(1)