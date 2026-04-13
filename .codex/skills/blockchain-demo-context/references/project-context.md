---
noteId: "c7fcbe00377f11f192639138078f7c84"
tags: []

---

# Project Context

## What This Project Is

An educational blockchain demo for classroom use, built on Express + Pug.

It now includes:

- classic blockchain concept demos
- cryptography and signatures demos
- integrated signed-transaction/block scenarios
- UTXO teaching flow
- classroom-mode multiuser MVP

## Core Files

- `views/layout.pug`: main navigation and app shell
- `views/index.pug`: homepage and teaching catalogue
- `routes/index.js`: page routes and classroom API endpoints
- `lib/classroom-store.js`: in-memory classroom state
- `public/javascripts/blockchain.js`: shared mining/hash/Merkle helpers
- `public/stylesheets/blockchain.css`: all global and page styles

## Important Educational Modules

### Signatures and identity

- `keys`
- `signatures`
- `transaction`
- `signedblock`
- `utxo`

These pages should be treated as a connected teaching sequence.

### Economic / network intuition

- `mempool`
- `coinbase`
- `attack51`
- `distributed`

### Blockchain structure

- `hash`
- `block`
- `blockchain`
- `bitcoinblock`
- `theory`

## Conceptual Accuracy Rules

### Acceptable simplification

For introductory teaching, it is acceptable to say:

- a public address is derived from the public key
- the ledger shows addresses rather than names
- transactions are signed by the sender

### Accuracy upgrade

When the lesson goes deeper, make clear that:

- Bitcoin uses UTXOs rather than account balances
- a transaction consumes previous outputs
- the unlocking data reveals public key + signature
- the node checks both authorization and spendability

## Design Rules

- Keep didactic structure stronger than decorative styling.
- Prefer one strong explanation flow per page.
- Use callouts, step cards and status outputs to show process.
- Avoid homepage or page layouts where panels compete for attention without clear hierarchy.

## Multiuser Context

Classroom mode currently supports:

- teacher creates room
- student joins with code
- shared mempool
- shared chain
- mine/reset/inject traffic actions

It does not yet provide:

- persistence
- formal authentication
- analytics
- production-safe horizontal scaling

## Good Future Directions

- connect cryptography labs into classroom mode
- add UTXO or signed-transaction multiplayer scenarios
- extract large inline scripts from templates
- split oversized CSS into page-specific files if the repo keeps growing

