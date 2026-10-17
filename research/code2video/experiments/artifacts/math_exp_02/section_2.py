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
        # Define colors for each lecture line
        colors = [
            "#FFD700",  # Gold for line 1
            "#87CEEB",  # Sky Blue for line 2
            "#98FB98",  # Pale Green for line 3
            "#FFA07A",  # Light Salmon for line 4
            "#DDA0DD",  # Plum for line 5
        ]

        self.setup_layout(
            "Sec 2: The Parallel Line Bridge (Prerequisite Setup)",
            [
                "Draw a line through the top.",
                "This line is parallel to the base.",
                "Parallel lines create equal angles.",
                "These are Alternate Interior Angles.",
                "They allow us to move angles."
            ]
        )

        # Setup Triangle Geometry
        # Triangle vertices: A (top), B (bottom left), C (bottom right)
        A = np.array([2.5, 1.5, 0])
        B = np.array([1.0, -1.0, 0])
        C = np.array([4.0, -1.0, 0])
        
        triangle = Polygon(A, B, C, color=WHITE, stroke_width=2)
        self.add(triangle)

        # Labels for vertices
        label_A = Text("A", font_size=24, color=WHITE).next_to(A, UP, buff=0.1)
        label_B = Text("B", font_size=24, color=WHITE).next_to(B, DOWN, buff=0.1)
        label_C = Text("C", font_size=24, color=WHITE).next_to(C, DOWN, buff=0.1)
        self.add(label_A, label_B, label_C)

        # === Animation for Lecture Line 1 ===
        # "Draw a line through the top."
        self.lecture[0].set_color(colors[0])
        
        # Horizontal line through A
        line_start = np.array([0.5, A[1], 0])
        line_end = np.array([4.5, A[1], 0])
        parallel_line = Line(line_start, line_end, color=colors[0], stroke_width=3)
        
        self.play(Create(parallel_line), run_time=1.5)
        self.wait(0.5)

        # === Animation for Lecture Line 2 ===
        # "This line is parallel to the base."
        self.lecture[1].set_color(colors[1])
        
        # Add parallel arrows
        # Arrow on the new line
        arrow_top = Arrow(
            line_start + np.array([0.5, 0, 0]), 
            line_start + np.array([1.5, 0, 0]), 
            color=colors[1], 
            buff=0
        )
        # Arrow on the base BC
        arrow_base = Arrow(
            B + np.array([0.5, 0, 0]), 
            B + np.array([1.5, 0, 0]), 
            color=colors[1], 
            buff=0
        )
        
        self.play(GrowArrow(arrow_top), GrowArrow(arrow_base), run_time=1)
        self.wait(0.5)

        # === Animation for Lecture Line 3 ===
        # "Parallel lines create equal angles."
        self.lecture[2].set_color(colors[2])
        
        # Highlight angle at A (left side, between AB and parallel line)
        # Angle is between vector AB and vector Left
        vec_AB = B - A
        vec_Left = np.array([-1, 0, 0])
        angle_A_left = Angle(Line(A, A + vec_Left), Line(A, A + vec_AB), radius=0.3, color=colors[2])
        
        # Highlight angle at B (between BA and BC)
        vec_BA = A - B
        vec_BC = C - B
        angle_B = Angle(Line(B, B + vec_BC), Line(B, B + vec_BA), radius=0.3, color=colors[2])
        
        # Flash to show equality
        self.play(Create(angle_A_left), Create(angle_B), run_time=1)
        self.play(Flash(angle_A_left, color=colors[2], flash_radius=0.5), 
                  Flash(angle_B, color=colors[2], flash_radius=0.5), run_time=1)
        self.wait(0.5)

        # === Animation for Lecture Line 4 ===
        # "These are Alternate Interior Angles."
        self.lecture[3].set_color(colors[3])
        
        # Highlight angle at A (right side, between AC and parallel line)
        vec_AC = C - A
        vec_Right = np.array([1, 0, 0])
        angle_A_right = Angle(Line(A, A + vec_AC), Line(A, A + vec_Right), radius=0.3, color=colors[3])
        
        # Highlight angle at C (between CA and CB)
        vec_CA = A - C
        vec_CB = B - C
        angle_C = Angle(Line(C, C + vec_CA), Line(C, C + vec_CB), radius=0.3, color=colors[3])
        
        # Flash to show equality
        self.play(Create(angle_A_right), Create(angle_C), run_time=1)
        self.play(Flash(angle_A_right, color=colors[3], flash_radius=0.5), 
                  Flash(angle_C, color=colors[3], flash_radius=0.5), run_time=1)
        
        # Label the angles
        label_alt_int = Text("Alternate Interior Angles", font_size=18, color=colors[3])
        self.place_at_grid(label_alt_int, "D3", scale_factor=0.8)
        
        # Subtle Z-path trace connecting the angles
        # Path from angle_A_left to angle_B to angle_A_right to angle_C
        path_points = [
            angle_A_left.get_center(),
            angle_B.get_center(),
            angle_A_right.get_center(),
            angle_C.get_center()
        ]
        z_path = VMobject(color=colors[3], stroke_width=2)
        z_path.set_points_smoothly(path_points)
        
        self.play(FadeIn(label_alt_int), Create(z_path), run_time=1.5)
        self.wait(0.5)

        # === Animation for Lecture Line 5 ===
        # "They allow us to move angles."
        self.lecture[4].set_color(colors[4])
        
        # Animate moving angle A_left to position B
        # Create a copy of angle_A_left to animate
        angle_move_copy = angle_A_left.copy()
        
        # Animate the copy moving to B's angle position
        self.play(
            Transform(angle_move_copy, angle_B.copy()),
            run_time=1.5
        )
        
        # Animate moving angle A_right to position C
        angle_move_copy2 = angle_A_right.copy()
        self.play(
            Transform(angle_move_copy2, angle_C.copy()),
            run_time=1.5
        )
        
        self.wait(1)