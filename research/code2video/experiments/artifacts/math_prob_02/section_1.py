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
        self.setup_layout("Sec 1: The Concept of the Derivative: Slope as a Function", ['Derivative is a slope detector.', 'Tangent line moves along the curve.', 'Slope changes at every single point.', 'We need a formula for any x.', 'Think of it as track steepness.'])
        
        # Define colors
        CURVE_COLOR = "#00FFFF"
        POINT_COLOR = "#FFFF00"
        TANGENT_COLOR = "#FF5555"
        TEXT_COLOR = "#FFFFFF"
        
        # Define the curve function
        # A cubic curve for visual interest
        func = lambda x: 0.5 * (x - 2) * (x - 0) * (x + 2)  # Roots at -2, 0, 2
        
        # Create the curve
        # We need to position this in the grid area.
        # Let's define a local coordinate system for the curve and then move it.
        # Or just plot it in a range and move the whole graph.
        
        x_min, x_max = -3, 3
        curve = FunctionGraph(func, x_range=[x_min, x_max], color=CURVE_COLOR)
        
        # Calculate derivative for tangent slope
        def derivative(x):
            # f(x) = 0.5 * (x^3 - 4x) = 0.5x^3 - 2x
            # f'(x) = 1.5x^2 - 2
            return 1.5 * x**2 - 2
        
        # Helper function to get tangent line at a specific x
        def get_tangent_line(x_val):
            y_val = func(x_val)
            slope = derivative(x_val)
            # Line equation: y - y_val = slope * (x - x_val)
            # y = slope * x + (y_val - slope * x_val)
            m = slope
            b = y_val - slope * x_val
            line = Line(
                start=np.array([x_min, m * x_min + b, 0]),
                end=np.array([x_max, m * x_max + b, 0]),
                color=TANGENT_COLOR
            )
            return line

        # Create the moving point
        point = Dot(color=POINT_COLOR, radius=0.1)
        
        # Initial position of the point (start from left)
        start_x = -2.5
        point.move_to(np.array([start_x, func(start_x), 0]))
        
        # Initial tangent line
        tangent_line = get_tangent_line(start_x)
        
        # Group curve, point, and tangent for easier management
        # But we need to animate them separately.
        
        # Position the entire graph in the grid area
        # Let's place the center of the graph (0,0) at grid position C3 or D3
        # Grid C3 is approx (3.5, 0.5). Grid D3 is approx (3.5, -0.5).
        # Let's aim for the center of the right side.
        # The grid x range is 1.5 to 6.5. Center x is 4.
        # The grid y range is 2.5 to -2.5. Center y is 0.
        # So we want to move the graph so that its origin (0,0) is at (4, 0).
        
        graph_group = VGroup(curve, point, tangent_line)
        # We will move the group, but the point and tangent need to update relative to the curve.
        # It's better to keep the curve in a fixed local frame and move the whole group.
        # However, Manim's FunctionGraph is in global coords.
        # Let's just shift the curve, point, and tangent by a vector.
        
        shift_vector = np.array([4, 0, 0])
        
        curve.shift(shift_vector)
        point.shift(shift_vector)
        tangent_line.shift(shift_vector)
        
        # Update the get_tangent_line function to account for the shift?
        # No, it's easier to define a new function that returns the tangent in the shifted space.
        def get_shifted_tangent_line(x_val):
            y_val = func(x_val)
            slope = derivative(x_val)
            m = slope
            b = y_val - slope * x_val
            # Points in local space
            start_local = np.array([x_min, m * x_min + b, 0])
            end_local = np.array([x_max, m * x_max + b, 0])
            # Shift to global space
            start_global = start_local + shift_vector
            end_global = end_local + shift_vector
            line = Line(
                start=start_global,
                end=end_global,
                color=TANGENT_COLOR
            )
            return line

        # Recreate initial tangent with shift
        tangent_line = get_shifted_tangent_line(start_x)
        
        # === Animation for Lecture Line 1 ===
        # "Derivative is a slope detector."
        self.lecture[0].set_color(CURVE_COLOR)
        
        # Fade in the curve
        self.play(FadeIn(curve, shift=0.5 * DOWN), run_time=1.5)
        
        # Point appears on the curve
        self.play(FadeIn(point), run_time=0.5)
        
        # === Animation for Lecture Line 2 ===
        # "Tangent line moves along the curve."
        self.lecture[1].set_color(TANGENT_COLOR)
        
        # Draw the tangent line
        self.play(Create(tangent_line), run_time=1.0)
        
        # The point moves slowly along the curve from left to right
        # We need to animate the point and the tangent line together.
        # Use a custom updater or interpolate.
        
        # Let's define the animation of the point moving from x=-2.5 to x=2.5
        # And the tangent line updating accordingly.
        
        # Create a helper to update the point and tangent
        def update_point_and_tangent(mob, t):
            # t goes from 0 to 1
            x_val = start_x + t * (2.5 - start_x) # -2.5 to 2.5
            y_val = func(x_val)
            # Update point position
            mob[0].move_to(np.array([x_val, y_val, 0]) + shift_vector)
            # Update tangent line
            new_tangent = get_shifted_tangent_line(x_val)
            # Replace the line
            mob[1].become(new_tangent)

        # Group point and tangent line for the updater
        moving_group = VGroup(point, tangent_line)
        
        # Animate the movement
        self.play(
            moving_group.animate,
            run_time=4.0,
            rate_func=linear
        )
        
        # Wait, the updater approach with `become` inside a play is tricky.
        # Better to use `UpdateFromAlphaFunc` or simply interpolate in a loop?
        # Manim's `play` with updaters is better.
        
        # Let's restart this part properly.
        self.remove(point, tangent_line)
        
        # Reset positions
        point.move_to(np.array([start_x, func(start_x), 0]) + shift_vector)
        tangent_line.become(get_shifted_tangent_line(start_x))
        
        # Add updaters
        def point_updater(mob, t):
            x_val = start_x + t * (2.5 - start_x)
            y_val = func(x_val)
            mob.move_to(np.array([x_val, y_val, 0]) + shift_vector)
            
        def tangent_updater(mob, t):
            x_val = start_x + t * (2.5 - start_x)
            mob.become(get_shifted_tangent_line(x_val))
            
        point.add_updater(point_updater)
        tangent_line.add_updater(tangent_updater)
        
        # Animate a dummy object to drive the time `t`?
        # Or use `self.play(point.animate, tangent_line.animate)`? No, that doesn't pass t.
        # We can use a `ValueTracker` or just `UpdateFromAlphaFunc`.
        
        # Let's use `UpdateFromAlphaFunc` on a dummy mobject or the group.
        # Actually, `UpdateFromAlphaFunc` is applied to the mobject being animated.
        # If we animate the point, we can update it based on alpha.
        
        # Remove previous updaters to be clean
        point.clear_updaters()
        tangent_line.clear_updaters()
        
        # Define updaters that take alpha
        def point_updater_alpha(mob, alpha):
            x_val = start_x + alpha * (2.5 - start_x)
            y_val = func(x_val)
            mob.move_to(np.array([x_val, y_val, 0]) + shift_vector)
            
        def tangent_updater_alpha(mob, alpha):
            x_val = start_x + alpha * (2.5 - start_x)
            mob.become(get_shifted_tangent_line(x_val))
            
        self.play(
            UpdateFromAlphaFunc(point, point_updater_alpha),
            UpdateFromAlphaFunc(tangent_line, tangent_updater_alpha),
            run_time=4.0
        )
        
        # Clear updaters after animation
        point.clear_updaters()
        tangent_line.clear_updaters()
        
        # === Animation for Lecture Line 3 ===
        # "Slope changes at every single point."
        self.lecture[2].set_color(POINT_COLOR)
        
        # As the point moves, the tangent line rotates to maintain tangency.
        # This is already demonstrated by the previous animation.
        # We can add a pause or a subtle emphasis.
        # Let's add a brief pause to let the viewer observe the rotation.
        self.wait(1.0)
        
        # === Animation for Lecture Line 4 ===
        # "We need a formula for any x."
        self.lecture[3].set_color(WHITE)
        
        # Highlight the tangent line with a flashing effect when it becomes horizontal (slope 0) and steep (high slope).
        # Slope is 0 at x=0 (vertex of the parabola-like part? No, f'(x)=1.5x^2-2. f'(x)=0 when x^2=4/1.5=8/3, x=sqrt(8/3) approx 1.63).
        # Wait, f(x) = 0.5(x^3 - 4x). f'(x) = 1.5x^2 - 2.
        # f'(x) = 0 => x^2 = 2/1.5 = 4/3 => x = +/- 1.15.
        # Let's find the local max/min.
        # f'(x) = 0 at x = sqrt(4/3) and x = -sqrt(4/3).
        # Let's highlight these points.
        
        # We can create a flashing effect by changing the color or opacity.
        # Let's animate the tangent line color to flash when it's near horizontal.
        
        # Define a function to check if slope is near 0 or high.
        # High slope is at the ends, x=-2.5 and x=2.5.
        
        # Let's do a specific animation for the "horizontal" case.
        # Move the point to x = sqrt(4/3) approx 1.15.
        x_horiz = np.sqrt(4/3)
        
        # Move point to horizontal position
        point.move_to(np.array([x_horiz, func(x_horiz), 0]) + shift_vector)
        tangent_line.become(get_shifted_tangent_line(x_horiz))
        
        # Flash the tangent line
        self.play(
            tangent_line.animate.set_color(YELLOW),
            run_time=0.3
        )
        self.play(
            tangent_line.animate.set_color(TANGENT_COLOR),
            run_time=0.3
        )
        self.play(
            tangent_line.animate.set_color(YELLOW),
            run_time=0.3
        )
        
        # Now move to a steep point, e.g., x = 2.5
        x_steep = 2.5
        point.move_to(np.array([x_steep, func(x_steep), 0]) + shift_vector)
        tangent_line.become(get_shifted_tangent_line(x_steep))
        
        # Flash the tangent line
        self.play(
            tangent_line.animate.set_color(YELLOW),
            run_time=0.3
        )
        self.play(
            tangent_line.animate.set_color(TANGENT_COLOR),
            run_time=0.3
        )
        
        # === Animation for Lecture Line 5 ===
        # "Think of it as track steepness."
        self.lecture[4].set_color(TEXT_COLOR)
        
        # Fade out the curve and tangent.
        self.play(
            FadeOut(curve),
            FadeOut(point),
            FadeOut(tangent_line),
            run_time=1.5
        )
        
        # Display text 'Slope Function' (color #FFFFFF) in center, pulsing gently.
        slope_text = Text("Slope Function", font_size=48, color=TEXT_COLOR)
        # Place it in the center of the grid area
        # Center of grid is roughly (4, 0)
        slope_text.move_to(np.array([4, 0, 0]))
        
        self.play(FadeIn(slope_text), run_time=1.0)
        
        # Pulsing effect
        self.play(
            slope_text.animate.scale(1.1),
            run_time=0.5
        )
        self.play(
            slope_text.animate.scale(1.0),
            run_time=0.5
        )
        self.play(
            slope_text.animate.scale(1.1),
            run_time=0.5
        )
        
        self.wait(2.0)