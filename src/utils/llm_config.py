"""
LLM Configuration - Claude AI and Ollama Support

Supports both Claude API (Anthropic) and local Ollama models.
Claude provides better performance but has API costs.
Ollama is free but runs locally and requires more resources.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class LLMConfig:
    """Configuration for LLM (Claude or Ollama)."""
    
    # LLM Provider Selection
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "claude" or "ollama"
    
    # Claude Configuration
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    CLAUDE_TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
    CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))
    
    # Ollama Configuration (fallback)
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    
    @staticmethod
    def get_llm(provider: Optional[str] = None, temperature: Optional[float] = None):
        """
        Get configured LLM instance based on provider.
        
        Args:
            provider: "claude" or "ollama" (default: from .env or "ollama")
            temperature: Sampling temperature (default: from .env or 0.7)
            
        Returns:
            LLM instance (Claude or Ollama)
        """
        provider = provider or LLMConfig.LLM_PROVIDER
        
        if provider.lower() == "claude":
            return LLMConfig._get_claude(temperature)
        elif provider.lower() == "ollama":
            return LLMConfig._get_ollama(temperature)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}. Use 'claude' or 'ollama'")
    
    @staticmethod
    def _get_claude(temperature: Optional[float] = None):
        """Get Claude AI instance."""
        from langchain_anthropic import ChatAnthropic
        
        if not LLMConfig.CLAUDE_API_KEY:
            raise ValueError(
                "CLAUDE_API_KEY not found in environment variables.\n"
                "Please add it to your .env file:\n"
                "  CLAUDE_API_KEY=your_api_key_here\n\n"
                "Get your API key at: https://console.anthropic.com/"
            )
        
        llm = ChatAnthropic(
            model=LLMConfig.CLAUDE_MODEL,
            anthropic_api_key=LLMConfig.CLAUDE_API_KEY,
            temperature=temperature or LLMConfig.CLAUDE_TEMPERATURE,
            max_tokens=LLMConfig.CLAUDE_MAX_TOKENS
        )
        
        print(f"Using Claude AI: {LLMConfig.CLAUDE_MODEL}")
        return llm
    
    @staticmethod
    def _get_ollama(temperature: Optional[float] = None):
        """Get Ollama instance."""
        from langchain_community.llms import Ollama

        try:
            llm = Ollama(
                model=LLMConfig.OLLAMA_MODEL,
                temperature=temperature or LLMConfig.OLLAMA_TEMPERATURE
            )

            print(f"Using Ollama: {LLMConfig.OLLAMA_MODEL}")
            return llm
        except Exception as e:
            raise RuntimeError(LLMConfig._ollama_error(e))

    @staticmethod
    def get_chat_llm(provider: Optional[str] = None, temperature: Optional[float] = None):
        """Get a ChatModel instance (required for LangChain agents/tool calling).

        Args:
            provider: "claude" or "ollama" (default: from .env)
            temperature: Sampling temperature

        Returns:
            ChatModel instance
        """
        provider = provider or LLMConfig.LLM_PROVIDER

        if provider.lower() == "claude":
            return LLMConfig._get_claude(temperature)
        elif provider.lower() == "ollama":
            return LLMConfig._get_chat_ollama(temperature)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}. Use 'claude' or 'ollama'")

    @staticmethod
    def _get_chat_ollama(temperature: Optional[float] = None):
        """Get ChatOllama instance (ChatModel, supports tool calling)."""
        from langchain_ollama import ChatOllama

        try:
            llm = ChatOllama(
                model=LLMConfig.OLLAMA_MODEL,
                temperature=temperature or LLMConfig.OLLAMA_TEMPERATURE
            )

            print(f"Using ChatOllama: {LLMConfig.OLLAMA_MODEL}")
            return llm
        except Exception as e:
            raise RuntimeError(LLMConfig._ollama_error(e))

    @staticmethod
    def _ollama_error(e):
        return (
            f"\nFailed to connect to Ollama: {e}\n\n"
            "Troubleshooting steps:\n"
            "1. Make sure Ollama is installed:\n"
            "   - Windows: Download from https://ollama.com/download\n"
            "   - Mac/Linux: curl -fsSL https://ollama.com/install.sh | sh\n"
            "2. Check if Ollama is running:\n"
            "   - Windows: Look for Ollama icon in system tray\n"
            "   - Or run: ollama serve\n"
            "3. Download the model: ollama pull llama3.1\n"
            "4. Test it works: ollama run llama3.1\n"
            "5. If still failing, restart PowerShell/Terminal\n\n"
            "See docs/OLLAMA_SETUP.md for detailed instructions."
        )


def test_llm():
    """Test LLM connection."""
    print("="*60)
    print("TESTING LLM CONNECTION")
    print("="*60)
    
    try:
        llm = LLMConfig.get_llm()
        
        # Test with a simple query
        print("\nSending test query to LLM...")
        
        if LLMConfig.LLM_PROVIDER == "claude":
            # Claude uses messages format
            from langchain_core.messages import HumanMessage
            response = llm.invoke([HumanMessage(content="Say 'LLM is working!' if you can read this.")])
            print(f"\nLLM Response: {response.content}")
        else:
            # Ollama uses text format
            response = llm.invoke("Say 'LLM is working!' if you can read this.")
            print(f"\nLLM Response: {response}")
        
        print("\nLLM connection successful!")
        return True
        
    except Exception as e:
        print(f"\nLLM connection failed: {e}")
        return False


def print_setup_instructions():
    """Print setup instructions based on chosen provider."""
    print("\n" + "="*60)
    print("LLM SETUP INSTRUCTIONS")
    print("="*60)
    
    provider = LLMConfig.LLM_PROVIDER
    
    if provider == "claude":
        print("\nCLAUDE AI (Current Selection)")
        print("-" * 60)
        print("\nPros:")
        print("  + Best performance and quality")
        print("  + No local resources needed")
        print("  + Fast responses")
        print("  + Better reasoning capabilities")
        
        print("\nCons:")
        print("  - API costs (but there's a free tier)")
        print("  - Requires internet connection")
        
        print("\nSetup:")
        print("  1. Get API key: https://console.anthropic.com/")
        print("  2. Add to .env file:")
        print("     CLAUDE_API_KEY=your_api_key_here")
        print("     LLM_PROVIDER=claude")
        
        print("\nCost:")
        print("  - Free tier: $5 credit (good for ~1000 requests)")
        print("  - After that: ~$0.003 per request (very affordable)")
        
        if not LLMConfig.CLAUDE_API_KEY:
            print("\n[WARNING] CLAUDE_API_KEY not set - please add to .env file")
        else:
            print("\n[OK] CLAUDE_API_KEY configured")
    
    else:  # ollama
        print("\nOLLAMA (Current Selection)")
        print("-" * 60)
        print("\nPros:")
        print("  + Completely free")
        print("  + No API costs")
        print("  + Runs offline")
        print("  + Data stays on your machine")
        
        print("\nCons:")
        print("  - Requires 8GB+ RAM")
        print("  - Slower responses")
        print("  - Lower quality than Claude")
        
        print("\nSetup:")
        print("  Mac/Linux:")
        print("    1. Install: curl -fsSL https://ollama.com/install.sh | sh")
        print("    2. Download model: ollama pull llama3.1")
        print("  Windows:")
        print("    1. Download from: https://ollama.com/download")
        print("    2. Run OllamaSetup.exe installer")
        print("    3. Restart PowerShell, then: ollama pull llama3.1")
        print("  .env configuration:")
        print("    LLM_PROVIDER=ollama")
        print("    OLLAMA_MODEL=llama3.1")
    
    print("\n" + "="*60)
    print("TO SWITCH PROVIDERS:")
    print("="*60)
    print("\nEdit your .env file and change:")
    print("  LLM_PROVIDER=claude    # For Claude AI")
    print("  LLM_PROVIDER=ollama    # For Ollama")
    print("="*60)


if __name__ == "__main__":
    print_setup_instructions()
    print("\n")
    test_llm()