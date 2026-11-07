import re
from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

NOT_FOUND_TEXT = "I could not find this in the document."

CONDENSE_SYSTEM_PROMPT = (
    "Given the following chat history and a follow-up question, rephrase the follow-up question "
    "into a concise standalone question that captures the full context (e.g., replacing pronouns like 'it', 'this article', 'that law' with the specific subject). "
    "Do NOT answer the question. Return ONLY the standalone question text, nothing else."
)


def load_toc_mapping(pdf_path: str = "data/constitution_of_india.pdf") -> dict[str, str]:
    """Parse the Table of Contents from pages 3-32 of the PDF into an article -> title map."""
    mapping = {}
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        for p in range(2, min(33, len(doc))):
            text = doc[p].get_text("text")
            matches = re.findall(r"\b(\d+[A-Z]?)\.\s*\n?\s*([A-Z][^\n\.]+)\.?", text)
            for num, title in matches:
                mapping[num.upper()] = " ".join(title.split())
    except Exception:
        pass
    return mapping


class RAGPipeline:
    def __init__(self, store, llm, count_fn: Callable[[], int], top_k: int = 8, condense_llm=None):
        self.store = store
        self.llm = llm
        self.condense_llm = condense_llm or llm
        self.count_fn = count_fn
        self.top_k = top_k
        self.toc_map = load_toc_mapping()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1.5, min=1, max=10), reraise=False)
    def condense_question(self, question: str, history: list[dict]) -> str:
        """Reformulate follow-up question using chat history into a standalone query."""
        if not history:
            return question.strip()

        history_str = "\n".join(
            f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')}"
            for m in history[-6:]
        )
        prompt = (
            f"{CONDENSE_SYSTEM_PROMPT}\n\n"
            f"Chat History:\n{history_str}\n\n"
            f"Follow-up Question: {question}\n"
            "Standalone Question:"
        )
        try:
            msg = self.condense_llm.invoke(prompt)
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            cleaned = content.strip().strip('"').strip("'")
            return cleaned if cleaned else question.strip()
        except Exception:
            return question.strip()

    def retrieve_docs(self, question: str) -> list:
        """Smart multi-query retrieval that handles article lookups, strips distractor phrases, and deduplicates."""
        clean_q = re.sub(
            r"\b(?:in|of|under)?\s*(?:the\s*)?(?:indian\s*)?constitution\b",
            "",
            question,
            flags=re.I,
        ).strip()

        search_queries = []

        # 1. Check if an article number is mentioned (e.g. Article 21, Article 21A, Article 370)
        m = re.search(r"\b(?:article\s*|art\.?\s*)(\d+[a-z]?)\b", question, re.I)
        if m:
            num = m.group(1).upper()
            title = self.toc_map.get(num, "")
            search_queries.append(f"Article {num} {title}".strip())
            search_queries.append(f"{num}. {title}".strip())
        else:
            # Check if any topic in the question matches an article title
            q_lower = question.lower()
            for num, title in self.toc_map.items():
                if len(title) > 6 and title.lower() in q_lower:
                    search_queries.append(f"Article {num} {title}")
                    break

        if clean_q and clean_q not in search_queries:
            search_queries.append(clean_q)
        if question not in search_queries:
            search_queries.append(question)

        docs = []
        seen = set()
        per_query_limit = max(3, self.top_k // 2)

        for q in search_queries:
            try:
                hits = self.store.similarity_search(q, k=per_query_limit)
                for d in hits:
                    key = (d.metadata.get("page"), d.page_content[:60])
                    if key not in seen:
                        docs.append(d)
                        seen.add(key)
            except Exception:
                continue
            if len(docs) >= self.top_k:
                break

        return docs[:self.top_k]

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30), reraise=True)
    def _call_llm(self, question: str, context: str, history: list[dict] | None = None):
        # Using direct Message objects avoids template parsing errors with curly braces in PDF text
        messages = [
            SystemMessage(
                content=(
                    "You are an expert legal assistant for the Constitution of India. "
                    "Answer the user's question accurately using ONLY the context passages below. "
                    "Maintain natural conversational flow when prior conversation history is present. "
                    "Cite page numbers like (p. 12) or article numbers when referring to provisions. "
                    f"If the context completely lacks any information to answer the question, reply exactly: {NOT_FOUND_TEXT}"
                    f"\n\nContext:\n{context}"
                )
            )
        ]

        if history:
            for m in history[-6:]:
                if m.get("role") == "user":
                    messages.append(HumanMessage(content=m.get("content", "")))
                else:
                    messages.append(AIMessage(content=m.get("content", "")))

        messages.append(HumanMessage(content=question))
        return self.llm.invoke(messages)

    def generate(self, question: str, history: list[dict] | None = None) -> dict:
        try:
            hits = self.retrieve_docs(question)
        except Exception:
            hits = []

        if not hits:
            return {
                "answer": NOT_FOUND_TEXT,
                "sources": [],
                "input_tokens": 0,
                "output_tokens": 0,
            }

        context = "\n\n".join(
            f"[Page {d.metadata.get('page')}]\n{d.page_content}" for d in hits
        )
        msg = self._call_llm(question, context, history=history)
        content = msg.content if isinstance(msg.content, str) else str(msg.content)

        usage = getattr(msg, "usage_metadata", None) or {}
        resp_meta = getattr(msg, "response_metadata", {}).get("token_usage", {})
        in_tok = usage.get("input_tokens") or resp_meta.get("prompt_tokens", 0)
        out_tok = usage.get("output_tokens") or resp_meta.get("completion_tokens", 0)

        sources = []
        for d in hits:
            item = {
                "page": d.metadata.get("page"),
                "snippet": d.page_content[:200],
            }
            if "article" in d.metadata:
                item["article"] = d.metadata["article"]
            sources.append(item)

        return {
            "answer": content.strip(),
            "sources": sources,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }

    def doc_count(self) -> int:
        return self.count_fn()
