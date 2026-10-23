"""
Long-Form Showrunner & Visual Essay Architect.
Choreographs 5-Chapter Tension Arcs for prestige 16:9 widescreen documentaries
combining 3D Blender sequences, Google Flow Veo 2/3 B-roll, Host A-Roll,
and tactile multi-track sound design.
"""
import os
import json
import dataclasses
from typing import List, Dict, Any, Optional
from pathlib import Path

@dataclasses.dataclass
class SoundCue:
    sfx_type: str  # "braam", "whoosh", "riser", "click", "drone"
    delay_sec: float = 0.0
    volume_db: float = -6.0
    params: Dict[str, Any] = dataclasses.field(default_factory=dict)

@dataclasses.dataclass
class StoryboardShot:
    shot_id: str
    shot_type: str  # "blender_3d" | "flow_broll" | "host_aroll"
    duration_sec: float
    narration: str
    visual_spec: Dict[str, Any]
    sound_cues: List[SoundCue] = dataclasses.field(default_factory=list)

@dataclasses.dataclass
class Chapter:
    chapter_num: int
    title: str
    arc_role: str  # "Inciting Anomaly", "False Origin", "Deep Mechanism", "Climax Crisis", "Philosophical Horizon"
    shots: List[StoryboardShot]

class ShowrunnerDirector:
    """Orchestrates long-form documentary scripts and asset manifests."""

    def __init__(self, workspace_root: str | Path = None):
        self.workspace_root = Path(workspace_root or Path(__file__).resolve().parent.parent.parent)

    def generate_demon_core_masterpiece(self) -> Dict[str, Any]:
        """
        Builds the reference prestige 5-chapter long-form essay:
        'THE DRAGON'S TAIL: The Physics and Human Hubris of the Demon Core'
        """
        chapters = [
            # CHAPTER 1: THE INCITING ANOMALY
            Chapter(
                chapter_num=1,
                title="THE INCITING ANOMALY",
                arc_role="Inciting Anomaly",
                shots=[
                    StoryboardShot(
                        shot_id="ch01_s01_title",
                        shot_type="blender_3d",
                        duration_sec=4.0,
                        narration="In May 1946, inside a top-secret Los Alamos laboratory, eight men gathered around a six-kilogram sphere of plutonium.",
                        visual_spec={
                            "template": "kinetic_title",
                            "params": {
                                "title": "THE DRAGON'S TAIL",
                                "subtitle": "LOS ALAMOS SCIENTIFIC LABORATORY // MAY 21, 1946",
                                "color": [0.0, 0.85, 1.0]
                            },
                            "frames": 120,
                            "fps": 30,
                            "resolution": (1920, 1080)
                        },
                        sound_cues=[
                            SoundCue(sfx_type="braam", delay_sec=0.0, volume_db=-3.0, params={"base_freq": 48.0}),
                            SoundCue(sfx_type="drone", delay_sec=0.0, volume_db=-14.0, params={"root_pitch": 55.0, "duration": 20.0})
                        ]
                    ),
                    StoryboardShot(
                        shot_id="ch01_s02_host",
                        shot_type="host_aroll",
                        duration_sec=6.0,
                        narration="They called it the Demon Core. It had already killed Harry Daghlian nine months earlier. But Louis Slotin was convinced he could master it.",
                        visual_spec={
                            "aspect_ratio": "16:9",
                            "prompt": (
                                "Full-frame 16:9 widescreen image edge to edge, no bars. Medium waist-up shot at sleek minimalist timber creator desk, "
                                "Liya host wearing tailored matte charcoal overshirt over crisp crewneck with generous headroom, opens leaning forward over desk "
                                "and snaps eyeline up to the lens with an energetic hand gesture holding up one finger, speaking with sharp conviction saying: "
                                "\"They called it the Demon Core, and it had already taken one life.\", warm 3200K key light, subtle practical lamp glow, "
                                "acoustic wood panel depth, 35mm f/2.0 lens, sharp cinematic 4k."
                            )
                        },
                        sound_cues=[
                            SoundCue(sfx_type="click", delay_sec=0.2, volume_db=-12.0)
                        ]
                    ),
                    StoryboardShot(
                        shot_id="ch01_s03_archival",
                        shot_type="flow_broll",
                        duration_sec=5.0,
                        narration="Between Slotin and a lethal prompt-critical burst was a single flat-head screwdriver blade. Less than eight hundredths of a millimeter.",
                        visual_spec={
                            "aspect_ratio": "16:9",
                            "archetype": "Archetype 3: Archival Investigation & Evidence Desk",
                            "prompt": (
                                "Full-frame 16:9 widescreen image edge to edge, no bars. ARRI Alexa Mini LF with Zeiss Supreme 50mm T1.5 prime lens "
                                "on motorized linear slider gliding 2mm above: hands in white cotton archival gloves examining declassified 1946 Manhattan Project "
                                "blueprints of a split hemisphere plutonium casing, vintage brass calipers, yellowed rag paper with faded blue fountain pen ink, "
                                "warm 2800K desk lamp glow, shallow depth of field, authentic documentary archive."
                            )
                        },
                        sound_cues=[
                            SoundCue(sfx_type="whoosh", delay_sec=0.0, volume_db=-8.0)
                        ]
                    )
                ]
            ),

            # CHAPTER 2: THE FALSE ORIGIN & INTUITION
            Chapter(
                chapter_num=2,
                title="THE DANGEROUS ILLUSION",
                arc_role="False Origin",
                shots=[
                    StoryboardShot(
                        shot_id="ch02_s01_orbit",
                        shot_type="blender_3d",
                        duration_sec=4.5,
                        narration="Most people imagine a nuclear weapon as inherently explosive. But plutonium alone does not explode—it requires neutron multiplication.",
                        visual_spec={
                            "template": "orbit_system",
                            "params": {
                                "color": [0.0, 0.9, 1.0],
                                "accent_color": [1.0, 0.45, 0.1],
                                "nodes": 40
                            },
                            "frames": 135,
                            "fps": 30,
                            "resolution": (1920, 1080)
                        },
                        sound_cues=[
                            SoundCue(sfx_type="whoosh", delay_sec=0.0, volume_db=-6.0),
                            SoundCue(sfx_type="click", delay_sec=1.5, volume_db=-10.0)
                        ]
                    ),
                    StoryboardShot(
                        shot_id="ch02_s02_host",
                        shot_type="host_aroll",
                        duration_sec=6.5,
                        narration="Slotin was warned by Richard Feynman that they were tickling the tail of a sleeping dragon. Yet Slotin treated it like routine lab shop work.",
                        visual_spec={
                            "aspect_ratio": "16:9",
                            "prompt": (
                                "Full-frame 16:9 widescreen image edge to edge, no bars. Medium waist-up shot at sleek minimalist timber creator desk, "
                                "Liya host wearing tailored matte charcoal overshirt over crisp crewneck, opens with a deliberate head shake and open palms, "
                                "eyeline direct to camera, speaking with solemn gravity saying: "
                                "\"Richard Feynman begged him to stop, warning him that he was tickling the tail of a sleeping dragon.\", "
                                "warm 3200K key light, subtle practical lamp glow, acoustic wood panel depth, 35mm f/2.0 lens, sharp 4k."
                            )
                        },
                        sound_cues=[]
                    ),
                    StoryboardShot(
                        shot_id="ch02_s03_manim_vector",
                        shot_type="manim_2d",
                        duration_sec=6.0,
                        narration="As the dome gap narrowed toward zero, neutron multiplication skyrocketed along an exponential curve directly into prompt criticality.",
                        visual_spec={
                            "template": "criticality_threshold",
                            "scene_name": "CriticalityThreshold"
                        },
                        sound_cues=[
                            SoundCue(sfx_type="whoosh", delay_sec=0.0, volume_db=-7.0),
                            SoundCue(sfx_type="click", delay_sec=2.5, volume_db=-6.0)
                        ]
                    )
                ]
            ),

            # CHAPTER 3: THE DEEP MECHANISM
            Chapter(
                chapter_num=3,
                title="THE CRITICAL MECHANISM",
                arc_role="Deep Mechanism",
                shots=[
                    StoryboardShot(
                        shot_id="ch03_s01_schematic",
                        shot_type="blender_3d",
                        duration_sec=5.0,
                        narration="The geometry was devastatingly simple. A plutonium-gallium alloy sphere surrounded by two beryllium reflector domes.",
                        visual_spec={
                            "template": "schematic_wireframe",
                            "params": {
                                "title": "CRITICAL GEOMETRY",
                                "callout_top": "UPPER BERYLLIUM REFLECTOR",
                                "callout_core": "PLUTONIUM-GALLIUM CORE (6.2 KG)",
                                "callout_base": "SUB-CRITICAL LOWER CRADLE",
                                "accent_color": [0.0, 0.85, 1.0],
                                "core_color": [1.0, 0.42, 0.05]
                            },
                            "frames": 150,
                            "fps": 30,
                            "resolution": (1920, 1080)
                        },
                        sound_cues=[
                            SoundCue(sfx_type="braam", delay_sec=0.0, volume_db=-4.0, params={"base_freq": 52.0}),
                            SoundCue(sfx_type="click", delay_sec=1.8, volume_db=-8.0),
                            SoundCue(sfx_type="click", delay_sec=3.2, volume_db=-8.0)
                        ]
                    ),
                    StoryboardShot(
                        shot_id="ch03_s02_crt",
                        shot_type="flow_broll",
                        duration_sec=4.5,
                        narration="As the upper dome lowered, reflected neutrons multiplied exponentially. The Geiger counters went from rhythmic clicking into a solid shriek.",
                        visual_spec={
                            "aspect_ratio": "16:9",
                            "archetype": "Archetype 6: Tangible Physical Apparatus & Analog Evidence",
                            "prompt": (
                                "Full-frame 16:9 widescreen image edge to edge, no bars. Macro rack-focus with 50mm f/1.4 lens across an authentic 1940s analog "
                                "radiation rate meter needle wildly pinning past the red danger zone, phosphor scale glow, matte dark-gray metal chassis, "
                                "warm vintage laboratory background, dust motes dancing in side tungsten light."
                            )
                        },
                        sound_cues=[
                            SoundCue(sfx_type="click", delay_sec=0.5, volume_db=-8.0),
                            SoundCue(sfx_type="riser", delay_sec=1.0, volume_db=-6.0, params={"duration": 3.5, "end_freq": 800.0})
                        ]
                    )
                ]
            ),

            # CHAPTER 4: THE CLIMAX & CRISIS
            Chapter(
                chapter_num=4,
                title="THE SLIP",
                arc_role="Climax Crisis",
                shots=[
                    StoryboardShot(
                        shot_id="ch04_s01_macro",
                        shot_type="flow_broll",
                        duration_sec=4.0,
                        narration="At exactly 3:20 PM, Louis Slotin's screwdriver slipped two millimeters. The beryllium dome snapped shut.",
                        visual_spec={
                            "aspect_ratio": "16:9",
                            "archetype": "Archetype 2: High-Speed Lab Physics & Impact Dynamics",
                            "prompt": (
                                "Full-frame 16:9 widescreen image edge to edge, no bars. Captured on Phantom Flex 4K at 20,000 fps with Laowa 24mm f/14 macro probe lens: "
                                "a steel flathead screwdriver blade slipping against a brushed metallic hemisphere, instantaneous cold blue Cherenkov ionization flash "
                                "erupting in the micro-gap, 180-degree physical shutter motion blur, directional tungsten side spotlight, authentic high-speed laboratory capture."
                            )
                        },
                        sound_cues=[
                            SoundCue(sfx_type="braam", delay_sec=0.0, volume_db=-2.0, params={"base_freq": 40.0, "drive": 4.0}),
                            SoundCue(sfx_type="click", delay_sec=0.1, volume_db=-4.0)
                        ]
                    ),
                    StoryboardShot(
                        shot_id="ch04_s02_host",
                        shot_type="host_aroll",
                        duration_sec=6.5,
                        narration="An instant wave of heat hit his face. A blinding blue glow enveloped the room. Slotin tore the hemisphere off with his bare hands to save his colleagues.",
                        visual_spec={
                            "aspect_ratio": "16:9",
                            "prompt": (
                                "Full-frame 16:9 widescreen image edge to edge, no bars. Medium waist-up shot at sleek minimalist timber creator desk, "
                                "Liya host wearing tailored matte charcoal overshirt over crisp crewneck, leaning in intensely, hands gripping the desk edge, "
                                "speaking with urgent breathless intensity saying: "
                                "\"A blinding flash of blue Cherenkov light engulfed the room. In half a second, he received a thousand roentgens of radiation.\", "
                                "warm 3200K key light with subtle cold blue rim fill, acoustic wood panel depth, 35mm f/2.0 lens, sharp 4k."
                            )
                        },
                        sound_cues=[
                            SoundCue(sfx_type="drone", delay_sec=0.0, volume_db=-10.0, params={"root_pitch": 45.0, "duration": 10.0})
                        ]
                    )
                ]
            ),

            # CHAPTER 5: THE PHILOSOPHICAL HORIZON
            Chapter(
                chapter_num=5,
                title="THE PRICE OF ARROGANCE",
                arc_role="Philosophical Horizon",
                shots=[
                    StoryboardShot(
                        shot_id="ch05_s01_orbit_outro",
                        shot_type="blender_3d",
                        duration_sec=5.0,
                        narration="Louis Slotin died nine days later. The Demon Core was never detonated in combat. Instead, it became the foundation of modern remote-handling safety protocols.",
                        visual_spec={
                            "template": "orbit_system",
                            "params": {
                                "color": [0.3, 0.5, 0.9],
                                "accent_color": [0.9, 0.8, 0.4],
                                "nodes": 25
                            },
                            "frames": 150,
                            "fps": 30,
                            "resolution": (1920, 1080)
                        },
                        sound_cues=[
                            SoundCue(sfx_type="whoosh", delay_sec=0.0, volume_db=-8.0),
                            SoundCue(sfx_type="drone", delay_sec=0.0, volume_db=-16.0, params={"root_pitch": 55.0, "duration": 15.0})
                        ]
                    ),
                    StoryboardShot(
                        shot_id="ch05_s02_host_final",
                        shot_type="host_aroll",
                        duration_sec=7.0,
                        narration="We unlocked the fundamental forces of the universe before we conquered our own arrogance. And the dragon's tail remembers.",
                        visual_spec={
                            "aspect_ratio": "16:9",
                            "prompt": (
                                "Full-frame 16:9 widescreen image edge to edge, no bars. Medium waist-up shot at sleek minimalist timber creator desk, "
                                "Liya host wearing tailored matte charcoal overshirt over crisp crewneck, seated back with poised restraint, "
                                "direct steady eye contact with the viewer, delivering the closing thought with measured resonance saying: "
                                "\"We unlocked the fundamental forces of the cosmos long before we learned how to govern our own hubris.\", "
                                "warm 3200K key light, subtle practical lamp glow, acoustic wood panel depth, 35mm f/2.0 lens, sharp 4k."
                            )
                        },
                        sound_cues=[
                            SoundCue(sfx_type="braam", delay_sec=4.5, volume_db=-4.0, params={"base_freq": 44.0})
                        ]
                    )
                ]
            )
        ]

        storyboard_dict = {
            "title": "THE DRAGON'S TAIL: The Physics and Human Hubris of the Demon Core",
            "format": "16:9 Widescreen Documentary",
            "narrative_framework": "5-Chapter Tension Arc (Anti-Slop Standard)",
            "total_chapters": len(chapters),
            "chapters": [
                {
                    "chapter_num": ch.chapter_num,
                    "title": ch.title,
                    "arc_role": ch.arc_role,
                    "shots": [dataclasses.asdict(s) for s in ch.shots]
                }
                for ch in chapters
            ]
        }

        out_path = self.workspace_root / "output" / "longform" / "demon_core_storyboard.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(storyboard_dict, f, indent=2)

        print(f"🎬 [Showrunner] 5-Chapter Long-Form Storyboard generated -> {out_path.name}")
        return storyboard_dict
