#!/usr/bin/env python3
"""Turn rough plain text into clean markdown, then into whatever the next tool reads.

Usage:
    python3 text_to_md.py rough.txt                      # writes rough.md
    python3 text_to_md.py rough.txt --chapters chapters  # also one markdown file per chapter
    python3 text_to_md.py rough.txt --html               # also rough.html (one <h1> per chapter)
    python3 text_to_md.py rough.md --chapters chapters   # after fixing rough.md by hand

"Rough text" means a plain .txt file: a Project Gutenberg download, an OCR dump, text pasted
out of a PDF. The script:
  - cuts the Project Gutenberg header and licence, if present
  - rejoins hard-wrapped lines into paragraphs and mends words hyphenated across lines
  - drops lines that hold only a page number (or, with --keep-pages, turns them into
    <a id="p123"></a> anchors, which the abridger prints after each passage)
  - finds chapter headings ("Chapter 4", "PART II", "IX.", "Preface" ...) and marks them "# "

Heading detection is a guess. Read the printed chapter list. If it is wrong, either pass
--heading with your own pattern, or open the .md, fix the "# " lines by hand, and run the
script again on the .md. A .md input is not cleaned again; it is only split or converted.

Two things it cannot know, so check for them:
  - a real hyphen at a line end ("non-" / "empirical") is closed up like a broken word
  - a page number that falls where one sentence ends and the next begins is read as a
    paragraph break, even if the paragraph in fact ran on

No packages needed beyond Python 3.
"""
import argparse, html, json, re
from pathlib import Path

NUM = r"(?:\d+|[IVXLCDM]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|" \
      r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty\S*|thirty\S*|" \
      r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)"
HEADING = re.compile(
    rf"^(?:(?:chapter|part|book|section|lecture|essay)\s+{NUM}\b.*"
    r"|[IVXLC]+\.?"
    r"|(?:preface|foreword|introduction|prologue|epilogue|conclusion|afterword|"
    r"appendix(?:\s+\S+)?|author's note|postscript)\.?"
    r"(?:\s+to\s+the\s+.+)?)$", re.I)
BREAK = "\x00pagebreak\x00"
PAGE_LINE = re.compile(r"^\s*(?:[-–—\[(]\s*)?(?:page\s+)?(\d{1,4})(?:\s*[-–—\])])?\s*$", re.I)


def strip_gutenberg(t):
    m = re.search(r"\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", t, re.S)
    if m:
        t = t[m.end():]
    m = re.search(r"\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG", t)
    return t[:m.start()] if m else t


def paragraphs(t, keep_pages):
    """Split rough text into paragraphs, one string each."""
    t = t.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n").replace("﻿", "")
    lines = [ln.rstrip() for ln in t.split("\n")]
    body = [ln for ln in lines if ln.strip()]
    if not body:
        return []
    blank_share = 1 - len(body) / len(lines)
    widths = sorted(len(ln) for ln in body)
    typical = widths[int(len(widths) * 0.8)]
    if blank_share < 0.02 and typical > 200:          # one paragraph per line
        lines = [x for ln in lines for x in (ln, "")]
    elif blank_share < 0.02:                          # wrapped, paragraphs shown by indent only
        lines = [x for ln in lines for x in (("", ln) if re.match(r"^(?:\t| {2,})\S", ln) else (ln,))]

    out, cur = [], []

    def flush():
        if cur:
            p = cur[0]
            for ln in cur[1:]:
                if re.search(r"[A-Za-z]{2}-$", p) and re.match(r"[a-z]", ln):
                    p = p[:-1] + ln               # mend a word hyphenated across lines
                else:
                    p += " " + ln
            out.append(re.sub(r"\s+", " ", p).strip())
            cur.clear()

    for ln in lines:
        s = ln.strip()
        m = PAGE_LINE.match(s) if s else None
        if m:                                     # a line holding only a page number
            flush()
            out.append(f'<a id="p{m.group(1)}"></a>' if keep_pages else BREAK)
            continue
        if not s:
            flush()
        else:
            cur.append(s)
    flush()
    # A page break joins the paragraph after it. If the paragraph before it stops mid-sentence
    # and the next one starts in lower case, the page break fell inside one paragraph: rejoin.
    merged, carry, broke = [], "", False
    for p in out:
        if p == BREAK or re.fullmatch(r'(?:<a id="p[^"]*"></a>)+', p):
            carry += "" if p == BREAK else p
            broke = True
        elif broke and merged and re.match(r"[a-z]", p) and not re.search(r'[.!?:]["”’)\]]*$', merged[-1]):
            if merged[-1].endswith("-") and re.search(r"[A-Za-z]{2}-$", merged[-1]):
                merged[-1] = merged[-1][:-1] + carry + p
            else:
                merged[-1] += " " + carry + p
            carry, broke = "", False
        else:
            merged.append(carry + p); carry, broke = "", False
    return merged


