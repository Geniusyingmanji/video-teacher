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
        self.setup_layout("Sec 4: Convergence at the Focal Point", 
                          ['All refracted rays meet at one point.', 
                           'This point is called the Focal Point.', 
                           'It lies on the principal axis.', 
                           'Distance from lens is the Focal Length.', 
                           'We label this distance as f.'])
        
        # Define colors for lecture lines
        colors = [
            "#FFD700",  # Gold
            "#FF6347",  # Tomato
            "#40E0D0",  # Turquoise
            "#9370DB",  # Medium Purple
            "#7FFF00"   # Chartreuse
        ]
        
        # === Animation for Lecture Line 1 ===
        # "All refracted rays meet at one point."
        # Animation step 1: Continue the ray paths from Section 3. 
        # Show the top, middle, and bottom rays intersecting at a single point on the right side of the lens.
        
        # Change color of Lecture Line 1
        self.lecture[0].set_color(colors[0])
        self.play(Write(self.lecture[0]), run_time=1)
        
        # Create Lens (simple ellipse representation)
        # Position lens around B3-C3 area
        lens = Ellipse(width=1.0, height=3.0, color=WHITE, stroke_width=2)
        lens = self.place_in_area(lens, 'B3', 'D3', scale_factor=1.0)
        
        # Create Principal Axis
        axis = Line(start=np.array([-1, 0, 0]), end=np.array([6, 0, 0]), color=GRAY, stroke_width=1)
        axis = self.place_in_area(axis, 'C1', 'C6', scale_factor=1.0)
        
        self.play(Create(lens), Create(axis), run_time=1.5)
        
        # Define Focal Point position (around E4 or F4, let's say E4)
        focal_point_pos = self.grid['E4']
        
        # Define Ray Start Points (Left side)
        ray_top_start = np.array([0.5, 1.5, 0])   # Top left
        ray_mid_start = np.array([0.5, 0, 0])     # Middle left (on axis)
        ray_bot_start = np.array([0.5, -1.5, 0])  # Bottom left
        
        # Define Ray End Points (At Focal Point)
        ray_top_end = focal_point_pos
        ray_mid_end = focal_point_pos
        ray_bot_end = focal_point_pos
        
        # Create Rays
        ray_top = Line(ray_top_start, ray_top_end, color="#FFD700", stroke_width=2)
        ray_mid = Line(ray_mid_start, ray_mid_end, color="#FFD700", stroke_width=2)
        ray_bot = Line(ray_bot_start, ray_bot_end, color="#FFD700", stroke_width=2)
        
        # Animate rays converging
        self.play(Create(ray_top), Create(ray_mid), Create(ray_bot), run_time=2)

        # === Animation for Lecture Line 2 ===
        # "This point is called the Focal Point."
        # Animation step 2: Place a bright red dot (#FF0000) at the intersection point. Label it 'F' in white text.
        
        # Change color of Lecture Line 2
        self.lecture[1].set_color(colors[1])
        self.play(Write(self.lecture[1]), run_time=1)
        
        # Create Focal Point Dot
        focal_dot = Dot(focal_point_pos, color="#FF0000", radius=0.1)
        
        # Create Label 'F'
        label_F = Text("F", font_size=36, color=WHITE)
        label_F = self.place_at_grid(label_F, 'E4', scale_factor=1.0)
        label_F.next_to(focal_dot, DR, buff=0.2)
        
        self.play(Create(focal_dot), Write(label_F), run_time=1)

        # === Animation for Lecture Line 3 ===
        # "It lies on the principal axis."
        # No specific new visual element requested in description for this line, 
        # but we can highlight the axis briefly or just wait.
        # Since description doesn't specify a new animation for this line, 
        # we just change the color of the lecture line.
        
        # Change color of Lecture Line 3
        self.lecture[2].set_color(colors[2])
        self.play(Write(self.lecture[2]), run_time=1)
        
        # Briefly highlight the axis to emphasize it
        self.play(axis.animate.set_color(WHITE).set_stroke(width=3), run_time=0.5)
        self.play(axis.animate.set_color(GRAY).set_stroke(width=1), run_time=0.5)

        # === Animation for Lecture Line 4 ===
        # "Distance from lens is the Focal Length."
        # Animation step 3: Draw a double-headed arrow from the center of the lens to point F. Color the arrow cyan (#00FFFF).
        
        # Change color of Lecture Line 4
        self.lecture[3].set_color(colors[3])
        self.play(Write(self.lecture[3]), run_time=1)
        
        # Get center of lens
        lens_center = lens.get_center()
        
        # Create Double-Headed Arrow
        # Start slightly above the axis to avoid overlapping the axis line itself
        arrow_start = lens_center + np.array([0, 0.3, 0])
        arrow_end = focal_point_pos + np.array([0, 0.3, 0])
        
        focal_length_arrow = DoubleArrow(arrow_start, arrow_end, color="#00FFFF", stroke_width=3)
        
        self.play(Create(focal_length_arrow), run_time=1.5)

        # === Animation for Lecture Line 5 ===
        # "We label this distance as f."
        # Animation step 4: Label the arrow with the letter 'f' in large, bold white font.
        # Animation step 5: Flash the entire path of the rays in green (#00FF00) briefly to show the complete convergence process.
        
        # Change color of Lecture Line 5
        self.lecture[4].set_color(colors[4])
        self.play(Write(self.lecture[4]), run_time=1)
        
        # Create Label 'f'
        label_f = Text("f", font_size=40, color=WHITE, weight=BOLD)
        # Position 'f' above the middle of the arrow
        arrow_midpoint = (arrow_start + arrow_end) / 2
        label_f.move_to(arrow_midpoint + np.array([0, 0.3, 0]))
        
        self.play(Write(label_f), run_time=0.8)
        
        # Flash the rays in green
        green_rays = VGroup(
            ray_top.copy().set_color("#00FF00"),
            ray_mid.copy().set_color("#00FF00"),
            ray_bot.copy().set_color("#00FF00")
        )
        
        self.play(FadeIn(green_rays), run_time=0.5)
        self.wait(0.5)
        self.play(FadeOut(green_rays), run_time=0.5)
        
        self.wait(1)