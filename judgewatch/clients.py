"""Judge clients: Anthropic, OpenAI-compatible endpoints, and a deterministic mock.

Judges run with their provider defaults (no temperature or thinking overrides),
so the audit measures the configuration people actually deploy.
"""

import hashlib
import os

import httpx


class JudgeError(Exception):
    """A judge call failed at the transport or API level."""


class AnthropicJudge:
    provider = "anthropic"

    def __init__(self, model: str, max_tokens: int = 2048):
        import anthropic

        self._errors = anthropic.APIError
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except self._errors as exc:
            raise JudgeError(str(exc)) from exc
        return "".join(b.text for b in response.content if b.type == "text")


class OpenAICompatJudge:
    """Any /chat/completions endpoint: OpenAI, OpenRouter, Together, local servers."""

    provider = "openai-compatible"

    def __init__(
        self,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        max_tokens: int = 2048,
    ):
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise JudgeError(f"{api_key_env} is not set")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"] or ""
        except httpx.HTTPError as exc:
            raise JudgeError(str(exc)) from exc


class MockJudge:
    """Deterministic offline judge for tests and local dry runs."""

    provider = "mock"
    model = "mock-judge"

    def complete(self, prompt: str) -> str:
        digest = int(hashlib.md5(prompt.encode()).hexdigest(), 16)
        if '"verdict"' in prompt:
            return '{"verdict": "%s"}' % ("A" if digest % 10 < 6 else "B")
        return '{"score": %d}' % (digest % 10 + 1)


def judge_from_spec(spec: dict):
    provider = spec.get("provider", "anthropic")
    if provider == "anthropic":
        return AnthropicJudge(spec["model"], max_tokens=spec.get("max_tokens", 2048))
    if provider in ("openai", "openai-compatible"):
        return OpenAICompatJudge(
            spec["model"],
            base_url=spec.get("base_url", "https://api.openai.com/v1"),
            api_key_env=spec.get("api_key_env", "OPENAI_API_KEY"),
            max_tokens=spec.get("max_tokens", 2048),
        )
    if provider == "mock":
        return MockJudge()
    raise JudgeError(f"Unknown provider: {provider}")
