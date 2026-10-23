"""
Manim Scene: The Criticality Threshold (TED-Ed Style Vector Animation).
Visualizes the exponential neutron multiplication and the 0.08mm critical gap.
"""
from manim import *
import numpy as np

class CriticalityThreshold(Scene):
    def construct(self):
        # 1. Dark aesthetic background
        self.camera.background_color = "#080D1A"

        # 2. Section Title (Modern Typography)
        title = Text("NEUTRON MULTIPLICATION FACTOR (k)", font="Helvetica", weight=BOLD)
        title.set_color(WHITE).scale(0.7).to_edge(UP, buff=0.5)

        sub_title = Text("Subcritical vs. Prompt Critical Threshold", font="Helvetica")
        sub_title.set_color("#6B82A6").scale(0.45).next_to(title, DOWN, buff=0.15)

        self.play(FadeIn(title, shift=DOWN * 0.2), FadeIn(sub_title, shift=DOWN * 0.2), run_time=1.0)

        # 3. Coordinate Axes
        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 10, 2],
            x_length=7.5,
            y_length=4.5,
            axis_config={"color": "#3A4D6B", "stroke_width": 2},
            tips=False
        ).shift(DOWN * 0.4 + LEFT * 0.8)

        x_label = Text("Dome Gap (mm) → 0", font="Helvetica").scale(0.35).set_color("#8EA8C3").next_to(axes.x_axis, DOWN, buff=0.2)
        y_label = Text("Neutron Flux (fission/sec)", font="Helvetica").scale(0.35).set_color("#8EA8C3").rotate(90 * DEGREES).next_to(axes.y_axis, LEFT, buff=0.2)

        self.play(Create(axes), Write(x_label), Write(y_label), run_time=1.2)

        # 4. Critical Threshold Horizon (Dashed Red Line)
        crit_line = DashedLine(
            start=axes.c2p(0, 7.5),
            end=axes.c2p(10, 7.5),
            color="#FF3366",
            stroke_width=2.5,
            dash_length=0.15
        )
        crit_label = Text("CRITICAL THRESHOLD (k = 1.0)", font="Helvetica", weight=BOLD)
        crit_label.scale(0.38).set_color("#FF3366").next_to(crit_line, UP, buff=0.1).to_edge(RIGHT, buff=0.8)

        self.play(Create(crit_line), FadeIn(crit_label), run_time=0.8)

        # 5. Exponential Curve Animation
        # y = 0.5 * exp(0.32 * x)
        exp_func = lambda x: 0.4 * np.exp(0.32 * x)
        curve = axes.plot(exp_func, x_range=[0, 9.2], color="#00F0FF", stroke_width=4)

        # Glowing tracker dot
        dot = Dot(color="#FFD700", radius=0.12)
        dot.move_to(axes.c2p(0, exp_func(0)))

        self.play(Create(curve), MoveAlongPath(dot, curve), run_time=2.5, rate_func=rate_functions.ease_in_cubic)

        # 6. Flash at Critical Point
        flash = Flash(dot, color="#FF0055", flash_radius=0.8, num_lines=16)
        self.play(flash, dot.animate.scale(1.8).set_color("#FF0055"), run_time=0.5)

        # 7. Final Alert Tag
        alert_box = Rectangle(width=3.6, height=1.0, color="#FF3366", fill_color="#1A0A14", fill_opacity=0.85)
        alert_box.shift(RIGHT * 3.2 + DOWN * 1.2)

        alert_text = MarkupText(
            "<span color='#FF3366'><b>FATAL EXCURSION</b></span>\n<span size='small' color='#FFFFFF'>3.0 × 10<sup>15</sup> Fissions in 0.5s</span>",
            font="Helvetica"
        ).scale(0.42).move_to(alert_box.get_center())

        self.play(FadeIn(alert_box), Write(alert_text), run_time=0.8)
        self.wait(1.0)