def to_markdown(paras, pattern):
    """Mark chapter headings with "# ". A short all-capitals line after a heading is its title."""
    md, i = [], 0
    while i < len(paras):
        p = paras[i]
        bare = re.sub(r'<a id="p[^"]*"></a>', "", p).strip()
        if len(bare) <= 90 and pattern.match(bare) and not bare.endswith((",", ";")):
            title = bare.rstrip(".")
            nxt = paras[i + 1] if i + 1 < len(paras) else ""
            if nxt and len(nxt) <= 90 and nxt.upper() == nxt and re.search(r"[A-Z]{3}", nxt) \
                    and not pattern.match(nxt):
                title += ". " + nxt.rstrip(".").title(); i += 1
            md.append("# " + title)
            anchors = "".join(re.findall(r'<a id="p[^"]*"></a>', p))
            if anchors and i + 1 < len(paras):
                paras[i + 1] = anchors + paras[i + 1]
        else:
            md.append(p)
        i += 1
    return md


def split_chapters(md):
    """[(title, [paragraphs])]. Text before the first heading becomes "Front matter"."""
    chapters = []
    for p in md:
        if p.startswith("# "):
            chapters.append((p[2:].strip(), []))
        else:
            if not chapters:
                chapters.append(("Front matter", []))
            chapters[-1][1].append(p)
    return chapters


def words(ps):
    return len(re.findall(r"[A-Za-z0-9]+", re.sub(r"<[^>]+>", "", " ".join(ps))))


def slug(s, n=40):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n].rstrip("-") or "chapter"


def md_inline_to_html(p):
    anchors = re.findall(r'<a id="p[^"]*"></a>', p)
    p = html.escape(re.sub(r'<a id="p[^"]*"></a>', "\x00", p), quote=False)
    p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
    p = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", p)
    for a in anchors:
        p = p.replace("\x00", a, 1)
    return p


def write_html(path, title, md):
    parts = ["<!DOCTYPE html>", "<html>", "<head>", '<meta charset="utf-8">',
             f"<title>{html.escape(title)}</title>", "</head>", "<body>", ""]
    for p in md:
        m = re.match(r"^(#{1,6}) (.*)$", p)
        if m:
            parts.append(f"<h{len(m.group(1))}>{md_inline_to_html(m.group(2))}</h{len(m.group(1))}>")
        elif p.startswith(">"):
            parts.append(f"<blockquote><p>{md_inline_to_html(p.lstrip('> '))}</p></blockquote>")
        else:
            parts.append(f"<p>{md_inline_to_html(p)}</p>")
    parts += ["", "</body>", "</html>", ""]
    path.write_text("\n".join(parts), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Rough plain text to clean markdown.")
    ap.add_argument("source", help="a .txt file, or a .md file already cleaned by this script")
    ap.add_argument("--chapters", metavar="DIR", help="also write one markdown file per chapter here")
    ap.add_argument("--html", action="store_true", help="also write an HTML file beside the markdown")
    ap.add_argument("--keep-pages", action="store_true", help="turn page-number lines into page anchors")
    ap.add_argument("--heading", metavar="REGEX", help="your own pattern for a chapter heading line")
    ap.add_argument("--title", help="book title for the HTML file (default: the file name)")
    a = ap.parse_args()
    src = Path(a.source)
    text = src.read_text(encoding="utf-8", errors="replace")

    if src.suffix.lower() in (".md", ".markdown"):
        md = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        md_path = src
    else:
        pattern = re.compile(a.heading, re.I) if a.heading else HEADING
        md = to_markdown(paragraphs(strip_gutenberg(text), a.keep_pages), pattern)
        md_path = src.with_suffix(".md")
        md_path.write_text("\n\n".join(md) + "\n", encoding="utf-8")
        print(f"wrote {md_path}")

    chapters = split_chapters(md)
    print(f"\n{len(chapters)} chapters found:")
    for i, (title, ps) in enumerate(chapters, 1):
        print(f"  {i:>3}. {title[:70]:<70} {words(ps):>7,} words")
    if len(chapters) <= 1:
        print("\nNo chapter headings were found. Pass --heading, or add \"# \" lines to the .md by hand.")

    if a.chapters:
        out = Path(a.chapters); out.mkdir(parents=True, exist_ok=True)
        cfg, n, width = {}, 0, max(2, len(str(len(chapters))))
        pending_part = None
        for title, ps in chapters:
            if words(ps) < 30:                      # no text of its own: a title page or a divider
                if re.match(r"(?:part|book)\b", title, re.I):
                    pending_part = title          # "Part II" becomes the next chapter's part heading
                continue
            n += 1
            name = f"{n:0{width}d}-{slug(title)}.md"
            (out / name).write_text("\n\n".join(ps) + "\n", encoding="utf-8")
            cfg[str(n)] = {"file": name, "title": title}
            if pending_part:
                cfg[str(n)]["part"] = pending_part; pending_part = None
        (out / "_chapters.json").write_text(
            json.dumps({"chapters": cfg}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwrote {n} chapter files to {out}/ and {out}/_chapters.json (paste into book.json)")

    if a.html:
        html_path = md_path.with_suffix(".html")
        write_html(html_path, a.title or md_path.stem.replace("_", " "), md)
        print(f"wrote {html_path}")


if __name__ == "__main__":
    main()
