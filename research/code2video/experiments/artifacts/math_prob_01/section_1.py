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
        self.setup_layout(
            "Sec 1: The Balance Scale Analogy", 
            [
                'An equation is a balanced scale.', 
                'Left side holds 2x plus 5.', 
                'Right side holds the number 17.', 
                'Both sides are currently equal.', 
                'Actions must mirror to stay balanced.'
            ]
        )

        # Colors
        GOLD = "#FFD700"
        BLUE = "#4FC3F7"
        YELLOW = "#FFEB3B"
        GREEN = "#4CAF50"
        WHITE = "#FFFFFF"
        GHOST_BLUE = "#4FC3F7"

        # Central position for the scale
        # Using grid C3/D3 area as the center of the right side
        center_pos = self.grid["C4"]
        
        # === Animation for Lecture Line 1 ===
        # "An equation is a balanced scale."
        # Highlight Lecture Line 1
        self.lecture[0].set_color(GOLD)
        self.play(Write(self.lecture[0]), run_time=1)

        # Create Balance Scale
        # Base
        base = Polygon(
            [-1, -2, 0], [1, -2, 0], [0.5, -1.5, 0], [-0.5, -1.5, 0],
            color=GOLD, fill_opacity=0.8, stroke_width=2
        )
        
        # Pillar
        pillar = Line([0, -1.5, 0], [0, 0.5, 0], color=GOLD, stroke_width=4)
        
        # Beam
        beam = Line([-2, 0.5, 0], [2, 0.5, 0], color=GOLD, stroke_width=4)
        
        # Pivot
        pivot = Dot([0, 0.5, 0], color=GOLD, radius=0.1)
        
        # Left Pan Assembly
        left_hanger = Line([-2, 0.5, 0], [-2, -0.5, 0], color=GOLD, stroke_width=2)
        left_pan = Arc(
            angle=PI, 
            radius=0.8, 
            start_angle=PI, 
            color=GOLD, 
            stroke_width=2,
            fill_opacity=0.3,
            fill_color=GOLD
        )
        left_pan.move_to([-2, -0.5, 0])
        left_pan.shift(DOWN * 0.3) # Adjust pan position relative to hanger end
        # Actually, let's make the pan a simple line or arc segment that sits below the hanger
        left_pan = Line([-2.5, -0.8, 0], [-1.5, -0.8, 0], color=GOLD, stroke_width=2)
        
        # Right Pan Assembly
        right_hanger = Line([2, 0.5, 0], [2, -0.5, 0], color=GOLD, stroke_width=2)
        right_pan = Line([1.5, -0.8, 0], [2.5, -0.8, 0], color=GOLD, stroke_width=2)

        scale_group = VGroup(base, pillar, beam, pivot, left_hanger, left_pan, right_hanger, right_pan)
        scale_group.move_to(center_pos)
        
        # Scale down to fit in the grid area nicely
        scale_group.scale(0.8)
        
        self.play(FadeIn(scale_group), run_time=1.5)

        # === Animation for Lecture Line 2 ===
        # "Left side holds 2x plus 5."
        self.lecture[1].set_color(BLUE)
        self.play(Write(self.lecture[1]), run_time=1)

        # Create Blocks
        # Block 'x'
        block_x = Rectangle(width=0.6, height=0.6, color=BLUE, fill_opacity=0.9)
        text_x = Text("x", font_size=20, color=WHITE)
        block_x_group = VGroup(block_x, text_x).arrange(DOWN, buff=0)
        block_x_group[0].set_fill(BLUE, opacity=0.9)
        block_x_group[1].set_color(WHITE)
        
        # Second Block 'x'
        block_x2 = block_x_group.copy()

        # Block '5'
        block_5 = Rectangle(width=0.6, height=0.6, color=YELLOW, fill_opacity=0.9)
        text_5 = Text("5", font_size=20, color=WHITE)
        block_5_group = VGroup(block_5, text_5).arrange(DOWN, buff=0)
        block_5_group[0].set_fill(YELLOW, opacity=0.9)
        block_5_group[1].set_color(WHITE)

        # Position on Left Pan
        # Left pan center is roughly at scale_group left pan position
        # Let's calculate relative to scale_group
        # scale_group is at center_pos. Left pan is at local [-2, -0.8] scaled by 0.8
        # Let's just place them visually near the left pan
        left_pan_pos = scale_group.get_center() + np.array([-1.6, -0.6, 0]) # Approximate
        
        # Arrange blocks on left pan
        left_blocks = VGroup(block_x_group, block_x2, block_5_group).arrange(RIGHT, buff=0.1)
        left_blocks.move_to(left_pan_pos)
        
        # Scale blocks to fit
        left_blocks.scale(0.8)
        
        self.play(FadeIn(left_blocks, shift=UP*0.5), run_time=1)

        # === Animation for Lecture Line 3 ===
        # "Right side holds the number 17."
        self.lecture[2].set_color(GREEN)
        self.play(Write(self.lecture[2]), run_time=1)

        # Block '17'
        block_17 = Rectangle(width=0.8, height=0.8, color=GREEN, fill_opacity=0.9)
        text_17 = Text("17", font_size=20, color=WHITE)
        block_17_group = VGroup(block_17, text_17).arrange(DOWN, buff=0)
        block_17_group[0].set_fill(GREEN, opacity=0.9)
        block_17_group[1].set_color(WHITE)

        # Position on Right Pan
        right_pan_pos = scale_group.get_center() + np.array([1.6, -0.6, 0])
        
        block_17_group.move_to(right_pan_pos)
        block_17_group.scale(0.8)

        self.play(FadeIn(block_17_group, shift=UP*0.5), run_time=1)

        # === Animation for Lecture Line 4 ===
        # "Both sides are currently equal."
        self.lecture[3].set_color(WHITE)
        self.play(Write(self.lecture[3]), run_time=1)

        # Pulse the beam
        self.play(
            scale_group.animate.scale(1.05, about_point=scale_group.get_center()),
            run_time=0.5
        )
        self.play(
            scale_group.animate.scale(0.95, about_point=scale_group.get_center()),
            run_time=0.5
        )
        self.play(
            scale_group.animate.scale(1.0, about_point=scale_group.get_center()),
            run_time=0.5
        )

        # Add Labels
        label_left = Text("2x + 5", font_size=18, color=WHITE)
        label_right = Text("17", font_size=18, color=WHITE)
        
        # Position labels above the pans
        label_left.move_to(left_pan_pos + UP * 1.2)
        label_right.move_to(right_pan_pos + UP * 1.2)
        
        self.play(FadeIn(label_left), FadeIn(label_right), run_time=1)

        # === Animation for Lecture Line 5 ===
        # "Actions must mirror to stay balanced."
        self.lecture[4].set_color(GOLD)
        self.play(Write(self.lecture[4]), run_time=1)

        # Ghosted hand/weight concept
        # Create a generic "weight" block to represent an action
        ghost_weight = Rectangle(width=0.5, height=0.5, color=WHITE, fill_opacity=0.3, stroke_width=1)
        text_ghost = Text("+", font_size=20, color=WHITE)
        ghost_group = VGroup(ghost_weight, text_ghost).arrange(DOWN, buff=0)
        ghost_group.scale(0.8)
        
        # Start position: Above left pan
        ghost_start = left_pan_pos + UP * 2
        ghost_group.move_to(ghost_start)
        
        # Animate adding to left
        self.play(FadeIn(ghost_group), run_time=0.5)
        self.play(ghost_group.animate.move_to(left_pan_pos + UP * 0.5), run_time=0.5)
        
        # "Mirror" action: Instantly show it on the right
        # Create a copy for the right side
        ghost_mirror = ghost_group.copy()
        ghost_mirror.set_fill(GOLD, opacity=0.5) # Distinguish slightly or keep same
        ghost_mirror.set_stroke(GOLD, width=1)
        
        # Move the original ghost to be "added" (visually merging)
        # Then show the mirror appearing on the right
        self.play(
            ghost_group.animate.scale(0.5).set_opacity(0), # Simulate adding
            FadeIn(ghost_mirror, shift=UP*0.5),
            run_time=1
        )
        ghost_mirror.move_to(right_pan_pos + UP * 0.5)
        
        # Add "Golden Rule" text
        golden_rule_text = Text("Golden Rule: Mirror Actions", font_size=16, color=GOLD)
        golden_rule_text.move_to(center_pos + DOWN * 2.5)
        
        self.play(FadeIn(golden_rule_text), run_time=1)

        # Hold for a moment
        self.wait(2)