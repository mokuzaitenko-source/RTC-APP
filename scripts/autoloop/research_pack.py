from __future__ import annotations

from typing import Dict, List, Literal


ResearchPolicy = Literal["primary_docs", "broad_web", "local_only"]


PRIMARY_REFS: List[Dict[str, str]] = [
    {"source": "local", "ref": "docs/prompting_book.md"},
    {"source": "local", "ref": "README.md"},
    {"source": "official", "ref": "https://platform.openai.com/docs/guides/structured-outputs"},
    {"source": "official", "ref": "https://platform.openai.com/docs/guides/streaming-responses"},
    {"source": "official", "ref": "https://github.com/langchain-ai/langgraph"},
    {"source": "official", "ref": "https://github.com/microsoft/autogen"},
    {"source": "official", "ref": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"},
]


BROAD_WEB_REFS: List[Dict[str, str]] = [
    {"source": "web", "ref": "https://arxiv.org/abs/2210.03629"},
    {"source": "web", "ref": "https://arxiv.org/abs/2303.17651"},
]


def resolve_research_sources(policy: ResearchPolicy) -> List[Dict[str, str]]:
    if policy == "local_only":
        return [ref for ref in PRIMARY_REFS if ref["source"] == "local"]
    if policy == "broad_web":
        return [*PRIMARY_REFS, *BROAD_WEB_REFS]
    return PRIMARY_REFS.copy()
