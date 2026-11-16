# distiller: a book summarized to about 10,000 words

`distiller.py` condenses a full book into one flowing summary using the Claude API. It works in two passes: it summarizes each chapter in proportion to its length, then rewrites the summaries into a single coherent document. The output is a Kindle-compatible EPUB and a single HTML file.

The result is a paraphrase in Claude's words. For a shortened edition made only of the author's own sentences, see [abridger](https://github.com/benwstevens/abridger).

## Prerequisites

- **Python 3.10+**
- **An Anthropic API key**: sign up at [console.anthropic.com](https://console.anthropic.com) and add credits under Settings > Billing

## Setup

```bash
git clone https://github.com/benwstevens/distiller.git
cd distiller
pip3 install -r requirements.txt
```

Create a file called `.env` in the `distiller` folder with one line:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

The `.env` file is ignored by git, so the key is not uploaded.

## Usage

```bash
python3 distiller.py mybook.epub                 # run everything
python3 distiller.py mybook.epub --target 5000   # change the length (default 10,000 words)
python3 distiller.py mybook.epub --dry-run       # split chapters and show the cost estimate, no API calls
python3 distiller.py mybook.epub --stage 3       # restart from stage 3 after an interruption
```

The script shows an estimated cost and asks for confirmation before making any API calls. A 100,000-word book costs very roughly $4–8.

### The stages

1. **Detect**: find which HTML heading tag marks chapter boundaries.
2. **Split**: split the ebook into chapter files and ask which to include. Type `1-9` or `1-5,22,23` to exclude chapters, or press Enter to keep all. The choice is saved.
3. **Distill each chapter**: send each chapter to Claude with a word target.
4. **Save**: write each chapter summary to disk. Finished chapters are skipped on a re-run, so an interrupted run resumes where it stopped.
5. **Coherence pass and assembly**: rewrite the chapter summaries into one document and write the final EPUB and HTML.

### Output

```
books/
  mybook/
    source/              # original EPUB + converted HTML
    chapters/            # individual chapter HTML files
    distilled_chapters/  # per-chapter summaries
    output/              # final EPUB and HTML
```

## Prep tools

All three are optional.

### splitready.py: fix an EPUB whose chapters do not split cleanly

Some EPUBs have a messy internal structure, and stage 2 finds the wrong chapters. `splitready.py` audits the EPUB's table of contents and headings, lets you choose what to keep, and writes a `_normalized.html` file. Pass that file to the distiller in place of the EPUB.

```bash
python3 splitready.py mybook.epub
python3 splitready.py mybook.epub --audit-only   # just show the structure
python3 distiller.py mybook_normalized.html
```

### papercopyprep.py: turn a scanned book into an EPUB

Takes a searchable (OCR'd) PDF, detects chapters, cleans up OCR artifacts, and writes an EPUB.

```bash
python3 papercopyprep.py scanned.pdf --title "The Book Title" --author "Author Name"
```

If the PDF is image-only, run OCR first, for example with `ocrmypdf scanned.pdf searchable.pdf`. Check the EPUB before distilling it, since OCR quality varies.

### text_to_md.py: start from rough plain text

If all you have is plain text (a Project Gutenberg `.txt`, an OCR dump, text pasted out of a PDF), this cleans it into markdown and writes an HTML file the distiller can read:

```bash
python3 text_to_md.py rough.txt --html
python3 distiller.py rough.html
```

It rejoins hard-wrapped lines, mends words hyphenated across lines, removes the Project Gutenberg header and bare page numbers, and guesses the chapter headings. Read the chapter list it prints. If the chapters are wrong, open `rough.md`, fix the `# ` heading lines by hand, and run it again on the `.md`:

```bash
python3 text_to_md.py rough.md --html
```

## Customizing the instructions

The prompts are plain text files:

- `distiller_instructions.txt`: the per-chapter pass
- `distiller_coherence_instructions.txt`: the final coherence pass

The output must stay HTML, not Markdown, because the assembly step expects HTML.

## Known limits

- The summary is a paraphrase. Nothing checks "quotes" against the source.
- Each chapter's share of the length follows its size, not its importance.
- The model is pinned in `distiller.py` to `claude-sonnet-4-5-20250929`. Change it there to use a newer model.
- If a chapter fails, the run warns and continues without it. If the coherence pass fails, the output falls back to the raw chapter summaries.

## Files

```
distiller.py                          # the distiller
shared.py                             # EPUB conversion, chapter splitting, output helpers
distiller_instructions.txt            # prompt for the per-chapter pass
distiller_coherence_instructions.txt  # prompt for the coherence pass
splitready.py                         # EPUB structure fixer (optional prep)
papercopyprep.py                      # scanned PDF to EPUB (optional prep)
text_to_md.py                         # rough plain text to markdown and HTML (optional prep)
requirements.txt
```
