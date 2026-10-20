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
        self.setup_layout("Sec 4: The Conclusion: A Straight Line is 180°", ['The angles form a straight line.', 'A straight line is 180 degrees.', 'So, the sum is 180 degrees.'])
        
        # Define colors for lecture lines
        color1 = "#FF9999"  # Light red/pink
        color2 = "#99CCFF"  # Light blue
        color3 = "#FFFF00"  # Yellow

        # Initial state: Three angle sectors representing the angles
        # Position them in the grid, roughly in the middle-right area
        # Let's place them around C2, C3, C4 or similar to form a line
        # Actually, let's create three small sectors that will merge.
        # We'll use Sector or Arc for simplicity, or just colored rectangles to represent the angles.
        # Let's use small rectangles to represent the "angle sectors" for simplicity and clarity.
        
        # Create three small colored rectangles (representing the angles)
        # They should be adjacent to form a line eventually.
        # Let's place them initially slightly separated or just as distinct parts.
        
        rect_width = 0.8
        rect_height = 0.4
        
        angle1 = Rectangle(width=rect_width, height=rect_height, color=color1, fill_opacity=1, stroke_width=0)
        angle2 = Rectangle(width=rect_width, height=rect_height, color=color2, fill_opacity=1, stroke_width=0)
        angle3 = Rectangle(width=rect_width, height=rect_height, color=color3, fill_opacity=1, stroke_width=0)
        
        # Position them in a row, centered around the middle of the right grid
        # Let's center them around C3 (which is x=3.5, y=0.2)
        # Total width of three rects = 2.4. So they span from x=2.3 to x=4.7
        # Let's align their centers:
        # angle1 center: x = 3.5 - 0.8 = 2.7, y = 0.2
        # angle2 center: x = 3.5, y = 0.2
        # angle3 center: x = 3.5 + 0.8 = 4.3, y = 0.2
        
        angle1.move_to(np.array([2.7, 0.2, 0]))
        angle2.move_to(np.array([3.5, 0.2, 0]))
        angle3.move_to(np.array([4.3, 0.2, 0]))
        
        self.add(angle1, angle2, angle3)
        
        # === Animation for Lecture Line 1 ===
        # "The angles form a straight line."
        # Change color of lecture line 1
        self.lecture[0].set_color(color1)
        
        # Animation: The three individual angle sectors merge into a single glowing rectangular bar
        # Merge them into one bar
        merged_bar = Rectangle(width=rect_width * 3, height=rect_height, color=WHITE, fill_opacity=0.8, stroke_width=0)
        merged_bar.move_to(np.array([3.5, 0.2, 0]))
        
        # Animate the merging: Fade out individual rects, fade in merged bar
        self.play(FadeOut(angle1), FadeOut(angle2), FadeOut(angle3), run_time=0.5)
        self.play(FadeIn(merged_bar), run_time=0.5)
        
        # Add a glow effect by creating a slightly larger, semi-transparent rectangle behind it
        glow = Rectangle(width=rect_width * 3 + 0.2, height=rect_height + 0.2, color=WHITE, fill_opacity=0.3, stroke_width=0)
        glow.move_to(merged_bar.get_center())
        self.add(glow)
        
        self.wait(1)
        
        # === Animation for Lecture Line 2 ===
        # "A straight line is 180 degrees."
        # Change color of lecture line 2
        self.lecture[1].set_color(color2)
        
        # Animation: The bar pulses with a bright white light
        # Pulse effect: scale up and down slightly, or change opacity
        self.play(
            merged_bar.animate.set_fill(opacity=1.0).scale(1.05),
            glow.animate.scale(1.1).set_fill(opacity=0.5),
            run_time=0.5
        )
        self.play(
            merged_bar.animate.set_fill(opacity=0.8).scale(1.0),
            glow.animate.scale(1.0).set_fill(opacity=0.3),
            run_time=0.5
        )
        
        self.wait(1)
        
        # === Animation for Lecture Line 3 ===
        # "So, the sum is 180 degrees."
        # Change color of lecture line 3
        self.lecture[2].set_color(color3)
        
        # Animation: Text 'Sum = 180°' appears below the bar in bold yellow (#FFFF00)
        sum_text = Text("Sum = 180°", font_size=28, color="#FFFF00", weight=BOLD)
        # Position it below the bar. Bar is at y=0.2, height 0.4, so bottom is y=0.0
        # Place text at y=-0.5, x=3.5
        sum_text.move_to(np.array([3.5, -0.5, 0]))
        
        self.play(FadeIn(sum_text), run_time=0.5)
        
        self.wait(2)
        
        # Clean up or leave as is