---
noteId: "6979631035bd11f1881085dbd4e6cf0f"
tags: []

---

# Classroom Mode Roadmap

## Current State

This project is currently a single-user educational demo:

- Each browser owns its own blockchain state.
- Mining happens entirely in the client.
- There is no user identity, room concept, persistence, or shared event stream.
- The `distributed` page simulates peers visually, but all peers live in one browser session.

That makes the project excellent for teacher-led explanation, but not yet for a live classroom where many students connect at once.

## Target Outcome

Build a shared classroom session where:

- A teacher creates a room and selects the exercise.
- Students join with a room code and a nickname.
- The class shares one canonical chain, mempool, scoreboard and event log.
- Mining, tampering and validation are broadcast in real time.
- The teacher can reset, fork, freeze or replay the scenario.

## Recommended MVP

### Backend

- Keep `Express`.
- Add `express-session` for teacher auth and room ownership.
- Add `Socket.IO` for real-time room updates.
- Store room state in memory first.
- Add Redis only if you later need multiple app instances or persistent room recovery.

### Identity Model

- Teacher:
  - email + password or magic link
  - owns classroom sessions
- Student:
  - join code + display name
  - no password required for MVP

This gives low friction in class while still letting the teacher control the room.

### Shared Room State

Each room should hold:

- room id / join code
- selected scenario (`blockchain`, `distributed`, `mempool`, `attack51`)
- difficulty
- canonical chain
- mempool
- participants
- event history
- phase controls (`editing`, `mining`, `discussion`, `locked`)

## Interaction Model

### Teacher Console

- Create / close room
- Set difficulty
- Start round
- Freeze editing
- Force fork / attack event
- Reset room
- Reveal solution

### Student View

- Join room
- Choose a role: miner, validator, observer
- Submit transaction or block proposal
- Mine locally, but send candidate result to the server
- Receive authoritative updates from the room

## Important Product Decision

Do not trust the browser as the final authority for classroom mining results.

Recommended rule:

- The browser can simulate work and submit a candidate nonce.
- The server validates the candidate against the room state.
- The first valid candidate wins and is broadcast to the class.

This prevents state drift and keeps the exercise fair.

## Rollout Plan

### Phase 1

- Add room creation
- Add student join flow
- Add shared mempool / chain state
- Add Socket.IO broadcast

### Phase 2

- Add roles and scoreboard
- Add teacher orchestration tools
- Add event timeline

### Phase 3

- Add saved session replay
- Add participation analytics
- Add institution SSO if needed

## Suggested First Implementation Slice

If you want the fastest path to a usable classroom demo, start with:

1. `mempool` as the first shared scenario
2. teacher creates room
3. students join with code
4. all users see the same mempool
5. one student mines the next block
6. teacher resets and repeats

That slice is narrow, highly visual, and easy to use in a live class.
