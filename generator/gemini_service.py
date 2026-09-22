"""
Gemini Service — Centralized GA Client for Gemini 3 Models.
Standardized on gemini-3.5-flash with resilient GA fallbacks (gemini-3.1-flash-lite, gemini-3.8-flash),
multi-key rotation, daily quota tracking, and strict Thought Signature Circulation.
"""
import json
import re
import time
import logging
from typing import Optional, List, Dict

from google import genai
from google.genai import types

import quota_tracker
from config import GEMINI_API_KEY, GEMINI_API_KEYS, GEMINI_MODEL, GEMINI_FALLBACK_MODELS

logger = logging.getLogger("gemini_service")


class GeminiService:
    """
    Production-grade client for Google Gemini 3 GA models.
    Supports key rotation, model fallback on 503/429, exponential backoff,
    and Thought Signature Circulation across multi-turn sessions.
    """

    def __init__(self):
        self.api_keys = GEMINI_API_KEYS if GEMINI_API_KEYS else ([GEMINI_API_KEY] if GEMINI_API_KEY else [])
        if not self.api_keys:
            raise ValueError("No Gemini API keys configured. Set GEMINI_API_KEY in .env.")
        
        self.current_key_idx = 0
        self.default_model = GEMINI_MODEL or "gemini-3.5-flash"
        self.fallback_models = GEMINI_FALLBACK_MODELS or [self.default_model, "gemini-3.1-flash-lite", "gemini-3.8-flash"]
        self._clients: Dict[str, genai.Client] = {}

    def _get_client(self, key_idx: Optional[int] = None) -> genai.Client:
        """Retrieve or instantiate a genai.Client for the given key index."""
        if key_idx is None:
            key_idx = self.current_key_idx
        api_key = self.api_keys[key_idx]
        if api_key not in self._clients:
            self._clients[api_key] = genai.Client(api_key=api_key)
        return self._clients[api_key]

    def _rotate_key(self):
        """Rotate to next available API key in the pool."""
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            print(f"   ⏳ Gemini key rate-limited. Switching to backup key #{self.current_key_idx + 1}/{len(self.api_keys)}...")
        else:
            print("   ⏳ Rate limit hit on single key. Sleeping 60s...")
            time.sleep(60)

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        retries: int = 4,
    ) -> str:
        """Generate raw text response with automatic key rotation, model fallback, and backoff."""
        target_models = ([model] + [m for m in self.fallback_models if m != model]) if model else self.fallback_models
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        for attempt in range(retries):
            for mod in target_models:
                try:
                    quota_tracker.increment()
                    client = self._get_client()
                    response = client.models.generate_content(
                        model=mod,
                        contents=prompt,
                        config=config
                    )
                    return response.text or ""
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in type(e).__name__:
                        self._rotate_key()
                        time.sleep(2)
                        continue
                    elif "503" in err_str or "UNAVAILABLE" in err_str:
                        print(f"   ⚠️ Model '{mod}' busy (503). Trying next fallback...")
                        continue
                    else:
                        print(f"   ⚠️ Gemini error on '{mod}': {e}")
                        time.sleep(2)
            if attempt < retries - 1:
                sleep_sec = 3 * (attempt + 1)
                print(f"   ⏳ All models busy. Backing off for {sleep_sec}s before retry #{attempt + 2}...")
                time.sleep(sleep_sec)
        return ""

    def generate_json(
        self,
        prompt: str,
        required_keys: Optional[List[str]] = None,
        retries: int = 4,
        model: Optional[str] = None,
    ) -> dict:
        """
        Generate structured JSON response, stripping markdown fences and validating keys.
        Falls back across models on 503 or repeated failures with exponential backoff.
        """
        target_models = ([model] + [m for m in self.fallback_models if m != model]) if model else self.fallback_models
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        for attempt in range(retries):
            for mod in target_models:
                try:
                    quota_tracker.increment()
                    client = self._get_client()
                    response = client.models.generate_content(
                        model=mod,
                        contents=prompt,
                        config=config
                    )
                    raw_text = response.text or ""
                    clean_text = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
                    clean_text = re.sub(r"^```\s*", "", clean_text)
                    clean_text = re.sub(r"\s*```$", "", clean_text).strip()
                    
                    try:
                        data = json.loads(clean_text)
                    except json.JSONDecodeError:
                        # Extract the first valid JSON object / array if trailing extra data exists
                        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", clean_text)
                        if match:
                            decoder = json.JSONDecoder()
                            data, _ = decoder.raw_decode(match.group(0))
                        else:
                            raise
                    if required_keys:
                        missing = [k for k in required_keys if k not in data]
                        if missing:
                            raise ValueError(f"Missing required keys in JSON: {missing}")
                    return data
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in type(e).__name__:
                        self._rotate_key()
                        time.sleep(2)
                        continue
                    elif "503" in err_str or "UNAVAILABLE" in err_str:
                        print(f"   ⚠️ Model '{mod}' returned 503 high-demand. Trying next fallback...")
                        continue
                    else:
                        print(f"   ⚠️ Error on '{mod}': {e}")
                        time.sleep(2)
            if attempt < retries - 1:
                sleep_sec = 3 * (attempt + 1)
                print(f"   ⏳ All models busy. Backing off for {sleep_sec}s before retry #{attempt + 2}...")
                time.sleep(sleep_sec)
        return {}

    def create_conversation(self, model: Optional[str] = None) -> "GeminiConversation":
        """Start a multi-turn conversation with strict Thought Signature Circulation."""
        return GeminiConversation(self, model=model or self.default_model)


