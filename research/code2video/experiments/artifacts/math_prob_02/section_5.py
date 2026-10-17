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
        self.setup_layout("Sec 5: Verification and Final Insight", ['Original: f(x) = x^3 + 2x.', "Derivative: f'(x) = 3x^2 + 2.", 'Horizontal tangent means slope is zero.', 'Derivative crosses x-axis at these points.', 'Derivative describes rate of change.'])
        
        # Define colors for lecture lines and corresponding elements
        # Lecture Line 1: Original: f(x) = x^3 + 2x. -> Color #00FFFF (Cyan)
        # Lecture Line 2: Derivative: f'(x) = 3x^2 + 2. -> Color #FF5555 (Red)
        # Lecture Line 3: Horizontal tangent means slope is zero. -> Color #FFFF00 (Yellow)
        # Lecture Line 4: Derivative crosses x-axis at these points. -> Color #00FF00 (Green)
        # Lecture Line 5: Derivative describes rate of change. -> Color #FF00FF (Magenta)

        # Setup coordinate system for the graph on the right side
        # The grid area is roughly x: 0.5 to 6.5, y: -3.8 to 2.2
        # We will place the axes in the center of the grid area
        axes_center = self.place_in_area(
            VGroup(), 'A1', 'F6', scale_factor=1.0
        )
        
        # Create Axes
        axes = Axes(
            x_range=[-2, 2, 1],
            y_range=[-5, 5, 1],
            x_length=5,
            y_length=5,
            axis_config={"color": GRAY},
            tips=False
        )
        
        # Position axes in the center of the right side grid
        # Center of A1-F6 is roughly at grid center
        # Grid A1 is (0.5, 2.2), F6 is (6.5, -3.8)
        # Center is (3.5, -0.8)
        axes.move_to(np.array([3.5, -0.8, 0]))
        
        # Define functions
        def f(x):
            return x**3 + 2*x
            
        def f_prime(x):
            return 3*x**2 + 2

        # === Animation for Lecture Line 1 ===
        # "Original: f(x) = x^3 + 2x."
        # Highlight Lecture Line 1
        self.lecture[0].set_color("#00FFFF")
        
        # Plot original cubic curve
        cubic_curve = axes.plot(f, color="#00FFFF")
        cubic_label = MathTex("f(x)", color="#00FFFF").scale(0.7)
        cubic_label.next_to(cubic_curve.get_start(), UP, buff=0.2)
        
        self.play(Create(axes), run_time=1)
        self.play(Create(cubic_curve), Write(cubic_label), run_time=2)
        self.wait(1)

        # === Animation for Lecture Line 2 ===
        # "Derivative: f'(x) = 3x^2 + 2."
        # Highlight Lecture Line 2
        self.lecture[1].set_color("#FF5555")
        
        # Plot derivative quadratic curve
        derivative_curve = axes.plot(f_prime, color="#FF5555")
        derivative_label = MathTex("f'(x)", color="#FF5555").scale(0.7)
        derivative_label.next_to(derivative_curve.get_start(), DOWN, buff=0.2)
        
        self.play(Create(derivative_curve), Write(derivative_label), run_time=2)
        self.wait(1)

        # === Animation for Lecture Line 3 ===
        # "Horizontal tangent means slope is zero."
        # Highlight Lecture Line 3
        self.lecture[2].set_color("#FFFF00")
        
        # Find point on cubic where tangent is horizontal.
        # f'(x) = 0 => 3x^2 + 2 = 0 => x^2 = -2/3. No real solution.
        # Wait, the script says "Horizontal tangent means slope is zero."
        # But f(x) = x^3 + 2x has no horizontal tangent because f'(x) = 3x^2 + 2 is always positive.
        # Let's re-read the animation description.
        # "Animation step 2: Highlight a point on the cubic curve where the tangent is horizontal."
        # This is mathematically impossible for f(x) = x^3 + 2x.
        # However, I must follow the script. Maybe the script implies a generic case or there's a mistake in the script's math.
        # Or maybe I should pick a point where the slope is minimal? Or just pick a point and draw a tangent?
        # Let's look at the next step: "Show a vertical line dropping from that point to the x-axis, intersecting the red derivative curve at y=0."
        # This implies that at that x-value, f'(x) = 0.
        # Since f'(x) = 3x^2 + 2 never equals 0, there is a contradiction in the prompt's math.
        # I will assume the prompt meant a function like f(x) = x^3 - 3x which has f'(x) = 3x^2 - 3 = 0 at x = +/- 1.
        # But I must use the provided function f(x) = x^3 + 2x.
        # Perhaps the "horizontal tangent" is a conceptual error in the prompt, but I need to visualize the *idea*.
        # Let's pick x=0. f(0)=0. f'(0)=2. Not zero.
        # Let's pick x=1. f(1)=3. f'(1)=5.
        # Let's just pick a point, say x=0, and draw the tangent line there, even though it's not horizontal.
        # Or, to satisfy the visual requirement of "intersecting derivative at y=0", I might need to fudge the math visualization or pick a different function?
        # No, I must stick to the code. I will pick a point x=0.
        # Tangent at x=0: y - 0 = 2(x - 0) => y = 2x.
        # The derivative curve at x=0 is y=2.
        # The prompt says "intersecting the red derivative curve at y=0". This is impossible.
        
        # Alternative interpretation: Maybe the "horizontal tangent" refers to the *derivative* being zero?
        # Let's just visualize a tangent line at x=0 to show the concept, even if the math in the prompt is flawed.
        # I will draw a tangent line at x=0.
        
        x_point = 0
        y_point = f(x_point)
        point_on_curve = axes.c2p(x_point, y_point)
        
        # Slope at x=0 is 2
        slope = f_prime(x_point)
        
        # Create tangent line
        tangent_line = Line(
            axes.c2p(x_point - 1, y_point - slope),
            axes.c2p(x_point + 1, y_point + slope),
            color="#FFFF00",
            stroke_width=3
        )
        
        # Highlight the point
        point_dot = Dot(point_on_curve, color="#FFFF00", radius=0.05)
        
        self.play(Create(tangent_line), GrowFromCenter(point_dot), run_time=1.5)
        self.wait(1)

        # === Animation for Lecture Line 4 ===
        # "Derivative crosses x-axis at these points."
        # Highlight Lecture Line 4
        self.lecture[3].set_color("#00FF00")
        
        # "Show a vertical line dropping from that point to the x-axis, intersecting the red derivative curve at y=0."
        # Again, mathematically impossible. I will drop a vertical line from the point on the cubic to the x-axis.
        # It will intersect the derivative curve at y=2 (since x=0).
        # I will just draw the vertical line and a dot at the intersection with the derivative curve.
        
        x_axis_point = axes.c2p(x_point, 0)
        derivative_point = axes.c2p(x_point, f_prime(x_point))
        
        vertical_line = Line(
            point_on_curve,
            x_axis_point,
            color="#00FF00",
            stroke_width=2
        )
        
        # Dot at the intersection with derivative curve
        intersection_dot = Dot(derivative_point, color="#00FF00", radius=0.05)
        
        self.play(Create(vertical_line), GrowFromCenter(intersection_dot), run_time=1.5)
        self.wait(1)

        # === Animation for Lecture Line 5 ===
        # "Derivative describes rate of change."
        # Highlight Lecture Line 5
        self.lecture[4].set_color("#FF00FF")
        
        # "Flash the intersection point on the derivative curve to emphasize the zero value."
        # Since the value isn't zero, I'll just flash the intersection point.
        self.play(Flash(intersection_dot, color="#00FF00", flash_radius=0.3, run_time=1))
        
        # "Fade out graphs. Display text 'Rate of Change' (color #00FF00) in center."
        graphs_group = VGroup(axes, cubic_curve, derivative_curve, cubic_label, derivative_label, tangent_line, point_dot, vertical_line, intersection_dot)
        
        self.play(FadeOut(graphs_group), run_time=1)
        
        rate_of_change_text = Text("Rate of Change", color="#00FF00", font_size=36)
        rate_of_change_text.move_to(np.array([3.5, -0.8, 0])) # Center of the grid area
        
        self.play(Write(rate_of_change_text), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(rate_of_change_text), run_time=1)
        self.wait(1)