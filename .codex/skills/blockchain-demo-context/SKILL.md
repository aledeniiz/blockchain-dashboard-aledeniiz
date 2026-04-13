---
noteId: "c7fce511377f11f192639138078f7c84"
tags: []
name: "blockchain-demo-context"
description: "Use when working on this blockchain-demo repository, especially for teaching-flow updates, new educational modules, classroom-mode changes, cryptography explanations, signed transaction flows, mempool/block mining scenarios, address derivation, or UTXO-based examples. Helps preserve the repo's educational architecture, simplified-vs-accurate teaching model, and existing module map."

---

# Blockchain Demo Context

Use this skill when modifying or extending this repository.

## Start Here

Read [project-context.md](references/project-context.md) before making substantial changes.

Then inspect only the files directly related to the task.

## Repo Pattern

Most features are implemented as:

- one Pug page in `views/`
- navigation entry in `views/layout.pug`
- page-local script inside the Pug template
- styles added to `public/stylesheets/blockchain.css`

Prefer following that pattern unless the task clearly benefits from extracting reusable code.

## Teaching Model

Preserve the distinction between:

- simplified pedagogical explanations for first contact
- more accurate blockchain mechanics introduced later

Examples already used in the repo:

- address derived from public key
- ledger shows addresses, not names
- signatures prove authorization
- UTXO validation proves spendability

Do not collapse these layers into one confusing explanation.

## When Adding New Educational Pages

1. Keep the page focused on one conceptual progression.
2. Show intermediate states, not only final outputs.
3. Prefer visible validation steps over abstract text.
4. Add the page to both the menu and the homepage when it is a first-class teaching module.
5. Reuse the existing visual language from the modernized pages rather than old Bootstrap-only layouts.

## Classroom Mode Guidance

Current classroom mode is an in-memory MVP.

- shared state lives in `lib/classroom-store.js`
- routes live in `routes/index.js`
- it uses SSE, not a database-backed realtime layer

Avoid treating it like production infrastructure unless the user explicitly asks for that upgrade.

## Validation

After changing pages, render the affected Pug views through Express.

Typical quick check:

```powershell
@'
const app = require('./app');
app.render('index', { page: 'index', __: (s) => s }, (err) => {
  if (err) { console.error(err.message); process.exit(1); }
  console.log('ok');
});
'@ | node -
```

For multi-page work, render each affected view similarly.

