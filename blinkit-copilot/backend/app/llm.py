"""Thin adapter around the Gemini SDK.

The agent loop only talks to this small interface (start / step / add_tool_results), so it can be
unit-tested with a scripted fake and swapped to another provider without touching agent code.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .config import settings


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict            # JSON-schema style, types in UPPERCASE for Gemini
    fn: Any = None              # callable(args: dict) -> str | (str, ui_dict)


@dataclass
class Call:
    name: str
    args: dict


@dataclass
class Step:
    text: str = ""
    calls: list[Call] = field(default_factory=list)
    raw: Any = None
    in_tokens: int = 0
    out_tokens: int = 0


class LLMUnavailable(Exception):
    pass


class GeminiLLM:
    def __init__(self):
        self._client = None

    @property
    def available(self) -> bool:
        return bool(settings.google_api_key)

    @property
    def client(self):
        if not self.available:
            raise LLMUnavailable("GOOGLE_API_KEY is not set. Add it to backend/.env and restart.")
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.google_api_key)
        return self._client

    # ---- conversation building ----
    def start(self, history: list[dict], question: str) -> list:
        from google.genai import types
        contents = []
        for m in history[-8:]:
            role = "user" if m.get("role") == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=str(m.get("content", ""))[:3000])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=question)]))
        return contents

    def add_tool_results(self, contents: list, step: Step, results: list[tuple[str, str]]):
        from google.genai import types
        contents.append(step.raw)
        contents.append(types.Content(role="user", parts=[
            types.Part.from_function_response(name=n, response={"result": r}) for n, r in results]))

    # ---- one model turn ----
    def step(self, contents: list, system: str, tools: list[ToolSpec] | None = None, temperature: float = 0.2) -> Step:
        from google.genai import types
        cfg = dict(system_instruction=system, temperature=temperature)
        if tools:
            cfg["tools"] = [types.Tool(function_declarations=[
                types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters)
                for t in tools])]
            cfg["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
        resp = self._with_retry(lambda: self.client.models.generate_content(
            model=settings.model, contents=contents, config=types.GenerateContentConfig(**cfg)))
        content = resp.candidates[0].content if resp.candidates else None
        parts = (content.parts or []) if content else []
        calls = [Call(p.function_call.name, dict(p.function_call.args or {})) for p in parts if p.function_call]
        text = "".join(p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False))
        u = resp.usage_metadata
        return Step(text=text.strip(), calls=calls, raw=content,
                    in_tokens=getattr(u, "prompt_token_count", 0) or 0,
                    out_tokens=getattr(u, "candidates_token_count", 0) or 0)

    def complete(self, prompt: str, system: str = "", temperature: float = 0.0) -> Step:
        from google.genai import types
        return self.step([types.Content(role="user", parts=[types.Part(text=prompt)])], system, None, temperature)

    # ---- embeddings ----
    def embed_docs(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]

    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        from google.genai import types
        out: list[list[float]] = []
        for i in range(0, len(texts), 64):
            batch = texts[i:i + 64]
            r = self._with_retry(lambda: self.client.models.embed_content(
                model=settings.embed_model, contents=batch, config=types.EmbedContentConfig(task_type=task)))
            out.extend(e.values for e in r.embeddings)
        return out

    @staticmethod
    def _with_retry(fn, tries: int = 3):
        for i in range(tries):
            try:
                return fn()
            except Exception as e:  # rate limits / transient 5xx
                msg = str(e)
                transient = any(s in msg for s in ("429", "500", "502", "503", "504", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
                if not transient or i == tries - 1:
                    raise
                time.sleep(1.5 * (2 ** i))


llm = GeminiLLM()
