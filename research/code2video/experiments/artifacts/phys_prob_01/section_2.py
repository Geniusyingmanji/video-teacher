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
        self.setup_layout(
            "Sec 2: Introducing Newton's Second Law",
            [
                "Formula: F equals m times a.",
                "Acceleration depends on force.",
                "More force means faster speed.",
                "More mass means slower speed.",
                "Solve for acceleration a."
            ]
        )

        # === Animation for Lecture Line 1 ===
        # "Formula: F equals m times a."
        # Animation step 1: The formula 'F = m * a' appears in the center in large white text (#FFFFFF).
        
        # Change lecture line 1 color to light blue
        self.lecture[0].set_color("#ADD8E6")
        
        # Create formula in center of grid (around C3-C4)
        formula = Text("F = m * a", font_size=48, color="#FFFFFF")
        self.place_in_area(formula, 'B3', 'D4', scale_factor=1.0)
        
        self.play(Write(formula), run_time=1.5)
        self.wait(0.5)

        # === Animation for Lecture Line 2 ===
        # "Acceleration depends on force."
        # Animation step 2: A small gray block moves slowly to the right. A small red arrow pushes it. Text 'Small F, Low a' appears.
        
        # Change lecture line 2 color to light green
        self.lecture[1].set_color("#90EE90")
        
        # Create small gray block
        block = Square(side_length=0.5, color="#A9A9A9", fill_opacity=1.0)
        self.place_at_grid(block, 'C3', scale_factor=1.0)
        
        # Create small red arrow
        arrow = Arrow(
            start=block.get_left() + DOWN * 0.1,
            end=block.get_right() + RIGHT * 0.8,
            buff=0.1,
            color="#FF6347",
            stroke_width=3
        )
        
        # Create text label
        label1 = Text("Small F, Low a", font_size=20, color="#FF6347")
        self.place_at_grid(label1, 'D3', scale_factor=0.8)
        
        # Animate block moving right slowly
        block_start = block.get_center()
        block_end = block_start + RIGHT * 1.5
        
        self.play(
            block.animate.move_to(block_end),
            Create(arrow),
            FadeIn(label1),
            run_time=2.0
        )
        self.wait(0.5)

        # === Animation for Lecture Line 3 ===
        # "More force means faster speed."
        # Animation step 3: The red arrow grows larger and brighter. The block moves faster. Text 'Large F, High a' replaces the previous text.
        
        # Change lecture line 3 color to light yellow
        self.lecture[2].set_color("#FFFF99")
        
        # Grow the arrow (make it larger and brighter)
        large_arrow = Arrow(
            start=block.get_left() + DOWN * 0.1,
            end=block.get_right() + RIGHT * 1.5,
            buff=0.1,
            color="#FF0000",
            stroke_width=5
        )
        
        # Create new text label
        label2 = Text("Large F, High a", font_size=20, color="#FF0000")
        self.place_at_grid(label2, 'D3', scale_factor=0.8)
        
        # Animate: replace old arrow with larger one, block moves faster
        block_start2 = block.get_center()
        block_end2 = block_start2 + RIGHT * 2.5
        
        self.play(
            ReplacementTransform(arrow, large_arrow),
            block.animate.move_to(block_end2),
            FadeOut(label1),
            FadeIn(label2),
            run_time=1.5
        )
        self.wait(0.5)

        # === Animation for Lecture Line 4 ===
        # "More mass means slower speed."
        # Animation step 4: The block becomes larger (heavier). The same large red arrow is applied, but the block moves slower. Text 'Large m, Low a' appears.
        
        # Change lecture line 4 color to light orange
        self.lecture[3].set_color("#FFA07A")
        
        # Make block larger (heavier)
        large_block = Square(side_length=0.8, color="#808080", fill_opacity=1.0)
        large_block.move_to(block.get_center())
        
        # Create new text label
        label3 = Text("Large m, Low a", font_size=20, color="#FFA07A")
        self.place_at_grid(label3, 'D3', scale_factor=0.8)
        
        # Animate: replace small block with large block, block moves slower
        block_start3 = large_block.get_center()
        block_end3 = block_start3 + RIGHT * 1.0  # Slower movement
        
        self.play(
            ReplacementTransform(block, large_block),
            large_block.animate.move_to(block_end3),
            FadeOut(label2),
            FadeIn(label3),
            run_time=2.0
        )
        self.wait(0.5)

        # === Animation for Lecture Line 5 ===
        # "Solve for acceleration a."
        # Animation step 5: The variable 'a' in the central formula 'F = m * a' turns yellow (#FFFF00) and scales up slightly to highlight it as the target.
        
        # Change lecture line 5 color to light purple
        self.lecture[4].set_color("#DA70D6")
        
        # Create highlighted formula with 'a' in yellow
        formula_highlighted = VGroup(
            Text("F = m * ", font_size=48, color="#FFFFFF"),
            Text("a", font_size=56, color="#FFFF00")
        ).arrange(RIGHT, buff=0.05)
        
        # Position the highlighted formula in the same area as the original
        formula_highlighted.move_to(formula.get_center())
        
        # Animate: replace original formula with highlighted version
        self.play(
            ReplacementTransform(formula, formula_highlighted),
            run_time=1.5
        )
        self.wait(1.0)

        # Final cleanup: fade out all animation elements except lecture and title
        all_elements = VGroup(
            formula_highlighted,
            large_block,
            large_arrow,
            label3
        )
        self.play(FadeOut(all_elements), run_time=1.0)
        self.wait(0.5)