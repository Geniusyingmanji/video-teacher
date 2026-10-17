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
        self.setup_layout("Sec 3: Bending the Rays: The Mechanism", 
                          ['Parallel rays enter the lens from the left.', 
                           'Top rays bend downward toward the axis.', 
                           'Bottom rays bend upward toward the axis.', 
                           'The central ray goes straight through.', 
                           'Curvature acts like angled mirrors.'])

        # Define colors for lecture lines to match animations
        color_line1 = "#FFFFFF" # White
        color_line2 = "#FFD700" # Gold/Yellow for top ray emphasis
        color_line3 = "#87CEFA" # Light Blue for bottom ray emphasis
        color_line4 = "#FFFFFF" # White for central
        color_line5 = "#FFFF00" # Bright Yellow for curvature

        # --- Setup Geometry ---
        # Lens shape: Ellipse or custom path
        # Let's use an Ellipse for simplicity, scaled to look like a biconvex lens
        lens = Ellipse(width=1.5, height=4.0)
        lens.set_stroke(color=WHITE, width=3)
        lens.set_fill(color=BLUE_E, opacity=0.2)
        
        # Position lens in the center of the right grid area
        # Grid center is roughly around D3/D4
        lens.move_to(self.grid["D3"])

        # Define ray paths
        # The lens is at D3. 
        # Top ray enters from left, hits top-left quadrant of lens.
        # Bottom ray enters from left, hits bottom-left quadrant of lens.
        # Middle ray enters from left, hits center of lens.

        # Coordinates relative to lens center
        lens_center = lens.get_center()
        
        # Entry points on the left side of the lens
        # Top entry: slightly above center, on the left edge
        top_entry = lens_center + np.array([-0.7, 1.0, 0])
        mid_entry = lens_center + np.array([-0.75, 0.0, 0])
        bot_entry = lens_center + np.array([-0.7, -1.0, 0])

        # Exit points on the right side of the lens
        # Top exit: slightly above center, on the right edge
        top_exit = lens_center + np.array([0.7, 1.0, 0])
        mid_exit = lens_center + np.array([0.75, 0.0, 0])
        bot_exit = lens_center + np.array([0.7, -1.0, 0])

        # Focal point (convergence point)
        focal_point = lens_center + np.array([3.0, 0.0, 0])

        # --- Animation Step 1: Parallel rays enter ---
        # Lecture Line 1: "Parallel rays enter the lens from the left."
        
        # Create incoming rays
        # Length of incoming rays
        ray_length = 3.0
        
        top_ray_in = Line(start=top_entry - np.array([ray_length, 0, 0]), end=top_entry, stroke_width=2, color=WHITE)
        mid_ray_in = Line(start=mid_entry - np.array([ray_length, 0, 0]), end=mid_entry, stroke_width=2, color=WHITE)
        bot_ray_in = Line(start=bot_entry - np.array([ray_length, 0, 0]), end=bot_entry, stroke_width=2, color=WHITE)

        self.play(Write(lens), run_time=1)
        self.play(
            Create(top_ray_in),
            Create(mid_ray_in),
            Create(bot_ray_in),
            run_time=1.5
        )
        
        # Highlight Lecture Line 1
        self.lecture[0].set_color(color_line1)
        self.wait(0.5)

        # --- Animation Step 2: Top ray bends ---
        # Lecture Line 2: "Top rays bend downward toward the axis."
        
        # Path for top ray inside lens and exiting
        # Inside: from top_entry to top_exit (straight for now, but actually it bends at surface)
        # To simulate refraction simply:
        # 1. Ray hits surface at top_entry.
        # 2. Ray bends towards normal (downwards).
        # 3. Ray travels through glass to top_exit.
        # 4. Ray bends again at top_exit towards normal (downwards).
        
        # Let's define the segments for the top ray
        # Segment 1: Incoming (already drawn)
        # Segment 2: Inside lens. Let's say it goes from top_entry to a point on the axis? No, it exits at top_exit.
        # In a thin lens approximation, the ray bends at the center plane.
        # Let's use a simplified path:
        # Top ray: top_entry -> focal_point? No, it exits the lens first.
        # Let's draw the path inside the lens as a straight line from top_entry to top_exit? 
        # Actually, for a biconvex lens, the ray bends at the first surface, travels straight, bends at the second.
        # For visual clarity in Manim, we can show:
        # 1. Incoming ray.
        # 2. Ray inside lens: from top_entry to top_exit (slightly angled down).
        # 3. Ray exiting: from top_exit to focal_point.
        
        # Let's refine the "bending" visual.
        # Top ray inside: Line from top_entry to top_exit. 
        # Top ray outside (exit): Line from top_exit to focal_point.
        
        top_ray_in_lens = Line(start=top_entry, end=top_exit, stroke_width=2, color=WHITE)
        top_ray_out = Line(start=top_exit, end=focal_point, stroke_width=2, color=WHITE)

        # Animate the top ray continuing through the lens
        self.play(
            Create(top_ray_in_lens),
            run_time=0.5
        )
        
        # Highlight Lecture Line 2
        self.lecture[1].set_color(color_line2)
        
        # Animate the exit part of the top ray
        self.play(
            Create(top_ray_out),
            run_time=0.5
        )
        self.wait(0.5)

        # --- Animation Step 3: Bottom ray bends ---
        # Lecture Line 3: "Bottom rays bend upward toward the axis."
        
        bot_ray_in_lens = Line(start=bot_entry, end=bot_exit, stroke_width=2, color=WHITE)
        bot_ray_out = Line(start=bot_exit, end=focal_point, stroke_width=2, color=WHITE)

        self.play(
            Create(bot_ray_in_lens),
            run_time=0.5
        )
        
        # Highlight Lecture Line 3
        self.lecture[2].set_color(color_line3)
        
        self.play(
            Create(bot_ray_out),
            run_time=0.5
        )
        self.wait(0.5)

        # --- Animation Step 4: Central ray goes straight ---
        # Lecture Line 4: "The central ray goes straight through."
        
        # The central ray enters at mid_entry and exits at mid_exit.
        # Since it's on the axis, it doesn't bend.
        mid_ray_in_lens = Line(start=mid_entry, end=mid_exit, stroke_width=2, color=WHITE)
        mid_ray_out = Line(start=mid_exit, end=focal_point, stroke_width=2, color=WHITE)
        
        # Note: mid_ray_out is collinear with mid_ray_in and mid_ray_in_lens.
        # We can just draw a single line from mid_entry to focal_point to show it goes straight.
        # But we already have mid_ray_in. Let's complete it.
        
        self.play(
            Create(mid_ray_in_lens),
            run_time=0.5
        )
        
        # Highlight Lecture Line 4
        self.lecture[3].set_color(color_line4)
        
        self.play(
            Create(mid_ray_out),
            run_time=0.5
        )
        self.wait(0.5)

        # --- Animation Step 5: Curvature acts like angled mirrors ---
        # Lecture Line 5: "Curvature acts like angled mirrors."
        
        # Flash the lens outline in bright yellow
        lens_flash = lens.copy()
        lens_flash.set_stroke(color="#FFFF00", width=5)
        
        self.play(
            Transform(lens, lens_flash),
            run_time=1.0
        )
        
        # Highlight Lecture Line 5
        self.lecture[4].set_color(color_line5)
        
        self.wait(1)
        
        # Optional: Fade out or keep static
        self.play(
            FadeOut(lens),
            FadeOut(top_ray_in), FadeOut(top_ray_in_lens), FadeOut(top_ray_out),
            FadeOut(mid_ray_in), FadeOut(mid_ray_in_lens), FadeOut(mid_ray_out),
            FadeOut(bot_ray_in), FadeOut(bot_ray_in_lens), FadeOut(bot_ray_out),
            run_time=1
        )