# Cursor Rules Organization

This directory contains rules that guide AI assistance:

## Structure

```
.cursor/rules/
├── code-style.mdc       # Minimal, elegant code (always apply)
├── etiquette.mdc        # How to interact (suggest rules, pre-flight)
├── mistakes.mdc         # Antipatterns with BAD/GOOD examples
│
├── metacognition/       # How to think
    ├── backend.mdc      # Backend: TDD, FastAPI, async
    └── frontend.mdc     # Frontend: React, TypeScript, Tailwind
```

## Metacognition (How to Think)

**Location:** `metacognition/`

- **backend.mdc**: TDD, FastAPI/Python, error handling, async
- **frontend.mdc**: React, TypeScript, Shadcn/Tailwind, performance

## Mistakes (What to Avoid)

**Location:** `mistakes.mdc`

- Race conditions, null guards, data format consistency
- Singleton init (double-checked locking)
- Bug-fixing workflow: log → test first → fix → document

**Before any PR:** Review `mistakes.mdc`.

## Etiquette (How to Interact)

**Location:** `etiquette.mdc`

- When to suggest new rules
- Pre-flight: review `mistakes.mdc` before finalizing

## Other (Tech-Specific)

**Location:** `other/`

- **socket.io.mdc**: Real-time with Socket.IO (globs: `**/*.{js,jsx,ts,tsx}`)
- **vercel.mdc**: Deploy, env, Edge, caching (globs: `**/*`)
- **espn.mdc**: ESPN API rate limiting, server-side fetch (if used)

## Adding Rules

1. **Metacognition:** `metacognition/` — how to think about problems
2. **Mistakes:** `mistakes.mdc` — antipattern + BAD/GOOD + checklist
3. **Etiquette:** `etiquette.mdc` — interaction style
4. **Other:** `other/` — tech-specific (add `globs` in frontmatter when relevant)
