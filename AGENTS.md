# Guide for an AI assistant helping with the distiller

You are an AI assistant and a person has asked you to help them condense a book with this repository. This file tells you how the tool works and where it needs a human. `README.md` covers the same ground for a human reader.

## What the tool makes

`distiller.py` takes one book and produces a single flowing summary of about 10,000 words, as an EPUB and an HTML file. The summary is a **paraphrase written by Claude**. It is not made of the author's sentences, and the tool does not check any quotation against the source. If the person needs the author's exact words, point them to the abridger instead: https://github.com/benwstevens/abridger

## What it costs and what it needs

- It calls the Anthropic API and **spends the person's money**: very roughly $4 to $8 for a 100,000-word book. The script prints an estimate and asks for confirmation before any paid call. Never answer that confirmation on the person's behalf unless they have told you to.
- It needs Python 3.10 or later, the packages in `requirements.txt`, and an API key in a `.env` file in this folder, as one line: `ANTHROPIC_API_KEY=sk-ant-...`
- **Never print, log, commit or copy the API key.** `.env` is in `.gitignore`. Leave it there.

## Choose the starting point

| The person has | Do this first |
|---|---|
| A clean EPUB | Nothing. Go to "Run". |
| An EPUB whose chapters split badly | `python3 splitready.py book.epub`, then use the `_normalized.html` it writes |
| A scanned, OCR'd PDF | `python3 papercopyprep.py scan.pdf --title "..." --author "..."`, which writes an EPUB |
| Plain text | `python3 text_to_md.py rough.txt --html`, then use the `.html` it writes |

For plain text, read the chapter list that `text_to_md.py` prints. If it is wrong, fix the `# ` heading lines in the `.md` it wrote and run `python3 text_to_md.py rough.md --html`.

## Run

Always start with a dry run. It costs nothing.

```bash
python3 distiller.py book.epub --dry-run
```

The dry run splits the book into chapters and **asks which chapters to exclude**. This prompt is interactive. Typical answers are `1-3` to drop front matter, `1-3,22` for a mix, or Enter to keep everything. The answer is saved in `books/<slug>/selected_chapters.txt` and is not asked again. If you cannot answer a prompt in your environment, give the person the command to run themselves.

Check the chapter list with the person. If chapters are merged, split in odd places, or missing, stop and use `splitready.py`.

Then the real run:

```bash
python3 distiller.py book.epub                 # default target 10,000 words
python3 distiller.py book.epub --target 5000   # a different length
```

The five stages are: detect the chapter heading tag, split into chapters, summarize each chapter, save the summaries, then run a coherence pass and assemble the EPUB and HTML.

## Where the output goes

```
books/<slug>/
  source/              # the book and its converted HTML
  chapters/            # one HTML file per chapter
  distilled_chapters/  # one summary per chapter
  output/              # the final <Title>_distilled.epub and .html
```

`<slug>` comes from the file name. A new book gets a new folder, so nothing needs deleting between books.

## If a run stops or goes wrong

| Symptom | What to do |
|---|---|
| The run was interrupted | Run the same command again. Chapters already summarized are skipped. |
| Chapter summaries exist but the final file is missing or bad | `python3 distiller.py book.epub --stage 5` redoes the coherence pass and assembly only. |
| "ANTHROPIC_API_KEY not found" | The `.env` file is missing or empty. |
| "No heading tags found", or the chapters are wrong | Use `splitready.py` and pass its `_normalized.html`. |
| A 402 or credit error | The person needs to add API credit at console.anthropic.com. |
| A model-not-found error | The model name is pinned in `distiller.py` in two places. Update both to a current Claude model. |
| The final text is only the raw chapter summaries | The coherence pass failed and the script fell back. Re-run with `--stage 5`. |
| A chapter is missing from the summary | That chapter's API call failed, and the run continued without it. Re-run the same command to retry it. |

## What you may change

- `distiller_instructions.txt` is the prompt for the per-chapter pass. `distiller_coherence_instructions.txt` is the prompt for the final pass. Edit these to change tone, emphasis or structure. The output format must stay HTML, because the assembly step expects it.
- The summary's length follows each chapter's size, not its importance. To weight a chapter differently, exclude the chapters that matter least, or adjust the prompt.

## When you report back

Tell the person: where the output files are, the final word count against the target, what the run cost if the script reported it, and any chapter that failed or was excluded. Remind them the text is a paraphrase if they plan to quote from it.
