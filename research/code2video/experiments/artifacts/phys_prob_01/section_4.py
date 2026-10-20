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

class Section4Scene(TeachingScene):
    def construct(self):
        self.setup_layout("Sec 4: Real-World Application & Intuition Check", 
                          ['5 m/s squared is quick.', 
                           'Like a car accelerating fast.', 
                           'Zero to 18 km/h in one sec.', 
                           'Answer makes physical sense.', 
                           'Intuition confirms the calculation.'])
        
        # Define colors for each lecture line
        colors = [
            "#FFD700",  # Gold for line 1
            "#87CEEB",  # Sky blue for line 2
            "#98FB98",  # Pale green for line 3
            "#FFA07A",  # Light salmon for line 4
            "#DDA0DD"   # Plum for line 5
        ]
        
        # === Animation for Lecture Line 1 ===
        # "5 m/s squared is quick." - Show car and speedometer
        self.lecture[0].set_color(colors[0])
        
        # Create simple car icon (using basic shapes)
        car_body = Rectangle(width=1.2, height=0.5, color=colors[0], fill_opacity=0.8, stroke_width=2)
        car_roof = Rectangle(width=0.6, height=0.3, color=colors[0], fill_opacity=0.8, stroke_width=2)
        car_roof.next_to(car_body, UP, buff=0.05)
        wheel1 = Circle(radius=0.15, color=WHITE, fill_opacity=0.9, stroke_width=2)
        wheel2 = Circle(radius=0.15, color=WHITE, fill_opacity=0.9, stroke_width=2)
        wheel1.next_to(car_body, DOWN, buff=0.05).shift(LEFT * 0.3)
        wheel2.next_to(car_body, DOWN, buff=0.05).shift(RIGHT * 0.3)
        car = VGroup(car_body, car_roof, wheel1, wheel2)
        self.place_at_grid(car, 'B3', scale_factor=0.8)
        
        # Create speedometer gauge (simple arc with needle)
        speedo_arc = Arc(radius=0.6, start_angle=PI, angle=PI, color=WHITE, stroke_width=3)
        speedo_center = Dot(point=ORIGIN, radius=0.05, color=WHITE)
        speedo_needle = Line(ORIGIN, RIGHT * 0.5, color=RED, stroke_width=3)
        speedo_needle.rotate(PI/2)  # Start pointing up (0 position)
        speedo = VGroup(speedo_arc, speedo_center, speedo_needle)
        self.place_at_grid(speedo, 'B5', scale_factor=0.8)
        
        self.play(FadeIn(car), FadeIn(speedo), run_time=1)
        self.wait(0.5)
        
        # === Animation for Lecture Line 2 ===
        # "Like a car accelerating fast." - Speedometer needle moves
        self.lecture[1].set_color(colors[1])
        
        # Animate needle from 0 to 18 km/h position
        # 18 km/h is about 5 m/s, let's move needle to about 60 degrees from top
        target_angle = PI/2 - PI/3  # 60 degrees from vertical
        
        self.play(Rotate(speedo_needle, target_angle - PI/2, about_point=ORIGIN), run_time=1.5)
        self.wait(0.5)
        
        # Add label "18 km/h"
        speed_label = Text("18 km/h", font_size=18, color=colors[1])
        self.place_at_grid(speed_label, 'A5', scale_factor=0.8)
        self.play(FadeIn(speed_label), run_time=0.5)
        self.wait(0.5)
        
        # === Animation for Lecture Line 3 ===
        # "Zero to 18 km/h in one sec." - Timer appears
        self.lecture[2].set_color(colors[2])
        
        # Create timer icon
        timer_circle = Circle(radius=0.4, color=colors[2], stroke_width=2)
        timer_text = Text("1 second", font_size=16, color=colors[2])
        timer_text.move_to(timer_circle)
        timer = VGroup(timer_circle, timer_text)
        self.place_at_grid(timer, 'C3', scale_factor=0.8)
        
        self.play(FadeIn(timer), run_time=0.5)
        self.wait(0.5)
        
        # === Animation for Lecture Line 4 ===
        # "Answer makes physical sense." - Car moves forward, checkmark appears
        self.lecture[3].set_color(colors[3])
        
        # Move car forward
        self.play(car.animate.shift(RIGHT * 1.5), run_time=1)
        
        # Create checkmark
        checkmark = VGroup(
            Line(ORIGIN, RIGHT * 0.2 + DOWN * 0.1, color=GREEN, stroke_width=4),
            Line(RIGHT * 0.2 + DOWN * 0.1, RIGHT * 0.4 + UP * 0.2, color=GREEN, stroke_width=4)
        )
        checkmark.move_to(ORIGIN)
        check_text = Text("Reasonable? Yes", font_size=18, color=GREEN)
        check_group = VGroup(checkmark, check_text).arrange(DOWN, buff=0.2)
        self.place_at_grid(check_group, 'C5', scale_factor=0.8)
        
        self.play(FadeIn(check_group), run_time=0.5)
        self.wait(0.5)
        
        # === Animation for Lecture Line 5 ===
        # "Intuition confirms the calculation." - Final answer glows
        self.lecture[4].set_color(colors[4])
        
        # Create final answer
        final_answer = Text("a = 5 m/s²", font_size=28, color=colors[4])
        self.place_at_grid(final_answer, 'D4', scale_factor=1.0)
        
        self.play(FadeIn(final_answer), run_time=0.5)
        
        # Add glow effect by animating opacity
        final_answer_copy = final_answer.copy()
        final_answer_copy.set_opacity(0.5)
        final_answer_copy.scale(1.1)
        
        self.play(
            FadeIn(final_answer_copy),
            run_time=0.5
        )
        self.wait(1)
        
        # Clean up by removing glow
        self.play(FadeOut(final_answer_copy), run_time=0.5)
        self.wait(0.5)