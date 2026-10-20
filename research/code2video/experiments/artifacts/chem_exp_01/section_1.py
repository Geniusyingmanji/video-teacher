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

class Section1Scene(TeachingScene):
    def construct(self):
        self.setup_layout("Sec 1: Atomic Structure & Valence Electrons", 
                         ['Atoms have a nucleus and shells.', 
                          'Outermost layer is the valence shell.', 
                          'Stability means a full outer shell.', 
                          'Sodium has one valence electron.', 
                          'Chlorine needs one more electron.'])
        
        # === Animation for Lecture Line 1 ===
        # Highlight Lecture Line 1
        self.lecture[0].set_color("#FFD700") # Gold color for nucleus/shells
        
        # Create Nucleus
        nucleus = Circle(radius=0.3, color="#FFD700", fill_opacity=0.8, stroke_width=2)
        nucleus_label = Text("Nucleus", font_size=14, color=WHITE)
        nucleus_group = VGroup(nucleus, nucleus_label)
        nucleus_label.next_to(nucleus, DOWN, buff=0.1)
        
        # Position Nucleus at center of right grid (approx C3/D3)
        self.place_in_area(nucleus_group, 'B2', 'D4', scale_factor=1.0)
        
        # Create Shells
        shell1 = Circle(radius=0.8, color="#CCCCCC", stroke_width=1)
        shell2 = Circle(radius=1.3, color="#CCCCCC", stroke_width=1)
        shell3 = Circle(radius=1.8, color="#CCCCCC", stroke_width=1)
        
        # Align shells with nucleus
        shell1.move_to(nucleus)
        shell2.move_to(nucleus)
        shell3.move_to(nucleus)
        
        # Labels for shells
        label1 = Text("Shell 1", font_size=12, color="#CCCCCC")
        label2 = Text("Shell 2", font_size=12, color="#CCCCCC")
        label3 = Text("Shell 3", font_size=12, color="#CCCCCC")
        
        label1.next_to(shell1, RIGHT, buff=0.05)
        label2.next_to(shell2, RIGHT, buff=0.05)
        label3.next_to(shell3, RIGHT, buff=0.05)
        
        atom_base = VGroup(shell1, shell2, shell3, label1, label2, label3)
        
        self.play(FadeIn(nucleus_group), run_time=1)
        self.play(
            GrowFromCenter(shell1), Write(label1),
            GrowFromCenter(shell2), Write(label2),
            GrowFromCenter(shell3), Write(label3),
            run_time=2
        )
        
        # === Animation for Lecture Line 2 ===
        # Highlight Lecture Line 2
        self.lecture[1].set_color("#FFFFFF") # White for valence shell
        
        # Highlight outermost shell
        valence_highlight = Circle(radius=1.8, color="#FFFFFF", stroke_width=4)
        valence_highlight.move_to(nucleus)
        
        valence_label = Text("Valence Shell", font_size=16, color="#FFFFFF")
        valence_label.next_to(shell3, UP, buff=0.1)
        
        # Pulse animation
        def pulse(mob, t):
            mob.set_stroke(width=4 + 4 * np.sin(t * 4))
            return mob
            
        self.play(
            Create(valence_highlight),
            Write(valence_label),
            run_time=1
        )
        
        # Apply pulse effect for a short duration
        self.play(
            valence_highlight.animate.set_stroke(width=8),
            run_time=0.5
        )
        self.play(
            valence_highlight.animate.set_stroke(width=4),
            run_time=0.5
        )
        
        # Cleanup for next step
        self.play(
            FadeOut(valence_highlight),
            FadeOut(valence_label),
            run_time=0.5
        )
        
        # === Animation for Lecture Line 3 ===
        # Highlight Lecture Line 3
        self.lecture[2].set_color("#00FF00") # Green for stability
        
        # Display Octet Rule text
        octet_text = Text("Octet Rule: Full Outer Shell", font_size=20, color="#00FF00")
        self.place_at_grid(octet_text, 'A4', scale_factor=1.0)
        
        # Create generic atom with electrons
        # We will reuse the shell structure but add electrons
        # Clear previous specific labels if any, but keep shells for context
        # Let's create a new group for the "stable" atom to avoid clutter
        stable_atom = VGroup()
        s_nucleus = Circle(radius=0.3, color="#FFD700", fill_opacity=0.8)
        s_shell1 = Circle(radius=0.8, color="#CCCCCC", stroke_width=1)
        s_shell2 = Circle(radius=1.3, color="#CCCCCC", stroke_width=1)
        s_shell3 = Circle(radius=1.8, color="#CCCCCC", stroke_width=1)
        
        s_nucleus.move_to(nucleus)
        s_shell1.move_to(nucleus)
        s_shell2.move_to(nucleus)
        s_shell3.move_to(nucleus)
        
        # Add 8 electrons to outer shell (Shell 3)
        electrons = VGroup()
        for i in range(8):
            angle = i * (2 * PI / 8)
            pos = s_nucleus.get_center() + np.array([
                1.8 * np.cos(angle), 
                1.8 * np.sin(angle), 
                0
            ])
            dot = Dot(pos, radius=0.05, color="#FFFFFF")
            electrons.add(dot)
        
        stable_atom.add(s_nucleus, s_shell1, s_shell2, s_shell3, electrons)
        
        # Position stable atom in the grid, maybe slightly different to show change
        # Let's place it in the same spot for continuity, but fade out old labels
        self.play(
            FadeOut(atom_base), 
            FadeOut(nucleus_group),
            run_time=0.5
        )
        
        self.play(FadeIn(stable_atom), run_time=1)
        
        # Turn green to indicate stability
        self.play(
            s_shell3.animate.set_color("#00FF00"),
            electrons.animate.set_color("#00FF00"),
            run_time=1
        )
        
        self.play(
            FadeOut(stable_atom),
            FadeOut(octet_text),
            run_time=0.5
        )
        
        # === Animation for Lecture Line 4 ===
        # Highlight Lecture Line 4
        self.lecture[3].set_color("#FF0000") # Red for Sodium
        
        # Create Sodium Model
        na_nucleus = Circle(radius=0.3, color="#FFD700", fill_opacity=0.8)
        na_nucleus_text = Text("Na\n11p+", font_size=12, color=WHITE)
        na_nucleus_text.move_to(na_nucleus)
        
        na_shell1 = Circle(radius=0.8, color="#CCCCCC", stroke_width=1)
        na_shell2 = Circle(radius=1.3, color="#CCCCCC", stroke_width=1)
        na_shell3 = Circle(radius=1.8, color="#CCCCCC", stroke_width=1)
        
        na_nucleus.move_to(nucleus)
        na_shell1.move_to(na_nucleus)
        na_shell2.move_to(na_nucleus)
        na_shell3.move_to(na_nucleus)
        
        # Electrons
        na_e1 = VGroup()
        for i in range(2):
            angle = i * PI
            pos = na_nucleus.get_center() + np.array([0.8 * np.cos(angle), 0.8 * np.sin(angle), 0])
            na_e1.add(Dot(pos, radius=0.05, color="#FFFFFF"))
            
        na_e2 = VGroup()
        for i in range(8):
            angle = i * (2 * PI / 8)
            pos = na_nucleus.get_center() + np.array([1.3 * np.cos(angle), 1.3 * np.sin(angle), 0])
            na_e2.add(Dot(pos, radius=0.05, color="#FFFFFF"))
            
        # Single valence electron
        na_valence_e = Dot(radius=0.08, color="#FF0000")
        na_valence_e.move_to(na_nucleus.get_center() + np.array([1.8, 0, 0]))
        
        na_atom = VGroup(na_nucleus, na_nucleus_text, na_shell1, na_shell2, na_shell3, na_e1, na_e2, na_valence_e)
        
        self.play(FadeIn(na_atom), run_time=1)
        
        # Glow effect on valence electron
        glow = Circle(radius=0.15, color="#FF0000", stroke_width=2, fill_opacity=0.3)
        glow.move_to(na_valence_e)
        
        self.play(
            Create(glow),
            run_time=0.5
        )
        self.play(
            glow.animate.scale(1.5).set_opacity(0),
            run_time=0.5
        )
        
        self.play(
            FadeOut(na_atom),
            FadeOut(glow),
            run_time=0.5
        )
        
        # === Animation for Lecture Line 5 ===
        # Highlight Lecture Line 5
        self.lecture[4].set_color("#00BFFF") # Light Blue for Chlorine
        
        # Create Chlorine Model
        cl_nucleus = Circle(radius=0.3, color="#FFD700", fill_opacity=0.8)
        cl_nucleus_text = Text("Cl\n17p+", font_size=12, color=WHITE)
        cl_nucleus_text.move_to(cl_nucleus)
        
        cl_shell1 = Circle(radius=0.8, color="#CCCCCC", stroke_width=1)
        cl_shell2 = Circle(radius=1.3, color="#CCCCCC", stroke_width=1)
        cl_shell3 = Circle(radius=1.8, color="#CCCCCC", stroke_width=1)
        
        cl_nucleus.move_to(nucleus)
        cl_shell1.move_to(cl_nucleus)
        cl_shell2.move_to(cl_nucleus)
        cl_shell3.move_to(cl_nucleus)
        
        # Electrons
        cl_e1 = VGroup()
        for i in range(2):
            angle = i * PI
            pos = cl_nucleus.get_center() + np.array([0.8 * np.cos(angle), 0.8 * np.sin(angle), 0])
            cl_e1.add(Dot(pos, radius=0.05, color="#FFFFFF"))
            
        cl_e2 = VGroup()
        for i in range(8):
            angle = i * (2 * PI / 8)
            pos = cl_nucleus.get_center() + np.array([1.3 * np.cos(angle), 1.3 * np.sin(angle), 0])
            cl_e2.add(Dot(pos, radius=0.05, color="#FFFFFF"))
            
        cl_e3 = VGroup()
        # 7 electrons in shell 3. Leave one spot empty.
        # Let's place 7 dots evenly, skipping one position (e.g., right side)
        for i in range(8):
            if i == 0: # Skip the first position (0 degrees)
                continue
            angle = i * (2 * PI / 8)
            pos = cl_nucleus.get_center() + np.array([1.8 * np.cos(angle), 1.8 * np.sin(angle), 0])
            cl_e3.add(Dot(pos, radius=0.05, color="#FFFFFF"))
            
        cl_atom = VGroup(cl_nucleus, cl_nucleus_text, cl_shell1, cl_shell2, cl_shell3, cl_e1, cl_e2, cl_e3)
        
        self.play(FadeIn(cl_atom), run_time=1)
        
        # Highlight missing spot
        missing_spot = Circle(radius=0.1, color="#FFFFFF", stroke_width=2)
        missing_spot.move_to(cl_nucleus.get_center() + np.array([1.8, 0, 0]))
        
        missing_label = Text("Missing 1", font_size=14, color="#FFFFFF")
        missing_label.next_to(missing_spot, RIGHT, buff=0.1)
        
        self.play(
            Create(missing_spot),
            Write(missing_label),
            run_time=1
        )
        
        self.wait(2)