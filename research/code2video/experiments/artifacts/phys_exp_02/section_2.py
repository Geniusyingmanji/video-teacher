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
        self.setup_layout("Sec 2: The Shape of the Convex Lens", ['A convex lens is thick in the middle.', 'It is thin at the edges.', 'Light travels slower in glass.', 'Center light takes a longer path.', 'This path difference causes bending.'])
        
        # === Animation for Lecture Line 1 ===
        # Draw a biconvex lens shape using two curved lines meeting at points, filled with semi-transparent light blue (#ADD8E6).
        # Position: Center of the right side grid area (C3-C4)
        
        # Create the lens shape using an Ellipse or custom path
        # A biconvex lens can be approximated by two arcs
        lens_left = ArcBetweenPoints(
            np.array([1.5, 1.5, 0]),
            np.array([1.5, -1.5, 0]),
            angle=-PI/2
        )
        lens_right = ArcBetweenPoints(
            np.array([1.5, 1.5, 0]),
            np.array([1.5, -1.5, 0]),
            angle=PI/2
        )
        
        # Create a filled lens shape
        lens_shape = Polygon(
            *lens_left.get_points(),
            *lens_right.get_points()[::-1]
        )
        lens_shape.fill_color = "#ADD8E6"
        lens_shape.fill_opacity = 0.3
        lens_shape.set_stroke(color="#ADD8E6", width=2)
        
        # Position the lens in the center-right area
        self.place_in_area(lens_shape, 'B2', 'D5', scale_factor=1.0)
        self.add(lens_shape)
        
        # Change color of lecture line 1
        self.lecture[0].set_color("#ADD8E6")
        self.wait(1)
        
        # === Animation for Lecture Line 2 ===
        # Draw a horizontal red line (#FF4444) through the center (optical axis) and a vertical green line (#44FF44) through the middle (center of lens).
        
        # Get the center of the lens
        lens_center = lens_shape.get_center()
        
        # Horizontal line (optical axis) - red
        optical_axis = Line(
            lens_center + LEFT * 2,
            lens_center + RIGHT * 2,
            color="#FF4444",
            stroke_width=2
        )
        
        # Vertical line through center - green
        center_line = Line(
            lens_center + DOWN * 2,
            lens_center + UP * 2,
            color="#44FF44",
            stroke_width=2
        )
        
        self.add(optical_axis)
        self.add(center_line)
        
        # Change color of lecture line 2
        self.lecture[1].set_color("#FF4444")
        self.wait(1)
        
        # === Animation for Lecture Line 3 ===
        # Highlight the central vertical section of the lens in bright orange (#FFA500) to show thickness. Label it 'Thick Center'.
        
        # Create a highlight for the center thickness
        # The center is where the lens is thickest
        center_highlight = Rectangle(
            width=0.3,
            height=3,
            color="#FFA500",
            fill_color="#FFA500",
            fill_opacity=0.5,
            stroke_width=2
        )
        center_highlight.move_to(lens_center)
        self.add(center_highlight)
        
        # Add label 'Thick Center'
        thick_label = Text("Thick Center", font_size=18, color="#FFA500")
        thick_label.next_to(center_highlight, UP, buff=0.2)
        self.add(thick_label)
        
        # Change color of lecture line 3
        self.lecture[2].set_color("#FFA500")
        self.wait(1)
        
        # === Animation for Lecture Line 4 ===
        # Highlight the top and bottom edges of the lens in bright purple (#9400D3). Label them 'Thin Edges'.
        
        # Top edge highlight
        top_edge = Line(
            lens_center + LEFT * 0.5 + UP * 1.5,
            lens_center + RIGHT * 0.5 + UP * 1.5,
            color="#9400D3",
            stroke_width=3
        )
        
        # Bottom edge highlight
        bottom_edge = Line(
            lens_center + LEFT * 0.5 + DOWN * 1.5,
            lens_center + RIGHT * 0.5 + DOWN * 1.5,
            color="#9400D3",
            stroke_width=3
        )
        
        self.add(top_edge)
        self.add(bottom_edge)
        
        # Add label 'Thin Edges'
        thin_label = Text("Thin Edges", font_size=18, color="#9400D3")
        thin_label.next_to(top_edge, RIGHT, buff=0.3)
        self.add(thin_label)
        
        # Change color of lecture line 4
        self.lecture[3].set_color("#9400D3")
        self.wait(1)
        
        # === Animation for Lecture Line 5 ===
        # Animate a white dot moving from the center of the lens to the edge, with a trail that gets shorter, illustrating the path length difference.
        
        # Create a dot
        dot = Dot(radius=0.1, color=WHITE)
        dot.move_to(lens_center)
        self.add(dot)
        
        # Create a trail that shows the path
        # The path from center to edge is shorter than through the center
        trail_points = []
        num_points = 20
        for i in range(num_points):
            t = i / (num_points - 1)
            # Move from center to the right edge
            pos = lens_center + RIGHT * t * 1.5
            trail_points.append(pos)
        
        # Create a trail line
        trail = Line(
            trail_points[0],
            trail_points[-1],
            color=WHITE,
            stroke_width=1,
            stroke_opacity=0.5
        )
        self.add(trail)
        
        # Animate the dot moving
        self.play(dot.animate.move_to(lens_center + RIGHT * 1.5), run_time=2)
        
        # Change color of lecture line 5
        self.lecture[4].set_color(WHITE)
        self.wait(2)
        
        # Clean up
        self.wait(1)