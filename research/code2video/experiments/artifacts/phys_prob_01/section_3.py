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
        self.setup_layout("Sec 3: Step-by-Step Problem Solving", ['Knowns: m=2kg, F=10N.', 'Unknown: acceleration a.', 'Rearrange: a equals F over m.', 'Substitute: a equals 10 over 2.', 'Result: a is 5 m/s squared.'])
        
        # Define colors for each lecture line
        color_line1 = "#87CEEB"  # Light Sky Blue
        color_line2 = "#FFD700"  # Gold
        color_line3 = "#98FB98"  # Pale Green
        color_line4 = "#FFA07A"  # Light Salmon
        color_line5 = "#00FF00"  # Green

        # === Animation for Lecture Line 1 ===
        # Highlight lecture line 1
        self.lecture[0].set_color(color_line1)
        self.play(Write(self.lecture[0]), run_time=1)

        # Animation step 1: Two boxes appear
        box1_text = Text("m = 2 kg", font_size=24, color=WHITE)
        box1_bg = RoundedRectangle(corner_radius=0.1, width=2.5, height=0.8, fill_color="#333333", fill_opacity=1, stroke_color=WHITE, stroke_width=1)
        box1 = VGroup(box1_bg, box1_text).arrange(DOWN, buff=0.1)
        box1_text.move_to(box1_bg)
        
        box2_text = Text("F = 10 N", font_size=24, color=WHITE)
        box2_bg = RoundedRectangle(corner_radius=0.1, width=2.5, height=0.8, fill_color="#333333", fill_opacity=1, stroke_color=WHITE, stroke_width=1)
        box2 = VGroup(box2_bg, box2_text).arrange(DOWN, buff=0.1)
        box2_text.move_to(box2_bg)

        # Place boxes in grid A2 and A4
        self.place_at_grid(box1, 'A2', scale_factor=0.8)
        self.place_at_grid(box2, 'A4', scale_factor=0.8)

        self.play(FadeIn(box1), FadeIn(box2), run_time=1.5)

        # === Animation for Lecture Line 2 ===
        # Highlight lecture line 2
        self.lecture[1].set_color(color_line2)
        self.play(Write(self.lecture[1]), run_time=1)

        # Animation step 2: Question mark in yellow box, formula below
        q_text = Text("a = ?", font_size=28, color=WHITE)
        q_bg = RoundedRectangle(corner_radius=0.1, width=2.0, height=0.8, fill_color="#FFD700", fill_opacity=1, stroke_color=WHITE, stroke_width=1)
        q_box = VGroup(q_bg, q_text).arrange(DOWN, buff=0.1)
        q_text.move_to(q_bg)
        
        formula1 = MathTex("F = ma", font_size=36, color=WHITE)
        
        # Place q_box in B3 and formula in C3
        self.place_at_grid(q_box, 'B3', scale_factor=0.8)
        self.place_at_grid(formula1, 'C3', scale_factor=0.8)

        self.play(FadeIn(q_box), FadeIn(formula1), run_time=1.5)

        # === Animation for Lecture Line 3 ===
        # Highlight lecture line 3
        self.lecture[2].set_color(color_line3)
        self.play(Write(self.lecture[2]), run_time=1)

        # Animation step 3: Rearrange formula
        # Remove old formula and create new one
        self.play(FadeOut(formula1), run_time=0.5)
        
        formula2 = MathTex("a = \\frac{F}{m}", font_size=36, color=WHITE)
        self.place_at_grid(formula2, 'C3', scale_factor=0.8)
        
        self.play(Write(formula2), run_time=1.5)

        # === Animation for Lecture Line 4 ===
        # Highlight lecture line 4
        self.lecture[3].set_color(color_line4)
        self.play(Write(self.lecture[3]), run_time=1)

        # Animation step 4: Substitute numbers
        self.play(FadeOut(formula2), run_time=0.5)
        
        formula3 = MathTex("a = \\frac{10}{2}", font_size=36, color=WHITE)
        self.place_at_grid(formula3, 'C3', scale_factor=0.8)
        
        self.play(Write(formula3), run_time=1.5)

        # === Animation for Lecture Line 5 ===
        # Highlight lecture line 5
        self.lecture[4].set_color(color_line5)
        self.play(Write(self.lecture[4]), run_time=1)

        # Animation step 5: Result
        self.play(FadeOut(formula3), run_time=0.5)
        
        result_eq = MathTex("a = 5 \\, \\text{m/s}^2", font_size=36, color="#00FF00")
        self.place_at_grid(result_eq, 'C3', scale_factor=0.8)
        
        # Flash effect
        self.play(Write(result_eq), run_time=1)
        self.play(Flash(result_eq, color="#00FF00", flash_radius=1.5), run_time=1)

        # Highlight the result
        highlight_box = SurroundingRectangle(result_eq, color="#00FF00", buff=0.2)
        self.place_at_grid(highlight_box, 'C3', scale_factor=0.8)
        self.play(Create(highlight_box), run_time=1)

        self.wait(2)