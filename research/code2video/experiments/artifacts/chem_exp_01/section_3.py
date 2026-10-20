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
        self.setup_layout("Sec 3: Ion Formation: Charge and Identity", [
            'Losing electrons creates a cation.',
            'Gaining electrons creates an anion.',
            'Protons outnumber electrons in Na+.',
            'Electrons outnumber protons in Cl-.',
            'This imbalance defines the charge.'
        ])

        # Define colors for lecture lines
        color_line1 = "#FFA07A"  # Light Salmon for Cation
        color_line2 = "#87CEFA"  # Light Sky Blue for Anion
        color_line3 = "#FFA07A"  # Light Salmon for Na+
        color_line4 = "#87CEFA"  # Light Sky Blue for Cl-
        color_line5 = "#E0E0E0"  # Light Gray for Imbalance

        # === Animation for Lecture Line 1 ===
        # Split screen vertically. Left: Na, Right: Cl. Counter boxes above.
        
        # Create Na and Cl labels
        na_label = Text("Na", font_size=48, color=WHITE)
        cl_label = Text("Cl", font_size=48, color=WHITE)
        
        # Position Na on left side of right panel (Grid B2-B3 area)
        na_label = self.place_at_grid(na_label, 'B2', scale_factor=1.0)
        
        # Position Cl on right side of right panel (Grid B5-B6 area)
        cl_label = self.place_at_grid(cl_label, 'B5', scale_factor=1.0)
        
        # Create counter boxes
        na_counter_box = Rectangle(width=2, height=1.5, color=GRAY, stroke_width=2)
        cl_counter_box = Rectangle(width=2, height=1.5, color=GRAY, stroke_width=2)
        
        # Position counters above atoms
        na_counter_box = self.place_at_grid(na_counter_box, 'A2', scale_factor=1.0)
        cl_counter_box = self.place_at_grid(cl_counter_box, 'A5', scale_factor=1.0)
        
        # Add elements
        self.play(FadeIn(na_label, shift=UP * 0.5), run_time=1)
        self.play(FadeIn(cl_label, shift=UP * 0.5), run_time=1)
        self.play(FadeIn(na_counter_box, scale=0.8), FadeIn(cl_counter_box, scale=0.8), run_time=1)
        
        # Highlight Lecture Line 1
        self.lecture[0].set_color(color_line1)
        self.wait(1)

        # === Animation for Lecture Line 2 ===
        # Left counter: 11 Protons (red), 10 Electrons (blue). Red '+' flashes.
        
        # Create proton/electron text for Na
        na_protons = Text("11 Protons", font_size=20, color="#FF6B6B")
        na_electrons = Text("10 Electrons", font_size=20, color="#4ECDC4")
        
        # Position inside Na counter box
        na_protons = self.place_at_grid(na_protons, 'A2', scale_factor=0.8)
        na_protons.shift(UP * 0.3)
        
        na_electrons = self.place_at_grid(na_electrons, 'A2', scale_factor=0.8)
        na_electrons.shift(DOWN * 0.3)
        
        # Create '+' sign for cation
        na_plus_sign = Text("+", font_size=60, color="#FF6B6B")
        na_plus_sign = self.place_at_grid(na_plus_sign, 'C2', scale_factor=1.0)
        
        # Animate counter update
        self.play(FadeIn(na_protons, shift=DOWN * 0.2), FadeIn(na_electrons, shift=DOWN * 0.2), run_time=1)
        self.play(FadeIn(na_plus_sign, scale=1.5), run_time=0.5)
        self.play(na_plus_sign.animate.scale(1.0), run_time=0.5)
        self.play(na_plus_sign.animate.scale(1.2), run_time=0.3)
        self.play(na_plus_sign.animate.scale(1.0), run_time=0.3)
        
        # Highlight Lecture Line 2
        self.lecture[1].set_color(color_line2)
        self.wait(1)

        # === Animation for Lecture Line 3 ===
        # Right counter: 17 Protons (red), 18 Electrons (blue). Blue '-' flashes.
        
        # Create proton/electron text for Cl
        cl_protons = Text("17 Protons", font_size=20, color="#FF6B6B")
        cl_electrons = Text("18 Electrons", font_size=20, color="#4ECDC4")
        
        # Position inside Cl counter box
        cl_protons = self.place_at_grid(cl_protons, 'A5', scale_factor=0.8)
        cl_protons.shift(UP * 0.3)
        
        cl_electrons = self.place_at_grid(cl_electrons, 'A5', scale_factor=0.8)
        cl_electrons.shift(DOWN * 0.3)
        
        # Create '-' sign for anion
        cl_minus_sign = Text("-", font_size=60, color="#4ECDC4")
        cl_minus_sign = self.place_at_grid(cl_minus_sign, 'C5', scale_factor=1.0)
        
        # Animate counter update
        self.play(FadeIn(cl_protons, shift=DOWN * 0.2), FadeIn(cl_electrons, shift=DOWN * 0.2), run_time=1)
        self.play(FadeIn(cl_minus_sign, scale=1.5), run_time=0.5)
        self.play(cl_minus_sign.animate.scale(1.0), run_time=0.5)
        self.play(cl_minus_sign.animate.scale(1.2), run_time=0.3)
        self.play(cl_minus_sign.animate.scale(1.0), run_time=0.3)
        
        # Highlight Lecture Line 3
        self.lecture[2].set_color(color_line3)
        self.wait(1)

        # === Animation for Lecture Line 4 ===
        # Balance scale icon appears. Na side: Proton heavier, tips scale. Label 'Positive Charge'.
        
        # Create simple balance scale representation
        # Base
        scale_base = Rectangle(width=1, height=0.2, color=GRAY, stroke_width=2)
        scale_base = self.place_at_grid(scale_base, 'D3', scale_factor=1.0)
        
        # Central pole
        scale_pole = Line(ORIGIN, UP * 1.5, color=GRAY, stroke_width=3)
        scale_pole = self.place_at_grid(scale_pole, 'D3', scale_factor=1.0)
        scale_pole.shift(UP * 0.75)
        
        # Beam (initially horizontal)
        scale_beam = Line(LEFT * 1.5, RIGHT * 1.5, color=GRAY, stroke_width=3)
        scale_beam = self.place_at_grid(scale_beam, 'D3', scale_factor=1.0)
        scale_beam.shift(UP * 1.5)
        
        # Left pan (Na side) - Proton weight
        left_pan = Line(LEFT * 1.5, LEFT * 1.5 + DOWN * 0.5, color=GRAY, stroke_width=2)
        left_pan = self.place_at_grid(left_pan, 'D3', scale_factor=1.0)
        left_pan.shift(UP * 1.5)
        
        left_weight = Circle(radius=0.3, color="#FF6B6B", fill_opacity=0.8)
        left_weight_label = Text("P", font_size=16, color=WHITE)
        left_weight = self.place_at_grid(left_weight, 'D3', scale_factor=1.0)
        left_weight.shift(LEFT * 1.5 + DOWN * 0.8)
        left_weight_label = self.place_at_grid(left_weight_label, 'D3', scale_factor=1.0)
        left_weight_label.shift(LEFT * 1.5 + DOWN * 0.8)
        
        # Right pan (Cl side) - Electron weight
        right_pan = Line(RIGHT * 1.5, RIGHT * 1.5 + DOWN * 0.5, color=GRAY, stroke_width=2)
        right_pan = self.place_at_grid(right_pan, 'D3', scale_factor=1.0)
        right_pan.shift(UP * 1.5)
        
        right_weight = Circle(radius=0.3, color="#4ECDC4", fill_opacity=0.8)
        right_weight_label = Text("e", font_size=16, color=WHITE)
        right_weight = self.place_at_grid(right_weight, 'D3', scale_factor=1.0)
        right_weight.shift(RIGHT * 1.5 + DOWN * 0.8)
        right_weight_label = self.place_at_grid(right_weight_label, 'D3', scale_factor=1.0)
        right_weight_label.shift(RIGHT * 1.5 + DOWN * 0.8)
        
        # Group scale parts
        scale_group = VGroup(scale_base, scale_pole, scale_beam, left_pan, right_pan, 
                            left_weight, left_weight_label, right_weight, right_weight_label)
        
        # Animate scale appearance
        self.play(FadeIn(scale_group, shift=UP * 0.5), run_time=1)
        
        # Tilt scale to left (Na side heavier)
        self.play(
            scale_beam.animate.rotate(-15 * DEGREES, about_point=scale_beam.get_center()),
            left_pan.animate.rotate(-15 * DEGREES, about_point=left_pan.get_start()),
            right_pan.animate.rotate(-15 * DEGREES, about_point=right_pan.get_start()),
            left_weight.animate.shift(DOWN * 0.3 + LEFT * 0.2),
            right_weight.animate.shift(UP * 0.3 + RIGHT * 0.2),
            run_time=1.5
        )
        
        # Add 'Positive Charge' label
        positive_label = Text("Positive Charge", font_size=18, color="#FF6B6B")
        positive_label = self.place_at_grid(positive_label, 'E2', scale_factor=1.0)
        
        self.play(FadeIn(positive_label, shift=UP * 0.2), run_time=0.5)
        
        # Highlight Lecture Line 4
        self.lecture[3].set_color(color_line4)
        self.wait(1)

        # === Animation for Lecture Line 5 ===
        # Cl side: Electron heavier, tips scale opposite. Label 'Negative Charge'. Text 'Na+' and 'Cl-' appear.
        
        # Reset scale to horizontal
        self.play(
            scale_beam.animate.rotate(15 * DEGREES, about_point=scale_beam.get_center()),
            left_pan.animate.rotate(15 * DEGREES, about_point=left_pan.get_start()),
            right_pan.animate.rotate(15 * DEGREES, about_point=right_pan.get_start()),
            left_weight.animate.shift(UP * 0.3 + RIGHT * 0.2),
            right_weight.animate.shift(DOWN * 0.3 + LEFT * 0.2),
            run_time=1.5
        )
        
        # Tilt scale to right (Cl side heavier)
        self.play(
            scale_beam.animate.rotate(15 * DEGREES, about_point=scale_beam.get_center()),
            left_pan.animate.rotate(15 * DEGREES, about_point=left_pan.get_start()),
            right_pan.animate.rotate(15 * DEGREES, about_point=right_pan.get_start()),
            left_weight.animate.shift(UP * 0.3 + RIGHT * 0.2),
            right_weight.animate.shift(DOWN * 0.3 + LEFT * 0.2),
            run_time=1.5
        )
        
        # Add 'Negative Charge' label
        negative_label = Text("Negative Charge", font_size=18, color="#4ECDC4")
        negative_label = self.place_at_grid(negative_label, 'E5', scale_factor=1.0)
        
        self.play(FadeIn(negative_label, shift=UP * 0.2), run_time=0.5)
        
        # Add 'Na+' and 'Cl-' labels below atoms
        na_ion_label = Text("Na+", font_size=36, color="#FF6B6B")
        cl_ion_label = Text("Cl-", font_size=36, color="#4ECDC4")
        
        na_ion_label = self.place_at_grid(na_ion_label, 'D2', scale_factor=1.0)
        cl_ion_label = self.place_at_grid(cl_ion_label, 'D5', scale_factor=1.0)
        
        self.play(FadeIn(na_ion_label, shift=UP * 0.2), FadeIn(cl_ion_label, shift=UP * 0.2), run_time=1)
        
        # Highlight Lecture Line 5
        self.lecture[4].set_color(color_line5)
        self.wait(2)
        
        # Clean up
        self.play(FadeOut(scale_group), FadeOut(positive_label), FadeOut(negative_label), 
                  FadeOut(na_ion_label), FadeOut(cl_ion_label), run_time=1)