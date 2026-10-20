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

class Section5Scene(TeachingScene):
    def construct(self):
        self.setup_layout("Sec 5: Real-World Application: The Magnifying Glass", 
                         ['Magnifying glasses focus sunlight to a point.', 
                          'Energy concentrates at the focal point.', 
                          'This high intensity can burn paper.', 
                          'This is how real images form.', 
                          'Understanding focus explains many optical tools.'])
        
        # Define colors for lecture lines
        self.line_colors = [
            "#FFD700",  # Gold for line 1
            "#FF6347",  # Tomato for line 2
            "#8B4513",  # Brown for line 3
            "#4682B4",  # Steel blue for line 4
            "#98FB98"   # Pale green for line 5
        ]
        
        # === Animation for Lecture Line 1 ===
        # Highlight lecture line 1
        self.lecture[0].set_color(self.line_colors[0])
        
        # Draw magnifying glass icon in light gray
        lens_circle = Circle(radius=0.8, color="#D3D3D3", stroke_width=3)
        handle_line = Line(
            np.array([0.8, -0.8, 0]), 
            np.array([1.5, -1.5, 0]), 
            color="#D3D3D3", 
            stroke_width=4
        )
        magnifier = VGroup(lens_circle, handle_line)
        # Place magnifying glass on the left side of the right panel area (around B2-C3)
        self.place_in_area(magnifier, "B1", "C3", scale_factor=1.0)
        self.play(Create(lens_circle), Create(handle_line), run_time=1.5)
        self.wait(0.5)
        
        # Animate parallel yellow rays entering from left, converging to focal point
        focal_point = np.array([self.grid["D4"][0], self.grid["D4"][1], 0])
        ray_start_x = self.grid["B1"][0] - 1.5
        
        rays = VGroup()
        ray_offsets = [-0.5, -0.25, 0, 0.25, 0.5]
        for offset in ray_offsets:
            start_point = np.array([ray_start_x, self.grid["C3"][1] + offset, 0])
            # Rays converge to focal point
            ray = Arrow(
                start_point, 
                focal_point, 
                color="#FFFF00", 
                stroke_width=2,
                buff=0.1
            )
            rays.add(ray)
        
        self.place_in_area(rays, "B1", "D5", scale_factor=1.0)
        self.play(*[Create(ray) for ray in rays], run_time=2.0)
        self.wait(1.0)
        
        # === Animation for Lecture Line 2 ===
        # Highlight lecture line 2
        self.lecture[1].set_color(self.line_colors[1])
        
        # Place a small brown square at the focal point to represent paper
        paper_square = Square(side_length=0.3, color="#8B4513", fill_opacity=1.0, stroke_width=2)
        paper_square.move_to(focal_point)
        self.play(FadeIn(paper_square), run_time=0.8)
        self.wait(0.5)
        
        # === Animation for Lecture Line 3 ===
        # Highlight lecture line 3
        self.lecture[2].set_color(self.line_colors[2])
        
        # Animate a small puff of gray smoke rising from the paper square
        smoke_particles = VGroup()
        for i in range(3):
            particle = Dot(
                radius=0.05 + i * 0.02, 
                color="#A9A9A9", 
                fill_opacity=0.7
            )
            particle.move_to(focal_point + np.array([0, 0.2 + i * 0.15, 0]))
            smoke_particles.add(particle)
        
        smoke_group = VGroup(*smoke_particles)
        self.play(
            *[(particle.animate.move_to(particle.get_center() + np.array([0, 0.3, 0])).set_opacity(0.3)) 
              for particle in smoke_particles], 
            run_time=1.5
        )
        self.wait(1.0)
        
        # === Animation for Lecture Line 4 ===
        # Highlight lecture line 4
        self.lecture[3].set_color(self.line_colors[3])
        
        # Brief pause to emphasize the connection to real images
        self.wait(1.0)
        
        # === Animation for Lecture Line 5 ===
        # Highlight lecture line 5
        self.lecture[4].set_color(self.line_colors[4])
        
        # Fade out the rays and smoke
        self.play(
            *[(ray.animate.set_opacity(0)) for ray in rays],
            *[(particle.animate.set_opacity(0)) for particle in smoke_particles],
            run_time=1.5
        )
        
        # Add label 'Focus = Energy' in white text
        focus_label = Text("Focus = Energy", font_size=24, color=WHITE)
        # Position near the focal point but slightly below
        focus_label.move_to(focal_point + np.array([0, -0.8, 0]))
        self.play(FadeIn(focus_label), run_time=1.0)
        self.wait(2.0)
        
        # Final cleanup - fade out magnifier and paper
        self.play(
            magnifier.animate.set_opacity(0),
            paper_square.animate.set_opacity(0),
            focus_label.animate.set_opacity(0),
            run_time=1.5
        )
        self.wait(1.0)