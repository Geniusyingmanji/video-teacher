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
        self.setup_layout("Sec 3: The Transformation: Moving the Angles", ['Move the left angle up.', 'It fits perfectly at the top.', 'Now move the right angle up.', 'It fits on the other side.', 'All three sit on one line.'])
        
        # === Setup Geometry ===
        # Define triangle vertices
        # We place the triangle in the center-right area
        # Base is horizontal. Let's use grid points roughly.
        # Bottom Left: D2, Bottom Right: D5, Top: B3
        # Let's adjust to fit well in the 6x6 grid (x: 0.5 to 5.5, y: 2.2 to -2.8)
        
        # Triangle Vertices
        A = np.array([3.0, 1.5, 0])  # Top vertex (approx B3/C3 area)
        B = np.array([1.5, -1.0, 0]) # Bottom Left (approx D2/E2 area)
        C = np.array([4.5, -1.0, 0]) # Bottom Right (approx D5/E5 area)
        
        # Draw Triangle
        triangle = Polygon(A, B, C, color=GREY_B, fill_opacity=0.1, stroke_width=2)
        self.add(triangle)
        
        # Draw Parallel Line at Top
        # The parallel line passes through A.
        # It needs to be long enough to show the 180 degrees.
        # Let's make it from x=0.5 to x=5.5 at y=1.5
        parallel_line = Line(np.array([0.5, 1.5, 0]), np.array([5.5, 1.5, 0]), color=WHITE, stroke_width=2)
        self.add(parallel_line)
        
        # Define Angles
        # Angle A (Top, Red) - Interior angle of triangle at A
        # Angle B (Bottom Left, Blue) - Interior angle at B
        # Angle C (Bottom Right, Green) - Interior angle at C
        
        # We will create arc indicators for the angles
        # Angle at A: Between vector AB and AC
        angle_A = Angle(Line(A, B), Line(A, C), radius=0.4, color=RED, stroke_width=2)
        angle_A.move_to(A) # Angle origin is A by default if vectors are from A
        
        # Angle at B: Between vector BA and BC
        angle_B = Angle(Line(B, A), Line(B, C), radius=0.4, color=BLUE, stroke_width=2)
        angle_B.move_to(B)
        
        # Angle at C: Between vector CA and CB
        angle_C = Angle(Line(C, A), Line(C, B), radius=0.4, color=GREEN, stroke_width=2)
        angle_C.move_to(C)
        
        # Labels for angles
        label_A = Text("A", color=RED, font_size=24).next_to(angle_A, UP, buff=0.1)
        label_B = Text("B", color=BLUE, font_size=24).next_to(angle_B, DOWN, buff=0.1)
        label_C = Text("C", color=GREEN, font_size=24).next_to(angle_C, DOWN, buff=0.1)
        
        self.add(angle_A, label_A, angle_B, label_B, angle_C, label_C)
        
        # Create copies of B and C to animate
        angle_B_copy = angle_B.copy()
        label_B_copy = label_B.copy()
        angle_C_copy = angle_C.copy()
        label_C_copy = label_C.copy()
        
        # === Animation for Lecture Line 1 ===
        # "Move the left angle up."
        self.lecture[0].set_color(BLUE)
        
        # Animate Angle B moving to Top Vertex A
        # It slides up along the left side.
        # For simplicity and clarity, we animate the translation of the angle object to A.
        # The rotation will happen in the next step.
        # We move the center of the angle arc to A.
        # But wait, the angle is defined by vectors. 
        # To simulate "moving the angle", we usually translate the visual representation.
        # Let's translate the angle_B_copy and its label to A.
        
        self.play(
            angle_B_copy.animate.move_to(A),
            label_B_copy.animate.next_to(angle_B_copy, DOWN, buff=0.1),
            run_time=1.5
        )
        
        # === Animation for Lecture Line 2 ===
        # "It fits perfectly at the top."
        self.lecture[1].set_color(BLUE)
        
        # Rotate the blue angle to fit to the left of the red angle on the parallel line.
        # The parallel line is horizontal.
        # The red angle is at A.
        # The blue angle needs to be rotated so its "base" aligns with the parallel line.
        # Original Angle B is at B. Vectors BA and BC.
        # At A, we want the angle to be formed by the parallel line (left side) and the transversal AB.
        # Actually, the geometric proof shows that angle B (interior) is equal to the alternate interior angle at A.
        # The alternate interior angle at A is between the parallel line (left) and AB.
        
        # Let's calculate the rotation.
        # The angle B is "pointing" up-right.
        # At A, the corresponding position is "pointing" left-up relative to the parallel line?
        # No, let's look at the standard proof.
        # Angle B is between AB and BC.
        # Alternate Interior Angle at A is between AB and the Parallel Line (Left side).
        
        # We need to rotate angle_B_copy around A.
        # The current angle_B_copy is at A, but its orientation is still the same as at B.
        # We need to rotate it so that one of its bounding rays aligns with the parallel line.
        
        # Let's determine the rotation angle.
        # Vector BA (from B to A) is roughly (1.5, 2.5).
        # Vector BC (from B to C) is (3, 0).
        # Angle B is between these.
        
        # At A, the transversal is AB (vector from A to B is (-1.5, -2.5)).
        # The parallel line left side is (-1, 0).
        # The angle between AB and Parallel Left is the alternate interior angle.
        
        # To make it visual:
        # We rotate angle_B_copy around A.
        # How much?
        # The angle of vector BA with horizontal is atan2(2.5, 1.5).
        # The angle of vector AB with horizontal is atan2(-2.5, -1.5).
        # This is getting complex to calculate dynamically for arbitrary triangles.
        
        # Simpler approach for animation:
        # We know the target position.
        # The blue angle should sit on the parallel line, to the left of the red angle.
        # Let's create a new angle object that represents the "final" position of B.
        # Final Position of B: At A, between Vector Left (Parallel) and Vector AB.
        vec_left = np.array([-1, 0, 0])
        vec_AB_from_A = B - A
        final_angle_B = Angle(Line(A, A + vec_left), Line(A, B), radius=0.4, color=BLUE, stroke_width=2)
        final_angle_B.move_to(A)
        
        # Animate the transformation
        self.play(
            ReplacementTransform(angle_B_copy, final_angle_B),
            label_B_copy.animate.next_to(final_angle_B, LEFT, buff=0.1),
            run_time=1.5
        )
        angle_B_copy = final_angle_B # Update reference
        
        # === Animation for Lecture Line 3 ===
        # "Now move the right angle up."
        self.lecture[2].set_color(GREEN)
        
        # Move Angle C to Top Vertex A
        self.play(
            angle_C_copy.animate.move_to(A),
            label_C_copy.animate.next_to(angle_C_copy, DOWN, buff=0.1),
            run_time=1.5
        )
        
        # === Animation for Lecture Line 4 ===
        # "It fits on the other side."
        self.lecture[3].set_color(GREEN)
        
        # Rotate/Transform Angle C to fit to the right of the Red angle.
        # Final Position of C: At A, between Vector AB and Vector Right (Parallel).
        vec_right = np.array([1, 0, 0])
        # Wait, the angle at C is between CA and CB.
        # Alternate interior angle at A is between AC and Parallel Right.
        vec_AC_from_A = C - A
        final_angle_C = Angle(Line(A, C), Line(A, A + vec_right), radius=0.4, color=GREEN, stroke_width=2)
        final_angle_C.move_to(A)
        
        self.play(
            ReplacementTransform(angle_C_copy, final_angle_C),
            label_C_copy.animate.next_to(final_angle_C, RIGHT, buff=0.1),
            run_time=1.5
        )
        angle_C_copy = final_angle_C
        
        # === Animation for Lecture Line 5 ===
        # "All three sit on one line."
        self.lecture[4].set_color(YELLOW)
        
        # Highlight that they form a straight line (180 degrees).
        # We can draw a line or just pulse the whole assembly.
        # Let's add a label "180°" or just flash the line.
        
        # Create a group of the three angles at the top
        top_angles = VGroup(final_angle_B, angle_A, final_angle_C)
        
        # Animate a slight pulse or color change to emphasize the alignment
        self.play(
            top_angles.animate.set_color(YELLOW),
            run_time=1
        )
        
        # Add a text label indicating 180 degrees
        text_180 = Text("180°", color=YELLOW, font_size=28).next_to(top_angles, UP, buff=0.5)
        self.play(FadeIn(text_180, shift=DOWN*0.5))
        
        self.wait(2)
        
        # Cleanup
        self.play(
            FadeOut(top_angles),
            FadeOut(text_180),
            FadeOut(label_B_copy),
            FadeOut(label_C_copy),
            run_time=1
        )
        
        self.wait(1)