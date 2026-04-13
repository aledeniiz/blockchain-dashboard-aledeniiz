---
noteId: "c7fce510377f11f192639138078f7c84"
tags: []

---

# Project Memory

## Purpose

This repository is an educational web app for teaching blockchain and cryptography concepts in class.

The goal is not only to show blockchain structure, but to help students understand:

- hashing and proof of work
- chained blocks and tamper propagation
- distributed consensus intuition
- public/private key cryptography
- digital signatures
- signed transactions
- public addresses derived from public keys
- mempool selection and mining incentives
- 51% attack intuition
- UTXO-based spending and change
- classroom-oriented multiuser interaction

## Tech Stack

- Node.js + Express
- Pug templates
- jQuery on the client
- Custom blockchain logic in `public/javascripts/blockchain.js`
- No database
- Multiuser classroom state currently stored in memory

## Important Architecture Decisions

### 1. Keep the project lightweight

The project intentionally stays simple and server-rendered. New teaching modules are usually added as:

- a new Pug page in `views/`
- optional menu entry in `views/layout.pug`
- page-local client-side script inside the template
- supporting styles in `public/stylesheets/blockchain.css`

### 2. Difficulty logic stays global

Mining difficulty is controlled in `public/javascripts/blockchain.js` via:

- `setDifficulty`
- `difficultyMajor`
- `difficultyMinor`
- `maximumNonce`
- `pattern`

Teaching pages that simulate mining reuse that shared logic.

### 3. Classroom mode is an MVP

Current classroom mode is a practical demo, not production infrastructure.

- State is in `lib/classroom-store.js`
- Realtime sync uses SSE from `routes/index.js`
- No persistence across restarts
- No formal authentication system yet

This is good enough for classroom demos but should be treated as ephemeral state.

## Current Module Map

### Core blockchain pages

- `hash`: basic SHA-256 intuition
- `block`: nonce + proof of work
- `blockchain`: chained blocks
- `distributed`: peer copies of the chain
- `tokens`: simple transaction rows inside blocks
- `coinbase`: mining reward intuition
- `bitcoinblock`: real Bitcoin block header walkthrough
- `mempool`: fee market and block selection
- `attack51`: adversarial mining intuition
- `theory`: conceptual reference page

### Cryptography pages

- `keys`: private key -> public key
- `signatures`: sign/verify generic messages
- `transaction`: sign/verify a payment-style transaction
- `signedblock`: integrated flow from address derivation to signing, verification, mempool admission and mining
- `utxo`: UTXO selection, input coverage, fee and change

### Classroom mode

- `classroom`: multiuser shared room for mempool/block activity

## Teaching Model Already Embedded

The repo now mixes two levels of explanation:

### Simplified pedagogical model

Useful for introducing concepts cleanly:

- address derived from public key
- transaction signed by sender
- node verifies before mining
- ledger shows addresses, not user names

### More accurate blockchain model

Introduced once students are ready:

- the ledger does not store balances as bank accounts
- Bitcoin spends UTXOs, not account balances
- a spend reveals public key + signature to unlock previous outputs
- a valid signature alone is not enough; referenced outputs must exist and be unspent

This distinction is intentional and should be preserved in future teaching modules.

## UI / Design Direction

The app has been modernized away from pure Bootstrap-default visual language.

Key design choices:

- stronger product-style homepage hierarchy
- cleaner navigation shell
- dedicated classroom-oriented messaging
- scenario pages should feel guided and didactic, not just form-heavy

If future UI work is done, keep these principles:

- prioritize clarity over density
- each page should teach one progression, not many unrelated concepts
- explanatory labels and visible intermediate states are valuable
- avoid adding decorative complexity that hides the logic

## Known Constraints

- Large amounts of logic still live inline inside Pug templates
- `public/stylesheets/blockchain.css` is long and accumulates page-specific sections
- Some older pages still reflect legacy layout conventions
- Classroom mode can raise SSE/response handling issues if routes are changed carelessly
- There is still no persistence layer for classroom sessions

## Recommended Next Steps

Highest-value future improvements:

1. Connect `Signed Block Lab` and `UTXO Lab` into the multiuser classroom flow
2. Add persistence for classroom sessions
3. Improve route robustness for SSE and classroom state recovery
4. Modularize large inline scripts from Pug pages into separate JS files
5. Consider a dedicated module for script locking / unlocking or wallet addresses

## Files Worth Reading First In Future Sessions

- `views/layout.pug`
- `views/index.pug`
- `views/classroom.pug`
- `views/signedblock.pug`
- `views/utxo.pug`
- `lib/classroom-store.js`
- `routes/index.js`
- `public/javascripts/blockchain.js`
- `public/stylesheets/blockchain.css`
- `docs/classroom-mode-roadmap.md`

