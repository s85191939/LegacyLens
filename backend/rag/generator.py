"""LLM answer generation with citations and code understanding features."""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from openai import AsyncOpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a legacy code analyst for COBOL and C systems.

Rules:
1. Cite files and lines as: File: <path> | Lines: <start>-<end>
2. Keep answers concise and precise
3. Base claims only on retrieved snippets
4. If context is insufficient, say so clearly"""


FEATURE_PROMPTS = {
    "explain": """Explain what this code does in plain English. Break down the logic step by step.
Focus on:
- What is the purpose of this code?
- What are the inputs and outputs?
- What business logic or algorithms does it implement?""",

    "dependencies": """Analyze the dependencies in this code:
- What other modules/paragraphs/functions does it call? (PERFORM, CALL, COPY, #include)
- What data does it read or modify?
- What is the call chain / data flow?
Show the dependency relationships clearly.""",

    "patterns": """Find and explain code patterns in the retrieved snippets:
- Are there repeated patterns or idioms?
- Common error handling approaches?
- Data processing patterns?
- Similar structures across different files?""",

    "documentation": """Generate documentation for this code:
- Purpose and description
- Parameters/inputs
- Return values/outputs
- Side effects
- Usage examples
Format as clear documentation comments.""",

    "business_logic": """Identify and explain the business logic in this code:
- What business rules are encoded?
- What calculations or validations are performed?
- What domain-specific operations happen?
- How does this relate to real-world business processes?""",
}


class Generator:
    """LLM-powered answer generation with OpenRouter fallback."""

    def __init__(self):
        settings = get_settings()
        self.model = settings.llm_model
        self.fast_model = settings.llm_model_fast
        self.max_tokens = settings.llm_max_tokens
        self.fast_max_tokens = settings.llm_fast_max_tokens

        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

        self.openrouter_api_key = settings.openrouter_api_key
        self.openrouter_model = settings.openrouter_model
        self.openrouter_base_url = settings.openrouter_base_url
        self.openrouter_client = None

        if self.openrouter_api_key:
            self.openrouter_client = AsyncOpenAI(
                api_key=self.openrouter_api_key,
                base_url=self.openrouter_base_url,
            )

    def _should_fallback(self, exc: Exception) -> bool:
        """Fallback on provider throttling/quota/provider errors."""
        text = str(exc).lower()
        fallback_signals = [
            "rate limit",
            "429",
            "quota",
            "insufficient_quota",
            "too many requests",
            "temporarily unavailable",
            "overloaded",
            "upstream",
        ]
        return any(signal in text for signal in fallback_signals)

    async def generate_answer(
        self,
        query: str,
        context: str,
        sources: List[Dict[str, Any]],
        feature: Optional[str] = None,
        stream: bool = False,
        fast_mode: bool = False,
    ) -> Union[str, AsyncGenerator[str, None]]:
        feature_instruction = ""
        if feature and feature in FEATURE_PROMPTS:
            feature_instruction = f"\n\nAdditional instruction: {FEATURE_PROMPTS[feature]}"

        answer_style = "Give a concise answer in 5-10 bullet points." if fast_mode else "Provide a comprehensive answer."

        user_message = f"""Question: {query}{feature_instruction}

Retrieved Code Context:
{context}

Source files referenced:
{self._format_source_list(sources)}

{answer_style} Always include specific file and line references."""

        if fast_mode:
            fast_answer = self._fast_extractive_answer(query=query, sources=sources)
            if stream:
                async def quick_stream():
                    yield fast_answer
                return quick_stream()
            return fast_answer

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        if stream:
            return self._stream_response(messages, fast_mode=fast_mode)
        return await self._complete_response(messages, fast_mode=fast_mode)

    async def _complete_response(self, messages: list, fast_mode: bool = False) -> str:
        """Generate complete response with OpenRouter fallback."""
        model = self.fast_model if fast_mode else self.model
        max_tokens = self.fast_max_tokens if fast_mode else self.max_tokens
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as exc:
            if self.openrouter_client and self._should_fallback(exc):
                logger.warning("OpenAI failed (%s). Falling back to OpenRouter.", exc)
                response = await self.openrouter_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content
            raise

    async def _stream_response(self, messages: list, fast_mode: bool = False) -> AsyncGenerator[str, None]:
        """Generate streaming response with OpenRouter fallback."""
        model = self.fast_model if fast_mode else self.model
        max_tokens = self.fast_max_tokens if fast_mode else self.max_tokens
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as exc:
            if not (self.openrouter_client and self._should_fallback(exc)):
                raise

            logger.warning("OpenAI stream failed (%s). Falling back to OpenRouter stream.", exc)
            stream = await self.openrouter_client.chat.completions.create(
                model=self.openrouter_model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    def _fast_extractive_answer(self, query: str, sources: List[Dict[str, Any]]) -> str:
        """Low-latency extractive answer for performance mode."""
        if not sources:
            return "No relevant code found for this query."

        lines = [
            f"Fast summary for: {query}",
            "",
            "Most relevant locations:",
        ]

        for idx, src in enumerate(sources[:3], 1):
            content = (src.get("content") or "").strip().replace("\n", " ")
            snippet = content[:180] + ("..." if len(content) > 180 else "")
            lines.append(
                f"{idx}. File: {src.get('file_path')} | Lines: {src.get('start_line')}-{src.get('end_line')}"
            )
            if snippet:
                lines.append(f"   Snippet: {snippet}")

        lines.append("")
        lines.append("Use full mode (stream=true or fast_mode=false) for deeper explanation.")
        return "\n".join(lines)

    def _format_source_list(self, sources: List[Dict[str, Any]]) -> str:
        lines = []
        for i, src in enumerate(sources, 1):
            line = f"{i}. File: {src['file_path']} | Lines: {src['start_line']}-{src['end_line']}"
            if src.get("name"):
                line += f" | {src['chunk_type'].title()}: {src['name']}"
            line += f" (relevance: {src['score']:.2%})"
            lines.append(line)
        return "\n".join(lines)
