"""
Automated Test Suite for Gemini 3 GA Migration & Thought Signature Circulation.
Validates:
1. Target GA Model: gemini-3.5-flash single-turn structured JSON generation.
2. Thought Signature Circulation: Multi-turn reasoning token capture, byte verification, and verbatim circulation.
3. Model Fallback Chain: Resilient routing across gemini-3.5-flash, gemini-3.1-flash-lite, and gemini-3.8-flash.
4. Researcher Module: generator.researcher._call_gemini compatibility.
5. Script Generator Module: generator.script._call_gemini_for_script validation.
6. Autonomous Character Director: StoryDirector script generation and refinement with circulated reasoning.
"""
import sys
import unittest
from typing import Dict, Any

from generator.gemini_service import gemini_service, GeminiService
from generator.researcher import _call_gemini
from generator.script import _call_gemini_for_script
from experiments.autonomous_character_pipeline import StoryDirector


class TestGeminiMigration(unittest.TestCase):

    def test_01_gemini_35_flash_json_generation(self):
        """Verify primary target model gemini-3.5-flash generates valid structured JSON."""
        prompt = (
            "You are a test evaluator. Respond with a JSON object containing "
            "keys: 'status' (string 'success'), 'model' (string 'gemini-3.5-flash'), 'code' (integer 200)."
        )
        res = gemini_service.generate_json(
            prompt,
            required_keys=["status", "model", "code"],
            model="gemini-3.5-flash"
        )
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("code"), 200)
        print("   ✅ Test 1 Passed: gemini-3.5-flash generated structured JSON.")

    def test_02_thought_signature_circulation_multiturn(self):
        """
        Verify Thought Signature Circulation:
        - Turn 1: Capture encrypted thought_signature bytes from response candidate.
        - Turn 2: Echo prior turn with thought signature verbatim.
        - Verify model maintains unbroken reasoning context without HTTP 400 errors.
        """
        conv = gemini_service.create_conversation(model="gemini-3.5-flash")

        # Turn 1: Complex deduction
        t1_prompt = (
            "A safe has a 3-digit code. "
            "Clue 1: All digits are distinct prime numbers less than 10. "
            "Clue 2: The sum of the digits is 15. "
            "Clue 3: The digits are in strictly ascending order. "
            "Deduce the code step-by-step and state it clearly."
        )
        t1_response = conv.send_message(t1_prompt)
        self.assertTrue(len(t1_response) > 0)
        
        # Verify thought signature was captured
        sig = conv.last_thought_signature
        self.assertIsNotNone(sig, "Thought signature MUST be present in Gemini 3 model response parts.")
        self.assertIsInstance(sig, bytes)
        self.assertTrue(len(sig) > 50, f"Thought signature bytes too short: {len(sig)}")
        print(f"   🧠 Turn 1 Thought Signature Captured: {len(sig)} bytes.")

        # Turn 2: Follow-up relying on Turn 1 deduction with circulated signature
        t2_prompt = "What was the second digit in that code? Answer with only the digit."
        t2_response = conv.send_message(t2_prompt)
        self.assertTrue(len(t2_response) > 0)
        # For primes < 10 (2,3,5,7): sum=15 -> 3+5+7 = 15. Ascending: 3, 5, 7. Second digit = 5.
        self.assertIn("5", t2_response)
        self.assertEqual(len(conv.contents), 4, "Conversation history must have 4 turns (User, Model, User, Model).")
        print(f"   ✅ Test 2 Passed: Thought signature circulated successfully. Turn 2 resolved correctly: '{t2_response.strip()}'.")

    def test_03_model_fallback_resiliency(self):
        """Verify automatic failover when a model encounters high demand or error."""
        # Create a custom service instance with an invalid primary model to test fallback
        test_service = GeminiService()
        test_service.fallback_models = ["gemini-nonexistent-model", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
        
        res = test_service.generate_json(
            "Return JSON with key 'fallback_working' equal to true.",
            required_keys=["fallback_working"]
        )
        self.assertTrue(res.get("fallback_working") is True)
        print("   ✅ Test 3 Passed: Automatic fallback handled simulated primary model failure seamlessly.")

    def test_04_researcher_module_compatibility(self):
        """Verify generator.researcher._call_gemini works with modern gemini_service."""
        prompt = (
            "Evaluate topic potential. Return a JSON object with: "
            "'topic': 'Quantum Computing Breakthrough', 'score': 95, 'category': 'technology'."
        )
        data = _call_gemini(prompt)
        self.assertIsInstance(data, dict)
        self.assertIn("topic", data)
        self.assertIn("score", data)
        print(f"   ✅ Test 4 Passed: researcher._call_gemini returned: {data.get('topic')} (Score: {data.get('score')})")

    def test_05_script_generator_module_compatibility(self):
        """Verify generator.script._call_gemini_for_script works with required_keys validation."""
        prompt = (
            "Write a test short script. Return a JSON object with: "
            "'title': 'The Speed of Light Secret', 'hook': 'What if light could stop completely?', 'duration_sec': 50."
        )
        data = _call_gemini_for_script(prompt, required_keys=["title", "hook", "duration_sec"])
        self.assertIsNotNone(data)
        self.assertEqual(data.get("title"), "The Speed of Light Secret")
        print(f"   ✅ Test 5 Passed: script._call_gemini_for_script validated required keys successfully.")

    def test_06_story_director_script_generation_and_refinement(self):
        """Verify autonomous character StoryDirector generates and refines script using circulated thought signatures."""
        director = StoryDirector()
        char_info = {
            "name": "Alex",
            "role": "Curious Tech Explorer",
            "style_tags": "cinematic, 8k, photorealistic",
            "face_prompt": "charismatic young adult male creator with dark short hair and expressive eyes",
            "body_prompt": "wearing a dark grey crewneck sweater in an ambient LED lit studio desk"
        }
        
        script = director.generate_script(char_info, topic="How lasers can trap atoms in mid-air")
        self.assertIn("title", script)
        self.assertIn("scenes", script)
        self.assertTrue(len(script["scenes"]) >= 2)
        print(f"   🎬 Director Script generated: '{script['title']}' ({len(script['scenes'])} scenes)")

        # Test script refinement with circulated thought signature
        refined = director.refine_script("Make the opening hook even more suspenseful.")
        self.assertIn("title", refined)
        self.assertIn("scenes", refined)
        print(f"   ✅ Test 6 Passed: StoryDirector generated and refined script with circulated thought signature.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
