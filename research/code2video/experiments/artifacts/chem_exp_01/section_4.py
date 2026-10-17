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
        self.setup_layout("Sec 4: Electrostatic Attraction: The Ionic Bond", 
                         ['Opposite charges attract each other.', 
                          'This force is electrostatic attraction.', 
                          'It is not electron sharing.', 
                          'Ions pull into a stable bond.', 
                          'This connection is the ionic bond.'])
        
        # === Animation for Lecture Line 1 ===
        # Animation step 1: The Na+ (red glow) and Cl- (blue glow) ions start at opposite edges of the screen.
        
        # Create Na+ ion (red glow)
        na_ion = Circle(radius=0.4, color=RED, fill_opacity=0.3, stroke_width=2)
        na_label = Text("Na+", font_size=20, color=RED)
        na_group = VGroup(na_ion, na_label).arrange(DOWN, buff=0.1)
        self.place_at_grid(na_group, 'B1', scale_factor=1.0)
        
        # Create Cl- ion (blue glow)
        cl_ion = Circle(radius=0.4, color=BLUE, fill_opacity=0.3, stroke_width=2)
        cl_label = Text("Cl-", font_size=20, color=BLUE)
        cl_group = VGroup(cl_ion, cl_label).arrange(DOWN, buff=0.1)
        self.place_at_grid(cl_group, 'B5', scale_factor=1.0)
        
        # Animate lecture line 1 color change
        self.lecture[0].set_color(RED)
        self.play(Write(na_group), Write(cl_group), run_time=1.5)
        
        # === Animation for Lecture Line 2 ===
        # Animation step 2: The ions accelerate towards each other. Glowing yellow (#FFFF00) lines appear between them, representing force fields.
        
        # Create force field lines (yellow glow)
        force_lines = VGroup()
        for i in range(3):
            line = Line(
                start=na_group.get_center() + np.array([0.2, i*0.1 - 0.1, 0]),
                end=cl_group.get_center() + np.array([-0.2, i*0.1 - 0.1, 0]),
                color=YELLOW,
                stroke_width=2,
                stroke_opacity=0.8
            )
            force_lines.add(line)
        
        # Animate lecture line 2 color change
        self.lecture[1].set_color(YELLOW)
        
        # Move ions towards each other
        target_pos_na = self.grid['B3']
        target_pos_cl = self.grid['B4']
        
        self.play(
            na_group.animate.move_to(target_pos_na),
            cl_group.animate.move_to(target_pos_cl),
            Create(force_lines),
            run_time=2.0
        )
        
        # === Animation for Lecture Line 3 ===
        # Animation step 3: The ions collide softly and lock together. The yellow lines solidify into a rigid, glowing bridge between the nuclei.
        
        # Create rigid bridge (solidified yellow lines)
        bridge = Line(
            start=na_group.get_center(),
            end=cl_group.get_center(),
            color=YELLOW,
            stroke_width=4,
            stroke_opacity=1.0
        )
        
        # Animate lecture line 3 color change
        self.lecture[2].set_color(GREEN)
        
        # Transition from force lines to rigid bridge
        self.play(
            force_lines.animate.set_stroke(width=4, opacity=1.0),
            run_time=1.0
        )
        self.play(
            ReplacementTransform(force_lines, bridge),
            run_time=1.0
        )
        
        # === Animation for Lecture Line 4 ===
        # Animation step 4: Text 'Not Shared Electrons' appears with a red cross mark. Text 'Electrostatic Pull' appears with a green check mark.
        
        # Create "Not Shared Electrons" text with red cross
        not_shared_text = Text("Not Shared Electrons", font_size=18, color=RED)
        red_cross = Text("✗", font_size=24, color=RED)
        not_shared_group = VGroup(not_shared_text, red_cross).arrange(RIGHT, buff=0.2)
        self.place_at_grid(not_shared_group, 'D2', scale_factor=0.8)
        
        # Create "Electrostatic Pull" text with green check
        electrostatic_text = Text("Electrostatic Pull", font_size=18, color=GREEN)
        green_check = Text("✓", font_size=24, color=GREEN)
        electrostatic_group = VGroup(electrostatic_text, green_check).arrange(RIGHT, buff=0.2)
        self.place_at_grid(electrostatic_group, 'D4', scale_factor=0.8)
        
        # Animate lecture line 4 color change
        self.lecture[3].set_color(GREEN)
        
        self.play(
            Write(not_shared_group),
            Write(electrostatic_group),
            run_time=1.5
        )
        
        # === Animation for Lecture Line 5 ===
        # Animation step 5: A label 'Ionic Bond' fades in above the connected ions, with an arrow pointing to the glowing bridge.
        
        # Create "Ionic Bond" label
        ionic_bond_label = Text("Ionic Bond", font_size=20, color=WHITE)
        self.place_at_grid(ionic_bond_label, 'C3', scale_factor=1.0)
        
        # Create arrow pointing to the bridge
        arrow = Arrow(
            start=ionic_bond_label.get_bottom(),
            end=bridge.get_center(),
            color=WHITE,
            buff=0.1
        )
        
        # Animate lecture line 5 color change
        self.lecture[4].set_color(WHITE)
        
        self.play(
            FadeIn(ionic_bond_label),
            GrowArrow(arrow),
            run_time=1.5
        )
        
        # Hold final state
        self.wait(2)