"""LLM answer generation with citations and code understanding features."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from openai import AsyncOpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a legacy code analyst specializing in COBOL and C codebases. You help developers understand, navigate, and maintain large legacy enterprise systems.

When answering questions about code:
1. Always reference specific files and line numbers using the format: File: <path> | Lines: <start>-<end>
2. Explain code in plain English, avoiding jargon when possible
3. Highlight important patterns, dependencies, and business logic
4. Note any potential issues or areas of concern
5. When showing code structure, explain the COBOL divisions/sections/paragraphs or C functions

You have access to retrieved code snippets from the GnuCOBOL compiler codebase. Use these snippets to provide accurate, well-cited answers.

If the retrieved context doesn't contain enough information to fully answer the question, say so clearly and suggest what additional searches might help."""


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
    """LLM-powered answer generation with code understanding features."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    async def generate_answer(
        self,
        query: str,
        context: str,
        sources: List[Dict[str, Any]],
        feature: Optional[str] = None,
        stream: bool = False,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate an answer using the LLM with retrieved context.

        Args:
            query: User's natural language query
            context: Assembled context from retrieval
            sources: Source metadata for citations
            feature: Optional code understanding feature to activate
            stream: If True, return an async generator for streaming

        Returns:
            Generated answer string, or async generator if streaming
        """
        # Build the prompt
        feature_instruction = ""
        if feature and feature in FEATURE_PROMPTS:
            feature_instruction = f"\n\nAdditional instruction: {FEATURE_PROMPTS[feature]}"

        user_message = f"""Question: {query}{feature_instruction}

Retrieved Code Context:
{context}

Source files referenced:
{self._format_source_list(sources)}

Please provide a comprehensive answer with specific file and line references."""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        if stream:
            return self._stream_response(messages)
        else:
            return await self._complete_response(messages)

    async def _complete_response(self, messages: list) -> str:
        """Generate a complete response."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    async def _stream_response(self, messages: list) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _format_source_list(self, sources: List[Dict[str, Any]]) -> str:
        """Format sources list for the prompt."""
        lines = []
        for i, src in enumerate(sources, 1):
            line = f"{i}. File: {src['file_path']} | Lines: {src['start_line']}-{src['end_line']}"
            if src.get("name"):
                line += f" | {src['chunk_type'].title()}: {src['name']}"
            line += f" (relevance: {src['score']:.2%})"
            lines.append(line)
        return "\n".join(lines)
