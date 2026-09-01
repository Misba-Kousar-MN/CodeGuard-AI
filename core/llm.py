import os
import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

T = TypeVar("T", bound=BaseModel)

def resolve_server_side_key() -> str:
    """
    Resolves Gemini API Key server-side in precedence order:
    1. st.secrets["GEMINI_API_KEY"] or st.secrets["AI_agent"]
    2. os.getenv("GEMINI_API_KEY")
    3. os.getenv("AI_agent")
    4. ""
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
                return str(st.secrets["GEMINI_API_KEY"]).strip()
            if "AI_agent" in st.secrets and st.secrets["AI_agent"]:
                return str(st.secrets["AI_agent"]).strip()
    except Exception:
        pass

    key = os.getenv("GEMINI_API_KEY", "") or os.getenv("AI_agent", "")
    return key.strip() if key else ""


class GeminiLLMProvider:
    """
    LLM Provider Abstraction using the official Google GenAI SDK (google-genai).
    Handles API configuration, structured Pydantic outputs, and fallback mode.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = resolve_server_side_key()
            
        # Model precedence: parameter -> st.secrets -> os.getenv -> default
        model_secret = ""
        try:
            import streamlit as st
            if hasattr(st, "secrets") and st.secrets and "GEMINI_MODEL" in st.secrets:
                model_secret = str(st.secrets["GEMINI_MODEL"]).strip()
        except Exception:
            pass

        self.model = model or model_secret or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self._client = None

        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(timeout=15000)
                )
            except Exception as e:
                print(f"[GeminiLLMProvider] Warning: Failed to initialize GenAI client: {e}")
                self._client = None

    def is_available(self) -> bool:
        """Check if Gemini API key and client are configured."""
        return self._client is not None and bool(self.api_key.strip())

    def _clean_json_string(self, text: str) -> str:
        """Strips markdown code fences and cleans response text for JSON parsing."""
        if not text:
            return ""
        cleaned = text.strip()
        if "```json" in cleaned:
            parts = cleaned.split("```json")
            if len(parts) > 1:
                cleaned = parts[1].split("```")[0].strip()
        elif "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) > 1:
                cleaned = parts[1].split("```")[0].strip()

        # If still not starting with '{' or '[', attempt to extract JSON object
        if not cleaned.startswith("{") and not cleaned.startswith("[") and "{" in cleaned:
            first_brace = cleaned.find("{")
            last_brace = cleaned.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                cleaned = cleaned[first_brace:last_brace + 1].strip()
        return cleaned

    def generate_structured(self, prompt: str, schema_class: Type[T], system_instruction: Optional[str] = None) -> Optional[T]:
        """
        Generate a structured Pydantic model output using Gemini's JSON schema capability.
        Strict 15s timeout, maximum 1 retry on transient errors, fast failure fallback.
        """
        if not self.is_available():
            return None

        import time
        from google.genai import types

        max_retries = 1  # Maximum 1 automatic retry
        for attempt in range(max_retries + 1):
            try:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_class,
                    temperature=0.1,
                    max_output_tokens=8192,
                )
                if system_instruction:
                    config.system_instruction = system_instruction

                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                if not response or not response.text:
                    raise ValueError("Empty response received from Gemini API.")

                cleaned_text = self._clean_json_string(response.text)

                # Direct Pydantic model validation
                try:
                    return schema_class.model_validate_json(cleaned_text)
                except Exception:
                    data = json.loads(cleaned_text)
                    return schema_class.model_validate(data)

            except Exception as e:
                err_str = str(e)
                if attempt < max_retries:
                    print(f"[GeminiLLMProvider] Transient error for {schema_class.__name__} ({err_str[:80]}), retrying once...")
                    time.sleep(1.0)
                    continue

                print(f"[GeminiLLMProvider] Stage [{schema_class.__name__}] failed gracefully: {err_str[:120]}")
                try:
                    if 'response' in locals() and response and response.text:
                        cleaned_text = self._clean_json_string(response.text)
                        data = json.loads(cleaned_text)
                        return schema_class.model_validate(data)
                except Exception:
                    pass
                return None
        return None

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate freeform text response with strict timeout."""
        if not self.is_available():
            return "AI Analysis Unavailable: GEMINI_API_KEY is not configured."

        from google.genai import types

        try:
            config = types.GenerateContentConfig(temperature=0.2)
            if system_instruction:
                config.system_instruction = system_instruction

            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            return response.text if response and response.text else ""
        except Exception as e:
            return f"API Error: {str(e)}"
