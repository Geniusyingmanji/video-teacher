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
            "Sec 2: The Transfer: Sodium Gives, Chlorine Takes",
            [
                'Sodium loses its outer electron.',
                'Chlorine gains that electron.',
                'This is physical electron movement.',
                'Sodium becomes smaller and positive.',
                'Chlorine becomes larger and negative.'
            ]
        )

        # Colors for lecture lines
        color_line1 = "#FFD700"  # Gold
        color_line2 = "#00CED1"  # Dark Turquoise
        color_line3 = "#DA70D6"  # Orchid
        color_line4 = "#FF6347"  # Tomato
        color_line5 = "#1E90FF"  # Dodger Blue

        # Define atoms
        # Na Atom (Left side of grid area)
        na_nucleus = Circle(radius=0.3, color=RED, fill_opacity=1).set_fill(RED, opacity=1)
        na_label = Text("Na", font_size=36, color=WHITE)
        na_shell = Circle(radius=0.8, color=GREY_B, stroke_width=2)
        na_electron = Circle(radius=0.1, color=RED, fill_opacity=1).set_fill(RED, opacity=1)
        
        # Position Na
        na_group = VGroup(na_shell, na_nucleus, na_label)
        na_group.arrange(DOWN, buff=0.1) # This might not work well for circle+text, let's just group them
        # Better approach: Place nucleus at center, label inside or below, shell around
        na_nucleus.move_to(self.grid['C2'])
        na_shell.move_to(self.grid['C2'])
        na_label.next_to(na_nucleus, DOWN, buff=0.1)
        
        # Place electron on shell (right side of shell)
        na_electron.move_to(na_shell.get_right())

        # Cl Atom (Right side of grid area)
        cl_nucleus = Circle(radius=0.3, color=BLUE, fill_opacity=1).set_fill(BLUE, opacity=1)
        cl_label = Text("Cl", font_size=36, color=WHITE)
        cl_shell = Circle(radius=0.8, color=GREY_B, stroke_width=2)
        
        # Position Cl
        cl_nucleus.move_to(self.grid['C5'])
        cl_shell.move_to(self.grid['C5'])
        cl_label.next_to(cl_nucleus, DOWN, buff=0.1)
        
        # The "missing spot" on Cl shell (left side, facing Na)
        cl_missing_spot_pos = cl_shell.get_left()

        # Add atoms to scene
        self.add(na_shell, na_nucleus, na_label, na_electron)
        self.add(cl_shell, cl_nucleus, cl_label)

        # === Animation for Lecture Line 1 ===
        # "Sodium loses its outer electron."
        self.lecture[0].set_color(color_line1)
        
        # Pulse the electron
        pulse_anim = AnimationGroup(
            na_electron.animate.scale(1.5).set_fill(YELLOW, opacity=1),
            run_time=0.5
        )
        self.play(pulse_anim, rate_func=there_and_back)
        self.play(na_electron.animate.scale(1.0).set_fill(RED, opacity=1), run_time=0.2)

        # Detach and move
        # Create a copy for the trail effect or just move the main one
        electron_start_pos = na_electron.get_center().copy()
        
        # Move electron to Cl's missing spot
        self.play(
            na_electron.animate.move_to(cl_missing_spot_pos),
            run_time=1.5
        )
        
        # === Animation for Lecture Line 2 ===
        # "Chlorine gains that electron."
        self.lecture[1].set_color(color_line2)
        
        # Visualize the gain (maybe a flash or just keep it there)
        # The electron is now at Cl's shell position
        # We can add a brief highlight to Cl
        cl_highlight = Circle(radius=0.8, color=color_line2, stroke_width=4, fill_opacity=0)
        cl_highlight.move_to(cl_shell)
        self.play(
            Write(cl_highlight),
            run_time=0.5
        )
        self.play(
            FadeOut(cl_highlight),
            run_time=0.5
        )

        # === Animation for Lecture Line 3 ===
        # "This is physical electron movement."
        self.lecture[2].set_color(color_line3)
        
        # Add a trail effect. Since the electron already moved, we simulate the trail by drawing a line or particles
        # Let's draw a dashed line from start to end to emphasize the path
        path_line = Line(electron_start_pos, cl_missing_spot_pos, color=color_line3, stroke_width=2, stroke_opacity=0.5)
        self.play(
            Create(path_line),
            run_time=1.0
        )
        
        # Add some particles along the path for "physical movement" feel
        particles = VGroup()
        for i in range(5):
            p = Dot(radius=0.05, color=color_line3)
            # Interpolate positions
            pos = interpolate(electron_start_pos, cl_missing_spot_pos, i/4)
            p.move_to(pos)
            particles.add(p)
        
        self.play(
            LaggedStart(*[FadeIn(p) for p in particles], lag_ratio=0.2),
            run_time=1.0
        )
        self.play(
            LaggedStart(*[FadeOut(p) for p in particles], lag_ratio=0.2),
            run_time=0.5
        )
        self.play(
            FadeOut(path_line),
            run_time=0.5
        )

        # === Animation for Lecture Line 4 ===
        # "Sodium becomes smaller and positive."
        self.lecture[3].set_color(color_line4)
        
        # Shrink Na
        na_group_for_scale = VGroup(na_shell, na_nucleus, na_label)
        # Note: na_electron is no longer part of Na, it's now with Cl
        
        plus_sign = Text("+", font_size=48, color=color_line4)
        plus_sign.next_to(na_shell, UP, buff=0.2)
        
        self.play(
            na_shell.animate.scale(0.9),
            na_nucleus.animate.scale(0.9),
            na_label.animate.scale(0.9),
            Write(plus_sign),
            run_time=1.5
        )
        
        # Glow nucleus red
        na_nucleus_glow = Circle(radius=0.3, color=RED, stroke_width=5, fill_opacity=0)
        na_nucleus_glow.move_to(na_nucleus)
        self.play(
            Create(na_nucleus_glow),
            run_time=0.5
        )
        self.play(
            FadeOut(na_nucleus_glow),
            run_time=0.5
        )

        # === Animation for Lecture Line 5 ===
        # "Chlorine becomes larger and negative."
        self.lecture[4].set_color(color_line5)
        
        # Expand Cl
        cl_group_for_scale = VGroup(cl_shell, cl_nucleus, cl_label, na_electron) # na_electron is now the gained electron
        
        minus_sign = Text("-", font_size=48, color=color_line5)
        minus_sign.next_to(cl_shell, UP, buff=0.2)
        
        self.play(
            cl_shell.animate.scale(1.1),
            cl_nucleus.animate.scale(1.1),
            cl_label.animate.scale(1.1),
            na_electron.animate.scale(1.1), # Keep electron relative size consistent or let it stay
            Write(minus_sign),
            run_time=1.5
        )
        
        # Glow nucleus blue
        cl_nucleus_glow = Circle(radius=0.3, color=BLUE, stroke_width=5, fill_opacity=0)
        cl_nucleus_glow.move_to(cl_nucleus)
        self.play(
            Create(cl_nucleus_glow),
            run_time=0.5
        )
        self.play(
            FadeOut(cl_nucleus_glow),
            run_time=0.5
        )
        
        # Wait a bit for the final state
        self.wait(2)