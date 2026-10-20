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
        self.setup_layout("Sec 4: Interpreting the Result", ['Place pH three on the scale.', 'This value indicates an acidic solution.', 'It is similar to lemon juice.'])
        
        # Create the pH scale bar
        # The scale will span horizontally across the right side
        # We'll place it roughly in the middle of the grid area
        scale_bar = Rectangle(
            width=5, height=0.5,
            stroke_color=WHITE,
            stroke_width=2,
            fill_color=BLUE,
            fill_opacity=0.3
        )
        self.place_in_area(scale_bar, 'B2', 'B6', scale_factor=1.0)
        
        # Add tick marks and numbers for pH scale (0 to 14)
        tick_marks = VGroup()
        numbers = VGroup()
        for i in range(15):
            # Position ticks along the scale bar
            x_pos = self.grid['B2'][0] - 2.5 + i * (5 / 14)
            y_pos = self.grid['B2'][1]
            
            tick = Line(
                start=np.array([x_pos, y_pos - 0.3, 0]),
                end=np.array([x_pos, y_pos + 0.3, 0]),
                color=WHITE,
                stroke_width=1
            )
            tick_marks.add(tick)
            
            num = Text(str(i), font_size=14, color=WHITE)
            num.move_to(np.array([x_pos, y_pos - 0.5, 0]))
            numbers.add(num)
        
        self.add(scale_bar, tick_marks, numbers)
        
        # === Animation for Lecture Line 1 ===
        # Change lecture line 1 color
        self.lecture[0].set_color("#FF0000")
        
        # Marker drops onto the '3' position
        # pH 3 position: x = grid['B2'][0] - 2.5 + 3 * (5/14)
        pH3_x = self.grid['B2'][0] - 2.5 + 3 * (5 / 14)
        pH3_y = self.grid['B2'][1]
        
        marker = Triangle(
            fill_color="#FF0000",
            fill_opacity=1.0,
            stroke_color="#FF0000",
            stroke_width=1
        )
        marker.scale_to_fit_height(0.4)
        marker.rotate(PI)  # Point downward
        marker.move_to(np.array([pH3_x, pH3_y + 0.5, 0]))
        
        self.play(
            FadeIn(marker, shift=DOWN * 0.5),
            run_time=1.0
        )
        
        self.wait(0.5)
        
        # === Animation for Lecture Line 2 ===
        # Change lecture line 2 color
        self.lecture[1].set_color("#FF0000")
        
        # Highlight area from 0 to 7 in red
        acidic_region = Rectangle(
            width=5 * (7/14),  # From 0 to 7 is half the scale
            height=0.5,
            stroke_color="#FF0000",
            stroke_width=2,
            fill_color="#FF0000",
            fill_opacity=0.4
        )
        # Position acidic region from pH 0 to pH 7
        acidic_x_start = self.grid['B2'][0] - 2.5
        acidic_x_end = self.grid['B2'][0] - 2.5 + 5 * (7/14)
        acidic_center_x = (acidic_x_start + acidic_x_end) / 2
        acidic_region.move_to(np.array([acidic_center_x, self.grid['B2'][1], 0]))
        
        # Text 'ACIDIC' flashes in red above the scale
        acidic_text = Text("ACIDIC", font_size=24, color="#FF0000", weight=BOLD)
        self.place_in_area(acidic_text, 'A2', 'A6', scale_factor=1.0)
        acidic_text.move_to(np.array([self.grid['B2'][0], self.grid['B2'][1] + 0.8, 0]))
        
        self.play(
            FadeIn(acidic_region),
            Write(acidic_text),
            run_time=1.5
        )
        
        # Flash effect
        self.play(
            acidic_text.animate.set_opacity(0.5),
            run_time=0.2
        )
        self.play(
            acidic_text.animate.set_opacity(1.0),
            run_time=0.2
        )
        
        self.wait(0.5)
        
        # === Animation for Lecture Line 3 ===
        # Change lecture line 3 color
        self.lecture[2].set_color("#FFFF00")
        
        # Lemon icon appears next to the '3' marker
        # We'll use a simple circle with yellow fill to represent lemon
        lemon_icon = Circle(
            radius=0.25,
            fill_color="#FFFF00",
            fill_opacity=1.0,
            stroke_color="#FFCC00",
            stroke_width=2
        )
        lemon_icon.move_to(np.array([pH3_x + 0.5, pH3_y + 0.5, 0]))
        
        # Text 'Lemon Juice ~ pH 2' appears in yellow
        lemon_text = Text("Lemon Juice ~ pH 2", font_size=18, color="#FFFF00")
        self.place_in_area(lemon_text, 'C2', 'C6', scale_factor=1.0)
        lemon_text.move_to(np.array([pH3_x + 1.0, pH3_y + 0.5, 0]))
        
        self.play(
            FadeIn(lemon_icon),
            Write(lemon_text),
            run_time=1.0
        )
        
        self.wait(2)
        
        # Cleanup
        self.play(
            FadeOut(marker),
            FadeOut(acidic_region),
            FadeOut(acidic_text),
            FadeOut(lemon_icon),
            FadeOut(lemon_text),
            run_time=1.0
        )