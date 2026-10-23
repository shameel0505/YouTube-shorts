#!/usr/bin/env python3
"""
Test Manim vector animation rendering on Mac:
Creates a 3-second silky-smooth 60fps atomic particle cascade with glowing vectors.
"""

from manim import *

config.media_embed = False
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 60
config.background_color = "#080E1E"

class AtomicCascade(Scene):
    def construct(self):
        # 1. Central Core
        core = Circle(radius=1.2, color="#00F0FF", fill_opacity=0.25, stroke_width=3)
        core_glow = Circle(radius=1.4, color="#00F0FF", fill_opacity=0.1, stroke_width=0)
        core_label = Text("PLUTONIUM-239", font="sans-serif", font_size=20, weight=BOLD, color=WHITE)
        core_group = VGroup(core_glow, core, core_label)

        # 2. Outer Beryllium Shell
        upper_shell = Arc(radius=2.2, start_angle=0.1, angle=PI - 0.2, color="#F59E0B", stroke_width=6)
        lower_shell = Arc(radius=2.2, start_angle=PI + 0.1, angle=PI - 0.2, color="#F59E0B", stroke_width=6)
        shell_group = VGroup(upper_shell, lower_shell)

        # Animate Core Creation
        self.play(FadeIn(core_group, scale=0.8), run_time=0.8)
        self.play(Create(shell_group), run_time=0.8)

        # 3. Neutron Radiation Lines
        lines = VGroup(*[
            Line(ORIGIN, 3.5 * np.array([np.cos(theta), np.sin(theta), 0]), color="#EC4899", stroke_width=2)
            for theta in np.linspace(0, 2*PI, 16, endpoint=False)
        ])
        
        # Animate Criticality Pulse
        self.play(
            core.animate.set_color("#EF4444"),
            core.animate.scale(1.1),
            Create(lines),
            run_time=0.9
        )
        self.wait(0.5)

if __name__ == "__main__":
    scene = AtomicCascade()
    scene.render()
