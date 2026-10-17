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
        self.setup_layout(
            "Sec 5: The Result: The Crystal Lattice of NaCl", 
            [
                'Ions attract multiple other ions.', 
                'They form a 3D grid.', 
                'This is a crystal lattice.', 
                'The pattern creates solid salt.', 
                'Microscopic bonds make macroscopic salt.'
            ]
        )

        # Define colors
        NA_COLOR = "#FF6B6B" # Light Red
        CL_COLOR = "#4D96FF" # Light Blue
        LATTICE_COLOR = "#FFFFFF"
        
        # Center of the animation area (approx C3/D3)
        center_pos = self.grid['C3']

        # --- Initial Setup: Central Pair ---
        na_ion = Circle(radius=0.3, color=NA_COLOR, fill_opacity=1).add(Text("Na⁺", font_size=16, color=WHITE))
        cl_ion = Circle(radius=0.3, color=CL_COLOR, fill_opacity=1).add(Text("Cl⁻", font_size=16, color=WHITE))
        
        na_ion.move_to(center_pos + LEFT * 0.5)
        cl_ion.move_to(center_pos + RIGHT * 0.5)
        
        self.play(FadeIn(na_ion), FadeIn(cl_ion), run_time=1)
        self.wait(0.5)

        # === Animation for Lecture Line 1 ===
        # "Ions attract multiple other ions."
        self.lecture[0].set_color(NA_COLOR)
        
        # New ions fly in from corners
        # Positions relative to center for a 3x3 grid (center is 1,1)
        # Corners of the 3x3 block: (-1,-1), (1,-1), (-1,1), (1,1)
        # Center is (0,0) in local coords.
        
        # Define local offsets for a 3x3 grid
        # (0,0) is center
        # (-1, -1) top-left, (1, -1) top-right, (-1, 1) bottom-left, (1, 1) bottom-right
        # Wait, y is inverted in screen coords? No, Manim y is up.
        # Grid:
        # (-1, 1)   (0, 1)   (1, 1)
        # (-1, 0)   (0, 0)   (1, 0)
        # (-1, -1)  (0, -1)  (1, -1)
        
        # Existing: (0,0) is Na? No, we have Na at -0.5, Cl at +0.5.
        # Let's reset to a cleaner grid structure for the animation.
        # Let's assume the central pair is at (0,0) and (1,0) in a local grid?
        # Actually, the description says "Central Na+-Cl- pair remains".
        # Let's stick to the visual flow.
        
        # Create new ions
        na_new1 = Circle(radius=0.3, color=NA_COLOR, fill_opacity=1).add(Text("Na⁺", font_size=16, color=WHITE))
        cl_new1 = Circle(radius=0.3, color=CL_COLOR, fill_opacity=1).add(Text("Cl⁻", font_size=16, color=WHITE))
        na_new2 = Circle(radius=0.3, color=NA_COLOR, fill_opacity=1).add(Text("Na⁺", font_size=16, color=WHITE))
        cl_new2 = Circle(radius=0.3, color=CL_COLOR, fill_opacity=1).add(Text("Cl⁻", font_size=16, color=WHITE))
        
        # Start positions: Off-screen corners
        start_pos_1 = np.array([-6, 4, 0])
        start_pos_2 = np.array([8, 4, 0])
        start_pos_3 = np.array([-6, -4, 0])
        start_pos_4 = np.array([8, -4, 0])
        
        na_new1.move_to(start_pos_1)
        cl_new1.move_to(start_pos_2)
        na_new2.move_to(start_pos_3)
        cl_new2.move_to(start_pos_4)
        
        # Target positions: Surround the central pair
        # Central pair is at center_pos +/- 0.5 RIGHT
        # Let's form a 2x2 block around the center? Or just surround?
        # Description: "fly in from all four corners" -> implies they join the structure.
        # Let's place them to form a 2x2 checkerboard with the existing pair?
        # Existing: Na (left), Cl (right).
        # Let's add Na (top-left), Cl (top-right), Cl (bottom-left), Na (bottom-right)?
        # No, alternating.
        # Center (0,0) is Na? No, Na is at -0.5, Cl at +0.5.
        # Let's define a local coordinate system centered at `center_pos`.
        # Na is at (-0.5, 0). Cl is at (0.5, 0).
        
        # Target 1 (Top Left): Na? No, if Na is at (-0.5,0), top-left neighbor should be Cl?
        # Let's just place them in a 2x2 grid centered at 0.
        # Pos 1: (-0.5, 0.5) -> Cl (to alternate with Na at -0.5,0? No, vertical neighbor)
        # Let's simplify:
        # Row 1: Cl, Na
        # Row 2: Na, Cl
        # Current: Na at (-0.5, 0), Cl at (0.5, 0). This is Row 2.
        # So we need Row 1: Cl at (-0.5, 0.5), Na at (0.5, 0.5).
        # And maybe Row 3? "All four corners" might imply a 3x3 or just the immediate neighbors.
        # Let's add 4 ions to make a 2x4 or 4x2?
        # Let's add ions to make a 2x2 block above and below?
        # Let's just add 4 ions to form a larger cluster.
        
        # Let's place them to form a 2x2 block centered at (0, 0.5) and (0, -0.5)?
        # Simpler: Just place them at the 4 diagonal positions relative to the center pair.
        
        target_1 = center_pos + LEFT * 0.5 + UP * 0.5
        target_2 = center_pos + RIGHT * 0.5 + UP * 0.5
        target_3 = center_pos + LEFT * 0.5 + DOWN * 0.5
        target_4 = center_pos + RIGHT * 0.5 + DOWN * 0.5
        
        # Assign types to alternate
        # Top Left (target_1): Cl (since Na is below it at -0.5,0)
        # Top Right (target_2): Na (since Cl is below it at 0.5,0)
        # Bottom Left (target_3): Cl
        # Bottom Right (target_4): Na
        
        # We have na_new1, cl_new1, na_new2, cl_new2.
        # Let's map:
        # cl_new1 -> target_1
        # na_new1 -> target_2
        # cl_new2 -> target_3
        # na_new2 -> target_4
        
        self.play(
            cl_new1.animate.move_to(target_1),
            na_new1.animate.move_to(target_2),
            cl_new2.animate.move_to(target_3),
            na_new2.animate.move_to(target_4),
            run_time=1.5
        )
        self.wait(0.5)

        # === Animation for Lecture Line 2 ===
        # "They form a 3D grid."
        self.lecture[1].set_color(CL_COLOR)
        
        # Arrange into 2D checkerboard.
        # Currently we have a 2x2 block (if we consider the central pair as part of it).
        # Let's expand to a 3x3 or 4x4 2D grid.
        # Let's create a 3x3 grid centered at center_pos.
        
        ions_group = VGroup(na_ion, cl_ion, na_new1, cl_new1, na_new2, cl_new2)
        
        # Define 3x3 grid positions
        # Center is (0,0).
        # (-1, 1), (0, 1), (1, 1)
        # (-1, 0), (0, 0), (1, 0)
        # (-1, -1), (0, -1), (1, -1)
        
        # We need 9 ions for a 3x3. We have 6. Let's add 3 more.
        na_extra1 = Circle(radius=0.3, color=NA_COLOR, fill_opacity=1).add(Text("Na⁺", font_size=16, color=WHITE))
        cl_extra1 = Circle(radius=0.3, color=CL_COLOR, fill_opacity=1).add(Text("Cl⁻", font_size=16, color=WHITE))
        na_extra2 = Circle(radius=0.3, color=NA_COLOR, fill_opacity=1).add(Text("Na⁺", font_size=16, color=WHITE))
        
        # Start positions
        na_extra1.move_to(np.array([0, 6, 0]))
        cl_extra1.move_to(np.array([-6, 0, 0]))
        na_extra2.move_to(np.array([6, 0, 0]))
        
        # Target positions for 3x3 grid
        # Let's define the grid points
        g = 0.5 # spacing
        
        pos_00 = center_pos
        pos_10 = center_pos + RIGHT * g
        pos_m10 = center_pos + LEFT * g
        
        pos_01 = center_pos + UP * g
        pos_11 = center_pos + RIGHT * g + UP * g
        pos_m11 = center_pos + LEFT * g + UP * g
        
        pos_0m1 = center_pos + DOWN * g
        pos_1m1 = center_pos + RIGHT * g + DOWN * g
        pos_m1m1 = center_pos + LEFT * g + DOWN * g
        
        # Map existing ions to these positions
        # Current:
        # na_ion at center_pos + LEFT * 0.5 -> pos_m10
        # cl_ion at center_pos + RIGHT * 0.5 -> pos_10
        # cl_new1 at target_1 (pos_m11)
        # na_new1 at target_2 (pos_11)
        # cl_new2 at target_3 (pos_m1m1)
        # na_new2 at target_4 (pos_1m1)
        
        # Missing: Center (pos_00), Top Center (pos_01), Bottom Center (pos_0m1)
        # Center should be Cl (if neighbors are Na) or Na (if neighbors are Cl).
        # Neighbors of Center:
        # Left: Na (pos_m10)
        # Right: Cl (pos_10) -> Wait, this is not alternating horizontally.
        # My previous placement:
        # Row 2 (y=0): Na (left), Cl (right).
        # Row 1 (y=1): Cl (left), Na (right).
        # Row 3 (y=-1): Cl (left), Na (right).
        
        # This is not a proper checkerboard.
        # Let's re-arrange everything into a proper 3x3 checkerboard.
        
        # Pattern:
        # Cl Na Cl
        # Na Cl Na
        # Cl Na Cl
        
        # Targets:
        # pos_m11: Cl
        # pos_01: Na
        # pos_11: Cl
        
        # pos_m10: Na
        # pos_00: Cl
        # pos_10: Na
        
        # pos_m1m1: Cl
        # pos_0m1: Na
        # pos_1m1: Cl
        
        # Let's assign the 9 ions to these 9 spots.
        # We have:
        # na_ion, cl_ion, na_new1, cl_new1, na_new2, cl_new2, na_extra1, cl_extra1, na_extra2
        
        # Let's just clear and recreate for simplicity in code logic, or animate to new positions.
        # Animating to new positions is better.
        
        # Map:
        # pos_m11 (Cl): cl_new1
        # pos_01 (Na): na_extra1
        # pos_11 (Cl): cl_extra1
        
        # pos_m10 (Na): na_ion
        # pos_00 (Cl): cl_ion
        # pos_10 (Na): na_new1
        
        # pos_m1m1 (Cl): cl_new2
        # pos_0m1 (Na): na_new2
        # pos_1m1 (Cl): na_extra2 # Wait, na_extra2 is Na, pos_1m1 needs Cl.
        
        # Let's swap types or positions.
        # Let's just create a new group of 9 ions with correct types and positions,
        # and transform the existing ones?
        # Easier: Define the final state and animate existing ions to the nearest correct type slot.
        # Since we have 6 Na/Cl mixed, and need 5 Na and 4 Cl (or vice versa).
        # 3x3: 5 of one, 4 of other.
        # Let's use 5 Cl, 4 Na.
        
        # Final Positions:
        # Cl Na Cl
        # Na Cl Na
        # Cl Na Cl
        
        # Ions:
        # Cl: cl_ion, cl_new1, cl_new2, cl_extra1, (need one more Cl)
        # Na: na_ion, na_new1, na_new2, na_extra1, na_extra2
        
        # We have 5 Na and 4 Cl. Perfect.
        
        # Assignments:
        # pos_m11 (Cl): cl_new1
        # pos_01 (Na): na_extra1
        # pos_11 (Cl): cl_extra1
        
        # pos_m10 (Na): na_ion
        # pos_00 (Cl): cl_ion
        # pos_10 (Na): na_new1
        
        # pos_m1m1 (Cl): cl_new2
        # pos_0m1 (Na): na_new2
        # pos_1m1 (Cl): ??? We need a Cl here. We have no more Cl.
        # We have na_extra2 left. It is Na.
        # So pos_1m1 must be Na?
        # If pos_1m1 is Na, then the pattern is:
        # Cl Na Cl
        # Na Cl Na
        # Cl Na Na  <- Broken pattern.
        
        # Let's change the pattern to:
        # Na Cl Na
        # Cl Na Cl
        # Na Cl Na
        # This requires 5 Na, 4 Cl.
        
        # Targets:
        # pos_m11: Na
        # pos_01: Cl
        # pos_11: Na
        
        # pos_m10: Cl
        # pos_00: Na
        # pos_10: Cl
        
        # pos_m1m1: Na
        # pos_0m1: Cl
        # pos_1m1: Na
        
        # Assignments:
        # pos_m11 (Na): na_extra1
        # pos_01 (Cl): cl_new1
        # pos_11 (Na): na_extra2
        
        # pos_m10 (Cl): cl_new2
        # pos_00 (Na): na_ion
        # pos_10 (Cl): cl_ion
        
        # pos_m1m1 (Na): na_new2
        # pos_0m1 (Cl): cl_extra1
        # pos_1m1 (Na): na_new1
        
        self.play(
            na_extra1.animate.move_to(pos_m11),
            cl_new1.animate.move_to(pos_01),
            na_extra2.animate.move_to(pos_11),
            
            cl_new2.animate.move_to(pos_m10),
            na_ion.animate.move_to(pos_00),
            cl_ion.animate.move_to(pos_10),
            
            na_new2.animate.move_to(pos_m1m1),
            cl_extra1.animate.move_to(pos_0m1),
            na_new1.animate.move_to(pos_1m1),
            run_time=1.5
        )
        
        # Group them
        grid_2d = VGroup(
            na_extra1, cl_new1, na_extra2,
            cl_new2, na_ion, cl_ion,
            na_new2, cl_extra1, na_new1
        )
        
        self.wait(0.5)

        # === Animation for Lecture Line 3 ===
        # "This is a crystal lattice."
        self.lecture[2].set_color("#FFD93D") # Yellowish
        
        # Suggest 3D structure.
        # Add a back layer? Or just scale/shift slightly to imply depth.
        # "More layers of ions appear above and below"
        
        # Let's create a "back" layer that is slightly smaller and darker/transparent.
        back_layer_ions = VGroup()
        for ion in grid_2d:
            back_ion = ion.copy()
            back_ion.scale(0.8)
            back_ion.set_opacity(0.5)
            back_layer_ions.add(back_ion)
            
        # Position back layer slightly behind (shift up and left slightly, or just scale down from center)
        back_layer_ions.move_to(center_pos)
        back_layer_ions.scale(0.8)
        back_layer_ions.shift(UP * 0.2 + LEFT * 0.2) # Pseudo 3D
        
        self.play(FadeIn(back_layer_ions), run_time=1)
        
        # Also add a front layer? "Above and below"
        # Let's just stick to one back layer for simplicity, or add a top layer.
        # Let's add a "top" layer (shifted up)
        top_layer_ions = VGroup()
        for ion in grid_2d:
            top_ion = ion.copy()
            top_ion.scale(0.8)
            top_ion.set_opacity(0.5)
            top_layer_ions.add(top_ion)
            
        top_layer_ions.move_to(center_pos)
        top_layer_ions.scale(0.8)
        top_layer_ions.shift(UP * 0.4)
        
        self.play(FadeIn(top_layer_ions), run_time=1)
        
        self.wait(0.5)

        # === Animation for Lecture Line 4 ===
        # "The pattern creates solid salt."
        self.lecture[3].set_color("#6BCB77") # Green
        
        # Solidify into a white crystalline cube.
        # Fade out individual ions, fade in a cube.
        
        cube = Cube(side_length=2.0, color=LATTICE_COLOR, fill_opacity=0.2, stroke_width=2)
        cube.move_to(center_pos)
        
        # Add some internal lines to look like a lattice?
        lattice_lines = VGroup()
        # Vertical lines
        for x in [-0.5, 0.5]:
            line = Line(np.array([x, -1, 0]), np.array([x, 1, 0]), color=LATTICE_COLOR, stroke_width=1)
            lattice_lines.add(line)
        # Horizontal lines
        for y in [-0.5, 0.5]:
            line = Line(np.array([-1, y, 0]), np.array([1, y, 0]), color=LATTICE_COLOR, stroke_width=1)
            lattice_lines.add(line)
            
        lattice_lines.move_to(center_pos)
        
        self.play(
            FadeOut(grid_2d),
            FadeOut(back_layer_ions),
            FadeOut(top_layer_ions),
            FadeIn(cube),
            FadeIn(lattice_lines),
            run_time=1.5
        )
        
        # Label 'Crystal Lattice'
        label = Text("Crystal Lattice", font_size=24, color=LATTICE_COLOR)
        self.place_at_grid(label, 'A3', scale_factor=1.0)
        # Adjust position to be next to the cube
        label.next_to(cube, UP, buff=0.5)
        
        self.play(FadeIn(label), run_time=1)
        
        self.wait(0.5)

        # === Animation for Lecture Line 5 ===
        # "Microscopic bonds make macroscopic salt."
        self.lecture[4].set_color("#FF9F43") # Orange
        
        # Transform cube into salt shaker.
        # Draw a simple salt shaker.
        shaker_body = RoundedRectangle(corner_radius=0.2, width=1.5, height=2.0, color=WHITE, fill_opacity=0.8)
        shaker_top = Circle(radius=0.4, color=WHITE, fill_opacity=0.8)
        shaker_top.shift(UP * 1.2)
        
        # Holes on top
        holes = VGroup(*[Dot(radius=0.05, color=BLACK) for _ in range(3)])
        holes.arrange(RIGHT, buff=0.1)
        holes.move_to(shaker_top)
        
        shaker = VGroup(shaker_body, shaker_top, holes)
        shaker.move_to(center_pos)
        
        # Transform cube to shaker
        self.play(
            Transform(cube, shaker_body),
            Transform(lattice_lines, shaker_top), # Rough transform
            FadeIn(holes),
            run_time=1.5
        )
        
        # Remove label
        self.play(FadeOut(label), run_time=0.5)
        
        # Text 'Sodium Chloride (NaCl)'
        salt_text = Text("Sodium Chloride (NaCl)", font_size=24, color=WHITE)
        salt_text.next_to(shaker, DOWN, buff=0.5)
        
        self.play(FadeIn(salt_text), run_time=1)
        
        # Shaker shakes 'no' to liquid
        # Create a drop of liquid
        drop = Circle(radius=0.2, color="#4D96FF", fill_opacity=1)
        drop.move_to(shaker.get_top() + UP * 1.0)
        
        self.play(FadeIn(drop), run_time=0.5)
        
        # Shake animation
        self.play(Rotate(shaker, angle=0.2, about_point=shaker.get_center()), run_time=0.2)
        self.play(Rotate(shaker, angle=-0.4, about_point=shaker.get_center()), run_time=0.4)
        self.play(Rotate(shaker, angle=0.2, about_point=shaker.get_center()), run_time=0.2)
        
        # Drop falls or fades
        self.play(drop.animate.shift(DOWN * 0.5).set_opacity(0), run_time=0.5)
        
        self.wait(1)