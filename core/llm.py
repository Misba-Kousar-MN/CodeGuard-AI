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

        self.model = model or model_secret or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[GeminiLLMProvider] Warning: Failed to initialize GenAI client: {e}")
                self._client = None

    def is_available(self) -> bool:
        """Check if Gemini API key and client are configured."""
        return self._client is not None and bool(self.api_key.strip())

    def generate_structured(self, prompt: str, schema_class: Type[T], system_instruction: Optional[str] = None) -> Optional[T]:
        """
        Generate a structured Pydantic model output using Gemini's JSON schema capability.
        """
        if not self.is_available():
            print("[GeminiLLMProvider] Gemini API is unavailable.")
            return None

        from google.genai import types

        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema_class,
                temperature=0.2,
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

            # Parse response text into Pydantic model
            return schema_class.model_validate_json(response.text)

        except Exception as e:
            print(f"[GeminiLLMProvider] Error generating structured response: {e}")
            # Fallback attempt: try raw parsing if response text exists
            try:
                if 'response' in locals() and response and response.text:
                    clean_text = response.text.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                    elif clean_text.startswith("```"):
                        clean_text = clean_text.split("```")[1].split("```")[0].strip()
                    data = json.loads(clean_text)
                    return schema_class.model_validate(data)
            except Exception as parse_err:
                print(f"[GeminiLLMProvider] Fallback parsing failed: {parse_err}")
            return None

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate freeform text response."""
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
