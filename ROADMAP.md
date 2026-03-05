# Kanji Terminal — Product Roadmap

## Vision

A focused kanji drilling tool optimized for iPad handwriting practice. The core interaction is simple: see a kanji, write it, get feedback. Everything else is context that makes that loop more effective.

---

## Current State

A canvas-based drawing surface with audio sonification. Good rough draft — the scratchpad works but it dominates the screen at a scale that feels unnatural for handwriting on iPad.

---

## Phase 1 — Core Terminal Layout

**Goal:** Establish the foundational layout with the highest-value information panels.

### Scratchpad resize
- Shrink the canvas to ~1/3 of screen, centered
- Natural handwriting scale, not full-bleed
- Frees up real estate on all four sides

### Top bar — Reading + Meaning
- Display the kanji's hiragana reading(s)
- Display the English meaning(s)
- Always visible — this is the reference the user checks after writing
- Multiple readings (e.g. on'yomi vs kun'yomi) should both be shown

### Bottom bar — Example sentence
- Show the kanji used in a real sentence
- Consider: reveal after the user attempts writing (so it doesn't give away meaning)
- Alternatively: always visible as context, not a hint
- Decision TBD based on how the drill loop feels in practice

---

## Phase 2 — Deck & Navigation

**Goal:** Make it possible to drill a set of kanji, not just one at a time.

- Kanji deck / queue (ordered list to work through)
- Next / previous navigation
- Progress indicator (e.g. 4/30 kanji in session)
- Curriculum integration: tie decks to known vocab/lesson data (Genki lessons, JLPT level, etc.)

---

## Phase 3 — Right Panel (Deferred)

**Goal:** Quick kanji selection for on-the-fly drilling.

The selection logic is the open question here. Options ranked by utility:
1. **Visually similar kanji** — highest leverage; drilling confused pairs (己/已/巳, 末/未, 土/士) directly targets the most common errors
2. **By radical/component** — good for building systematic component knowledge
3. **By JLPT level** — decent fallback if similarity data isn't available
4. **Random from deck** — least useful on its own

Recommendation: wait until there's real usage data on which kanji are being confused before building this. It's most useful when informed by mistakes.

---

## Phase 4 — Left Panel (Deferred)

**Goal:** Show vocab words that use this kanji, filtered to what the user knows.

The critical constraint: without curriculum awareness, this panel is half-noise. Showing 日照り alongside 日本 when the user only knows Genki L3 vocab is counterproductive.

Prerequisites before building:
- Vocab knowledge base (e.g. from the `vocab/vocab_*.csv` files in the parent Japanese workspace)
- Filtering logic: only surface words where all kanji in the word are known
- Fallback for kanji with no known-vocab usage

When ready, this panel answers "where have I seen this kanji before?" — a powerful memory anchor.

---

## Open Questions

- **Drill loop:** Is the scratchpad for production (write from memory) or recognition (see and copy)? This affects minimum canvas size and whether stroke-order guides are needed.
- **Sentence reveal timing:** Always visible vs. revealed after attempt?
- **Correctness feedback:** How is the drawn kanji evaluated? OCR? Self-report? Currently audio only — is that sufficient?
- **Session structure:** Timed sessions, fixed-count decks, or free exploration?
