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
        self.setup_layout("Human Nephron Structure", ["Functional unit of the kidney", "Filtration and reabsorption", "Key components labeled"])
        
        # 1. Nephron Schematic
        # Bowman's Capsule
        capsule = Circle(radius=0.6, color=BLUE, stroke_width=3).move_to([0.5, 1.5, 0])
        
        # Glomerulus
        glom = Circle(radius=0.35, color=BLUE, fill_opacity=0.5, stroke_width=2).move_to([0.5, 1.5, 0])
        
        # Proximal Tubule (Red)
        proximal = ArcBetweenPoints(
            [0.9, 1.5, 0], [1.5, 0.5, 0], angle=-TAU/3, color=RED, stroke_width=4
        )
        
        # Loop of Henle (Green)
        loop = ArcBetweenPoints(
            [1.5, 0.5, 0], [2.5, 0.5, 0], angle=TAU/2, color=GREEN, stroke_width=4
        )
        
        # Distal Tubule (Orange)
        distal = ArcBetweenPoints(
            [2.5, 0.5, 0], [3.0, 1.5, 0], angle=-TAU/3, color=ORANGE, stroke_width=4
        )
        
        # Collecting Duct (Purple)
        duct = Line([3.0, 1.5, 0], [3.0, -1.5, 0], color=BLUE_E, stroke_width=4)
        
        nephron = VGroup(capsule, glom, proximal, loop, distal, duct)
        nephron.shift([1.0, -0.5, 0]) # Center it on the right side
        
        # 2. Labels
        lbl_glom = Text("Glomerulus", font_size=20, color=WHITE).next_to(capsule, LEFT, buff=0.2)
        lbl_prox = Text("Proximal Tubule", font_size=20, color=WHITE).next_to(proximal, RIGHT, buff=0.2)
        lbl_loop = Text("Loop of Henle", font_size=20, color=WHITE).next_to(loop, DOWN, buff=0.2)
        lbl_dist = Text("Distal Tubule", font_size=20, color=WHITE).next_to(distal, RIGHT, buff=0.2)
        lbl_duct = Text("Collecting Duct", font_size=20, color=WHITE).next_to(duct, RIGHT, buff=0.2)
        
        # Leader lines
        ln_glom = Line(lbl_glom.get_right(), capsule.get_left(), color=WHITE, stroke_width=1)
        ln_prox = Line(lbl_prox.get_left(), proximal.get_right(), color=WHITE, stroke_width=1)
        ln_loop = Line(lbl_loop.get_top(), loop.get_bottom(), color=WHITE, stroke_width=1)
        ln_dist = Line(lbl_dist.get_left(), distal.get_right(), color=WHITE, stroke_width=1)
        ln_duct = Line(lbl_duct.get_left(), duct.get_right(), color=WHITE, stroke_width=1)
        
        labels = VGroup(lbl_glom, ln_glom, lbl_prox, ln_prox, lbl_loop, ln_loop, lbl_dist, ln_dist, lbl_duct, ln_duct)
        
        # 3. Flow Arrows
        arr1 = Arrow(capsule.get_bottom(), proximal.get_start(), buff=0.1, color=YELLOW, stroke_width=3)
        arr2 = Arrow(proximal.get_end(), loop.get_start(), buff=0.1, color=YELLOW, stroke_width=3)
        arr3 = Arrow(loop.get_end(), distal.get_start(), buff=0.1, color=YELLOW, stroke_width=3)
        arr4 = Arrow(distal.get_end(), duct.get_start(), buff=0.1, color=YELLOW, stroke_width=3)
        arr5 = Arrow(duct.get_start(), duct.get_end(), buff=0.1, color=YELLOW, stroke_width=3)
        
        arrows = VGroup(arr1, arr2, arr3, arr4, arr5)
        
        # Animations
        self.play(FadeIn(nephron), run_time=1.5)
        self.play(FadeIn(labels), run_time=1.5)
        self.play(FadeIn(arrows), run_time=1.5)
        self.wait(0.5)