class GeminiConversation:
    """
    Multi-turn conversation session with explicit Thought Signature Circulation.
    Preserves encrypted thinking tokens (thought_signature) across turns so
    Gemini 3 models maintain their full reasoning capabilities without HTTP 400 errors.
    """

    def __init__(self, service: GeminiService, model: str):
        self.service = service
        self.model = model
        self.contents: List[types.Content] = []
        self.last_thought_signature: Optional[bytes] = None

    def send_message(self, user_prompt: str, retries: int = 4) -> str:
        """
        Send a message in the conversation, circulating the prior model
        candidate content (including its thought signature) back to the model.
        Supports model fallback in case primary model hits 503.
        """
        # Append user turn to history
        self.contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)]
            )
        )

        models_to_try = [self.model] + [m for m in self.service.fallback_models if m != self.model]
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        for attempt in range(retries):
            for mod in models_to_try:
                try:
                    quota_tracker.increment()
                    client = self.service._get_client()

                    response = client.models.generate_content(
                        model=mod,
                        contents=self.contents,
                        config=config
                    )

                    if not response.candidates:
                        raise RuntimeError("Gemini returned empty candidate response.")

                    candidate_content = response.candidates[0].content
                    
                    # Capture and verify thought signature
                    self.last_thought_signature = None
                    for part in candidate_content.parts:
                        sig = getattr(part, "thought_signature", None)
                        if sig:
                            self.last_thought_signature = sig
                            break

                    # CRITICAL THOUGHT SIGNATURE CIRCULATION:
                    # Echo the full candidate content (with its thought_signature bytes)
                    # directly into self.contents for subsequent turns.
                    self.contents.append(candidate_content)
                    return response.text or ""

                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in type(e).__name__:
                        self.service._rotate_key()
                        time.sleep(2)
                        continue
                    elif "503" in err_str or "UNAVAILABLE" in err_str:
                        print(f"   ⚠️ Conversation turn on '{mod}' hit 503. Trying next fallback...")
                        continue
                    else:
                        print(f"   ⚠️ Conversation turn error: {e}")
                        time.sleep(2)

            if attempt < retries - 1:
                sleep_sec = 3 * (attempt + 1)
                print(f"   ⏳ All conversation models busy. Backing off for {sleep_sec}s before retry #{attempt + 2}...")
                time.sleep(sleep_sec)

        # In case all models failed, roll back the pending user turn
        if self.contents and self.contents[-1].role == "user":
            self.contents.pop()
        raise RuntimeError(f"Failed to generate conversation response after trying models: {models_to_try}")

    def send_json_message(self, user_prompt: str, required_keys: Optional[List[str]] = None) -> dict:
        """Send message in conversation and parse/validate JSON response with circulated thought signature."""
        raw_text = self.send_message(user_prompt)
        clean_text = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
        clean_text = re.sub(r"^```\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text).strip()
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", clean_text)
            if match:
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(match.group(0))
            else:
                raise
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                raise ValueError(f"Missing required keys in JSON turn: {missing}")
        return data


# Global singleton instance
gemini_service = GeminiService()
