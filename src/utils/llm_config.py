"""
LLM configuration — supports Ollama (local), Claude (API), and Gemini (API).

Set LLM_PROVIDER=ollama, LLM_PROVIDER=claude, or LLM_PROVIDER=gemini in your .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class LLMConfig:
    """Factory for chat LLM instances used by the agent."""

    LLM_PROVIDER  = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "llama3.1")
    OLLAMA_HOST    = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_TEMP    = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL   = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    CLAUDE_TEMP    = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
    CLAUDE_TOKENS  = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    GEMINI_TEMP    = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))

    @staticmethod
    def get_chat_llm(provider: str = None, temperature: float = None):
        """Return a ChatModel instance for tool-calling agents.

        Args:
            provider: "ollama", "claude", or "gemini" (defaults to LLM_PROVIDER env var)
            temperature: Sampling temperature (defaults to env var value)
        """
        provider = (provider or LLMConfig.LLM_PROVIDER).lower()

        if provider == "gemini":
            if not LLMConfig.GEMINI_API_KEY:
                raise ValueError(
                    "GEMINI_API_KEY not set. Add it to your .env file:\n"
                    "  GEMINI_API_KEY=your_key_here\n"
                    "Get one at https://aistudio.google.com/apikey"
                )
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=LLMConfig.GEMINI_MODEL,
                google_api_key=LLMConfig.GEMINI_API_KEY,
                temperature=temperature or LLMConfig.GEMINI_TEMP,
            )

        if provider == "claude":
            if not LLMConfig.CLAUDE_API_KEY:
                raise ValueError(
                    "CLAUDE_API_KEY not set. Add it to your .env file:\n"
                    "  CLAUDE_API_KEY=your_key_here\n"
                    "Get one at https://console.anthropic.com/"
                )
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=LLMConfig.CLAUDE_MODEL,
                anthropic_api_key=LLMConfig.CLAUDE_API_KEY,
                temperature=temperature or LLMConfig.CLAUDE_TEMP,
                max_tokens=LLMConfig.CLAUDE_TOKENS,
            )

        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=LLMConfig.OLLAMA_MODEL,
                    base_url=LLMConfig.OLLAMA_HOST,
                    temperature=temperature or LLMConfig.OLLAMA_TEMP,
                )
            except Exception as e:
                raise RuntimeError(
                    f"Could not connect to Ollama at {LLMConfig.OLLAMA_HOST}: {e}\n"
                    "Make sure Ollama is running and the model is pulled:\n"
                    f"  ollama pull {LLMConfig.OLLAMA_MODEL}"
                ) from e

        raise ValueError(f"Unknown provider '{provider}'. Use 'ollama', 'claude', or 'gemini'.")
