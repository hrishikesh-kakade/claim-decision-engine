"""
Policy ingestion & chunking.

Reads the supplied policy source (a real PDF, OR the zip-packaged
image+OCR-text bundle that this assignment's PDF actually is -- both are
handled) and produces a list of semantically meaningful chunks with
page number, section, subsection and a stable chunk_id, saved to
`data/policy_chunks.json`.

Design notes (why this chunking, not fixed-size windows):
  * The DEFINITIONS block is a flat list of "<Term> means ..." entries.
    We split on that pattern so each definition is one atomic, citable
    chunk (a definition is almost always the exact evidence a downstream
    agent needs -- splitting it out beats burying it inside a 1000-token
    window).
  * WHAT WE COVER / WHAT WE EXCLUDE / EXTENSIONS / CLAIMS PROCEDURE /
    STANDARD TERMS AND CONDITIONS are split on their own numbered-item
    structure (1., 2., a), b) ...), because each numbered item is a
    freestanding policy rule (a sub-limit, an exclusion, a condition)
    that should be citable on its own.
  * Repeated page headers/footers (insurer name, IRDAI reg no, page no.)
    are stripped before chunking so they don't pollute retrieval.
  * Every chunk keeps the page number(s) it was drawn from, so every
    citation traces back to `source, page, section, chunk_id`.

Run:
    python scripts/ingest_policy.py --pdf <path> --out data/policy_chunks.json
"""
from __future__ import annotations

import argparse
import io
import json
import re
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

HEADER_FOOTER_PATTERNS = [
    r"UNIVERSAL SOMPO GENERAL INSURANCE CO LTD",
    r"CSC-\s*Individual Health Insurance-?Policy Wording UNIHLIP18004V011718 IRDAI Reg No:134",
    r"^\s*\d{1,3}\s*$",  # bare page numbers on their own line
]

SECTION_HEADINGS = [
    ("PREAMBLE", r"CSC\s*[-–]\s*INDIVIDUAL HEALTH INSURANCE"),
    ("DEFINITIONS", r"^DEFINITIONS\s*$"),
    ("CRITICAL_ILLNESS_DEFINITIONS", r"^Critical Illness\s*$"),
    ("SCOPE_OF_COVER", r"^SCOPE OF COVER\s*$|^WHAT WE COVER\s*$"),
    ("EXCLUSIONS", r"^WHAT WE EXCLUDE\s*$"),
    ("EXTENSIONS", r"^EXTENSIONS\s*$"),
    ("CLAIMS_PROCEDURE", r"^CLAIMS PROCEDURE\s*$"),
    ("STANDARD_TERMS", r"^STANDARD TERMS AND CONDITIONS:?\s*$"),
    ("GRIEVANCES", r"^21\. Grievances\s*$"),
]

# A defined term line looks like: "Accident means a sudden ..." or
# "Any one illness means continuous ..." -- capitalised term (allowing
# internal capitals/spaces/hyphens/slashes) immediately followed by " means".
DEFINITION_RE = re.compile(
    r"(?m)^(?P<term>[A-Z][A-Za-z0-9 /\-\u2013\u2019']{2,60}?) means\b"
)

NUMBERED_ITEM_RE = re.compile(r"(?m)^\s*(\d{1,2})\.\s+")
LETTERED_ITEM_RE = re.compile(r"(?m)^\s*([a-hA-H])\)\s+")


@dataclass
class Chunk:
    chunk_id: str
    section: str
    subsection: Optional[str]
    page_start: int
    page_end: int
    text: str


