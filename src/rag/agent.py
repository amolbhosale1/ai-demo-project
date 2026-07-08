"""Pydantic AI RAG agent with retrieval tool and role guardrails."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from rag.config import Settings, get_settings
from rag.models import RAGAnswer
from rag.privacy.redactor import Redactor
from rag.retriever import Retriever


@dataclass
class RAGDeps:
    retriever: Retriever
    role: str
    redactor: Redactor


SYSTEM_PROMPT = """\
You are a company information assistant for HR policy and workforce analytics.

Rules:
1. Answer ONLY using the context returned by the search_company_knowledge tool.
2. If the context does not contain the answer, say "I don't know".
3. Do not invent employee names, salaries, or performance details.
4. When the caller role is "employee":
   - Answer HR policy questions freely.
   - Prefer aggregate / department / location facts.
   - Refuse requests for individual salary, performance, or satisfaction details.
   Say you are not authorized and suggest contacting HR.
5. When the caller role is "hr_admin" or "dpo", you may answer individual workforce
   queries when the retrieved context supports them.
6. Never claim raw personal names if the context only shows Employee-XXXXXXXX tokens.
7. Cite which source files you relied on when possible.
"""


def build_agent(settings: Settings | None = None) -> Agent[RAGDeps, RAGAnswer]:
    settings = settings or get_settings()
    model = OpenAIChatModel(
        settings.ollama_llm_model,
        provider=OpenAIProvider(
            base_url=settings.ollama_openai_base_url,
            api_key="ollama",  # Ollama ignores the key but the client requires one
        ),
    )
    agent: Agent[RAGDeps, RAGAnswer] = Agent(
        model,
        deps_type=RAGDeps,
        output_type=RAGAnswer,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.tool
    async def search_company_knowledge(ctx: RunContext[RAGDeps], query: str) -> str:
        """Search the company knowledge base for relevant HR policy and workforce context."""
        hits = ctx.deps.retriever.search(query, role=ctx.deps.role)
        return ctx.deps.retriever.format_context(hits)

    return agent


def answer_question(
    question: str,
    role: str | None = None,
    settings: Settings | None = None,
) -> RAGAnswer:
    """Run a single RAG query synchronously."""
    settings = settings or get_settings()
    role = role or settings.rag_default_role
    redactor = Redactor(role=role, sensitivity=settings.gdpr_sensitivity)  # type: ignore[arg-type]

    if redactor.should_refuse_individual_sensitive(question) and role == "employee":
        return RAGAnswer(
            answer=(
                "I am not authorized to answer individual salary or performance "
                "questions in the employee role. Please contact HR or use --role hr_admin "
                "if you have the appropriate clearance."
            ),
            sources=[],
            redactions_applied=False,
        )

    agent = build_agent(settings)
    deps = RAGDeps(
        retriever=Retriever(settings=settings),
        role=role,
        redactor=redactor,
    )
    result = agent.run_sync(
        f"Caller role: {role}\n\nQuestion: {question}",
        deps=deps,
    )
    answer = result.output
    redacted_text, applied = redactor.redact_answer(answer.answer)
    return RAGAnswer(
        answer=redacted_text,
        sources=answer.sources,
        redactions_applied=answer.redactions_applied or applied,
    )
