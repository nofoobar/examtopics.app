import os
import random
from core.config import settings

os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
os.environ.setdefault("LANGFUSE_HOST", settings.LANGFUSE_HOST)

from langfuse.openai import openai


class OpenRouterClient:

    MODEL_MAP = {
        "gemini-cheap": "google/gemini-2.0-flash-001",
        "gemini":        "google/gemini-2.5-flash",
        "openai":        "openai/gpt-5-mini",
        "deepseek":      "deepseek/deepseek-v3.2",
        "claude":        "anthropic/claude-sonnet-4.5",
        "perplexity":    "perplexity/sonar-pro",
        "xai":           "x-ai/grok-4-fast",
    }

    # These models support OpenRouter's native web search options
    # (vs. the generic "exa" plugin used by others)
    NATIVE_SEARCH_PROVIDERS = {"openai", "claude", "perplexity", "xai"}

    # Pool used when model_key == "random"
    RANDOM_MODELS = ["gemini", "openai", "deepseek", "claude", "perplexity", "xai"]

    # Pool used when model_key == "web_search_models"
    WEB_SEARCH_MODELS = ["perplexity", "xai", "openai", "claude"]

    @classmethod
    def get_random_model(cls) -> str:
        """Return a random model key from the general pool."""
        return random.choice(cls.RANDOM_MODELS)

    @classmethod
    def get_web_search_model(cls) -> str:
        """Return a random model key from the web-search-capable pool."""
        return random.choice(cls.WEB_SEARCH_MODELS)

    def __init__(self):
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )

    def get_model(self, key: str) -> str:
        return self.MODEL_MAP.get(key, self.MODEL_MAP["gemini-cheap"])

    def supports_native_search(self, model_key: str) -> bool:
        return model_key in self.NATIVE_SEARCH_PROVIDERS

    def completion(
        self,
        model_key: str,  # also accepts "random" or "web_search_models" as virtual keys
        messages: list,
        temperature: float = 0.7,
        generation_name: str | None = None,
        metadata: dict | None = None,
        # web search
        enable_web_search: bool = False,
        web_search_engine: str | None = None,   # "native" | "exa" | None (auto)
        web_search_max_results: int = 5,
        web_search_context_size: str = "low",   # "low" | "medium" | "high"
    ) -> str:
        """
        Returns the text content of the first choice.
        Langfuse traces every call automatically.
        """
        # Resolve virtual model keys before anything else.
        # When a virtual key is used, also jitter temperature in [0.75, 0.99]
        # so each question gets a slightly different sampling distribution.
        if model_key == "random":
            model_key = self.get_random_model()
            temperature = round(random.uniform(0.80, 0.99), 2)
        elif model_key == "web_search_models":
            model_key = self.get_web_search_model()
            temperature = round(random.uniform(0.80, 0.99), 2)

        extra_body: dict = {}

        if enable_web_search:
            web_plugin: dict = {"id": "web"}

            if web_search_engine:
                web_plugin["engine"] = web_search_engine

            if web_search_max_results != 5:
                web_plugin["max_results"] = web_search_max_results

            extra_body["plugins"] = [web_plugin]

            # Native-search providers accept an additional context-size hint
            use_native = (
                web_search_engine == "native"
                or (web_search_engine is None and self.supports_native_search(model_key))
            )
            if use_native and web_search_context_size in ("medium", "high"):
                extra_body["web_search_options"] = {
                    "search_context_size": web_search_context_size
                }

        request_params: dict = {
            "model":       self.get_model(model_key),
            "messages":    messages,
            "temperature": temperature,
            "name":        generation_name or model_key,
            "metadata":    metadata or {},
            "extra_headers": {
                "HTTP-Referer": settings.APP_URL,
                "X-Title":      settings.APP_NAME,
            },
        }

        if extra_body:
            request_params["extra_body"] = extra_body

        response = self.client.chat.completions.create(**request_params)
        return response.choices[0].message.content


openrouter_client = OpenRouterClient()
