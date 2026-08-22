"""LLM client factory.

Supports Groq (default — fast, generous free tier, good for a take-home
assignment) or OpenAI, chosen via LLM_PROVIDER in .env. Swapping providers
never touches node logic since every node calls get_llm() and uses the
standard LangChain chat-model interface (.invoke).
"""
from functools import lru_cache
from src import config


@lru_cache
def get_llm(temperature: float = 0.0):
    if config.LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq

        if not config.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
        return ChatGroq(
            model=config.LLM_MODEL,
            temperature=temperature,
            api_key=config.GROQ_API_KEY,
        )

    if config.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        return ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=temperature,
            api_key=config.OPENAI_API_KEY,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER!r}")
