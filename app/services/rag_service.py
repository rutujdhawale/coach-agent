import re
from pathlib import Path
from typing import Dict, List


class TextbookRagService:
    """Loads pre-added textbook markdown files and retrieves relevant chunks."""

    def __init__(self, corpus_dir: str = "data/textbooks"):
        self.corpus_dir = Path(corpus_dir)
        self.chunks: List[Dict[str, str]] = []
        self._load_corpus()

    def _load_corpus(self) -> None:
        if not self.corpus_dir.exists():
            return
        for md_file in sorted(self.corpus_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            sections = re.split(r"\n##\s+", text)
            for section in sections[1:]:
                lines = [ln.strip() for ln in section.strip().splitlines() if ln.strip()]
                if not lines:
                    continue
                title = lines[0]
                topic = title
                source = md_file.name
                body_lines = []
                for ln in lines[1:]:
                    if ln.lower().startswith("topic:"):
                        topic = ln.split(":", 1)[1].strip()
                    elif ln.lower().startswith("source:"):
                        source = ln.split(":", 1)[1].strip()
                    else:
                        body_lines.append(ln)
                self.chunks.append(
                    {
                        "title": title,
                        "topic": topic,
                        "source": source,
                        "content": " ".join(body_lines),
                    }
                )

    def retrieve(self, query: str, topic: str = "", top_k: int = 3) -> List[Dict[str, str]]:
        q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        t_lower = topic.strip().lower()
        scored = []
        for chunk in self.chunks:
            if t_lower and t_lower not in chunk["topic"].lower() and t_lower not in chunk["title"].lower():
                continue
            haystack = f"{chunk['title']} {chunk['topic']} {chunk['content']}".lower()
            c_tokens = set(re.findall(r"[a-z0-9]+", haystack))
            overlap = len(q_tokens & c_tokens) if q_tokens else 1
            if overlap > 0 or t_lower:
                scored.append((overlap, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]
