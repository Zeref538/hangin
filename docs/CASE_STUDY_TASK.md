# Task: add a case-study page - Hangin' - Philippine air-quality forecasting

Paste this file's path into a fresh Claude Code session opened in this folder,
or say "follow docs/CASE_STUDY_TASK.md". It adds a case-study page in John's
shared design, then cleans up the project.

## Where the page goes

**Add the page at `web/public/case-study.html`.** The app is a Vite
React build deployed on Vercel, and files in `public/` are copied as-is, so it
will be served at `/case-study.html`. **Check `vercel.json` first:** a catch-all
rewrite would send that URL to the React app instead. Confirm with the built
`dist/` and on the preview deploy.

## The story this page tells

**A forecast that beats "the air stays the same" at every horizon.**
The backtest covers 5 Philippine metros, about 1.9 years, with a chronological
holdout. Lead with the per-horizon table: model error, baseline error, lift.

## Where the facts are

`README.md`, `data/backtest.json` (written by `python ml/train.py`), `ml/`.

## Traps specific to this project

- **FIX FIRST: the README gives three different sizes for the same win.**
  Line 13 says ~9-10% at 12-24h, the table says +23.0% (12h) and +15.6% (24h),
  and line 25 says +12-20% at 6-24h. `data/backtest.json` decides which is true.
  Make every place agree before writing a single number on the page.
- **It gives health advice.** The page and the app say in the interface that
  this is not medical advice.
- `web/node_modules` and `web/dist` are rebuildable. They are not project files.

## Read these first, fully, before changing anything

1. `C:\Users\johna\OneDrive\Documents\Portfolio\BRAND.md` - the spec, including
   the "Tried and rejected" list.
2. `C:\Users\johna\OneDrive\Documents\Portfolio\LiitLLM\docs\template.html` -
   the reference build.
3. Live reference: https://zeref538.github.io/liitllm/
4. This project's README and every file named under "Where the facts are" above.

## Part 1: the page

- Copy LiitLLM's `template.html` structure, CSS and scripts, then fill it with
  THIS project's content. Do not redesign from scratch and do not bring back
  anything on the rejected list.
- Copy the `fonts` folder (Schibsted Grotesk, Newsreader, Sora and the OFL
  licence files) and `docs/img/john.jpg` from LiitLLM, into the folder the
  page is served from.
- **Every number, chart and claim must come from this project's own files.**
  Do not invent results. If a LiitLLM section has no match here, drop it. If
  this project has something LiitLLM lacks, fit it into the same card style.
- **Charts are generated, not typed.** Build each figure with a committed script
  that reads committed result files, so re-running the script rebuilds it.
- Pick ONE project colour (not clay, and not a colour another project's page
  already uses - check BRAND.md). Use it wherever LiitLLM uses `--clay`, and run
  the dataviz palette validator on light and dark before using it. Add it to
  BRAND.md's colour table.
- The hero card fits one laptop screen (1366x768). The contents rail numbers
  match the number of sections.
- Keep the Simple / Technical toggle, and write both versions of every text.
- No em dashes anywhere in the copy.
- Link the page from the README (near the top) and from the live app if the app
  has a footer or about area.

## Part 2: clean up what is no longer used

- **Tracked files:** find scripts, configs, notes, old results and assets that
  nothing references any more. Grep for every file name before calling it
  unused. Remove them with `git rm` in their own commit, so they stay
  recoverable from history. Keep anything the README, tests, notebooks or
  pipeline still point to.
- **Page code:** remove CSS rules and JS for classes and ids that no longer
  appear in the HTML. Check `git diff` afterwards to confirm only dead rules went.
- **Junk:** `__pycache__`, `.pytest_cache`, old logs, your own screenshots and
  preview pages.
- **Big untracked files** (checkpoints, datasets, staging or upload folders): do
  NOT delete them yourself. List each one with its size, say whether it is safe
  to delete and why (rebuildable? a backup copy? the only copy?), and give John
  the exact PowerShell commands to delete the safe ones. He runs them.
- After cleanup, run the tests and rebuild the app and the page to prove
  nothing broke.

## Before saying it is done

- Screenshots at 1440x900, 1366x768, 768px and 390px, in light and dark.
- No sideways scroll (`scrollWidth` equals window width) and no console errors.
- **The live app still works** - load it locally and use its main feature once.
- Give John a localhost link to preview.
- Commit locally. Do NOT push until John says "push".
- Then run the `audit-site` skill; its model case-study list (items 75-86)
  applies to this page even though no language model is involved.