def _load_pages_from_zip(raw: bytes) -> dict[str, str]:
    """This assignment's supplied 'PDF' is actually a zip bundle of
    per-page JPEGs + OCR .txt + manifest.json. Detect and load it."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    manifest = json.loads(z.read("manifest.json").decode("utf-8"))
    pages = {}
    for p in manifest["pages"]:
        n = p["page_number"]
        txt_path = p["text"]["path"]
        pages[str(n)] = z.read(txt_path).decode("utf-8", errors="replace")
    return pages


def _load_pages_from_real_pdf(path: Path) -> dict[str, str]:
    try:
        import pdfplumber

        pages = {}
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages[str(i)] = page.extract_text() or ""
        return pages
    except Exception:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return {str(i + 1): (p.extract_text() or "") for i, p in enumerate(reader.pages)}


def load_pages(pdf_path: Path) -> dict[str, str]:
    raw = pdf_path.read_bytes()
    if raw[:2] == b"PK":  # zip magic -- the OCR-bundle case for this assignment
        return _load_pages_from_zip(raw)
    return _load_pages_from_real_pdf(pdf_path)


def clean_page_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pat in HEADER_FOOTER_PATTERNS:
        text = re.sub(pat, "", text, flags=re.MULTILINE | re.IGNORECASE)
    # normalise stray bullet glyphs / OCR artefacts, collapse blank lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_offset_index(pages: dict[str, str]) -> tuple[str, list[tuple[int, int]]]:
    """Concatenate cleaned pages; return (full_text, [(page_num, start_offset), ...])."""
    ordered = sorted(pages.items(), key=lambda kv: int(kv[0]))
    full_parts = []
    offsets = []
    pos = 0
    for page_num, raw in ordered:
        cleaned = clean_page_text(raw)
        offsets.append((int(page_num), pos))
        full_parts.append(cleaned)
        pos += len(cleaned) + 2  # +2 for the "\n\n" join below
    full_text = "\n\n".join(full_parts)
    return full_text, offsets


def page_for_offset(offset: int, offsets: list[tuple[int, int]]) -> int:
    page = offsets[0][0]
    for page_num, start in offsets:
        if start <= offset:
            page = page_num
        else:
            break
    return page


def split_sections(full_text: str) -> list[tuple[str, int, int]]:
    """Return [(section_name, start_offset, end_offset), ...] covering full_text."""
    matches = []
    for name, pattern in SECTION_HEADINGS:
        m = re.search(pattern, full_text, flags=re.MULTILINE)
        if m:
            matches.append((m.start(), name))
    matches.sort()
    if not matches or matches[0][0] > 0:
        matches.insert(0, (0, "PREAMBLE"))
    spans = []
    for idx, (start, name) in enumerate(matches):
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(full_text)
        spans.append((name, start, end))
    return spans


def chunk_definitions(section_text: str) -> list[tuple[str, str]]:
    """Split the DEFINITIONS section into (term, definition_text) pairs."""
    matches = list(DEFINITION_RE.finditer(section_text))
    out = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        term = m.group("term").strip()
        body = section_text[start:end].strip()
        if len(body) > 20:
            out.append((term, body))
    return out


def chunk_numbered_section(section_text: str, max_chars: int = 900) -> list[tuple[Optional[str], str]]:
    """Split on top-level numbered items (1. 2. 3. ...); further split an
    over-long item on lettered sub-items; fall back to paragraph chunks."""
    matches = list(NUMBERED_ITEM_RE.finditer(section_text))
    if len(matches) < 2:
        return chunk_paragraphs(section_text, max_chars)
    out = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        body = section_text[start:end].strip()
        if not body:
            continue
        label = body.split("\n", 1)[0][:80].strip()
        if len(body) <= max_chars:
            out.append((label, body))
        else:
            for sub_label, sub_body in chunk_paragraphs(body, max_chars):
                out.append((sub_label or label, sub_body))
    return out


def chunk_paragraphs(text: str, max_chars: int = 900) -> list[tuple[Optional[str], str]]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = []
    buf = ""
    for p in paras:
        if buf and len(buf) + len(p) + 1 > max_chars:
            out.append((None, buf.strip()))
            buf = p
        else:
            buf = (buf + "\n" + p).strip() if buf else p
    if buf.strip():
        out.append((None, buf.strip()))
    return out


def ingest(pdf_path: Path) -> list[dict]:
    pages = load_pages(pdf_path)
    full_text, offsets = build_offset_index(pages)
    sections = split_sections(full_text)

    chunks: list[Chunk] = []
    counters: dict[str, int] = {}

    def add_chunk(section: str, subsection: Optional[str], text: str, start_off: int, end_off: int):
        counters[section] = counters.get(section, 0) + 1
        cid = f"{section}-{counters[section]:03d}"
        p_start = page_for_offset(start_off, offsets)
        p_end = page_for_offset(max(end_off - 1, start_off), offsets)
        chunks.append(Chunk(cid, section, subsection, p_start, p_end, text.strip()))

    for name, start, end in sections:
        section_text = full_text[start:end]
        if not section_text.strip():
            continue
        if name in ("DEFINITIONS", "CRITICAL_ILLNESS_DEFINITIONS"):
            for term, body in chunk_definitions(section_text):
                local_off = full_text.find(body, start)
                add_chunk(name, term, body, max(local_off, start), max(local_off, start) + len(body))
        elif name in ("SCOPE_OF_COVER", "EXCLUSIONS", "EXTENSIONS", "CLAIMS_PROCEDURE", "STANDARD_TERMS"):
            for label, body in chunk_numbered_section(section_text):
                local_off = full_text.find(body, start)
                add_chunk(name, label, body, max(local_off, start), max(local_off, start) + len(body))
        elif name == "GRIEVANCES":
            # Ombudsman address list -- low decision-relevance; keep as one chunk.
            add_chunk(name, "Ombudsman & grievance contacts", section_text, start, end)
        else:
            for label, body in chunk_paragraphs(section_text):
                local_off = full_text.find(body, start)
                add_chunk(name, label, body, max(local_off, start), max(local_off, start) + len(body))

    return [asdict(c) for c in chunks]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default="/mnt/project/USGIC-CSCIndividualHealthInsurance_2017-2018.pdf")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "policy_chunks.json"))
    args = ap.parse_args()

    chunks = ingest(Path(args.pdf))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(chunks)} chunks to {out_path}")
    by_section: dict[str, int] = {}
    for c in chunks:
        by_section[c["section"]] = by_section.get(c["section"], 0) + 1
    for k, v in by_section.items():
        print(f"  {k}: {v} chunks")


if __name__ == "__main__":
    main()
