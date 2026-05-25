# Jarvis v2.1 — Robustness & State-Aware Architecture

**Context Reference**: [Reviewing Jarvis V2 Implementation Plan](file:///C:/Users/thipp/.gemini/antigravity/brain/1d5d2b37-e0b3-410d-92ee-63c2987b048a/overview.txt)

This document evolves the original "v2" design by addressing critical structural weaknesses identified in the technical review. It shifts the system from a "Navigation Map" to a **State-Aware Autonomous Agent**.

---

## 1. The Core Architecture Shift

| Feature | v2.0 (Visionary) | v2.1 (Robust) |
|---|---|---|
| **Memory Storage** | Loose Markdown files | **SQLite + NetworkX** (Persistent Graph DB) |
| **Node Identity** | UI Location only | **UI Location + State Snapshot** |
| **Pathfinding** | Cyclic Dijkstra (Expensive) | **A* with Contextual Pruning** |
| **Learning Loop** | "Execute -> Store" | **Execute -> Verify -> Learn** |
| **Reliability** | Heuristic Fallback | **Transactional Rollback** |

---

## 2. Pillar 1: Persistent Graph Database (The "Brain" Storage)

Instead of parsing `.md` files on every command, Jarvis v2.1 uses a structured database.

*   **Engine**: `sqlite3` + `NetworkX`.
*   **Schema**:
    *   `nodes`: `id`, `app_id`, `type`, `label`, `state_hash`, `ui_metadata` (JSON).
    *   `edges`: `id`, `from_id`, `to_id`, `action_type`, `action_params` (JSON), `confidence`, `success_count`, `fail_count`.
*   **Why**: Atomicity (no file corruption), sub-millisecond queries, and native support for complex graph algorithms.
*   **Human-Readability**: An `Exporter` service generates a human-readable `.md` snapshot on demand for debugging.

---

## 3. Pillar 2: State-Machine Nodes

Nodes are no longer just "points on a map." They are **States**.

*   **Node Representation**: `Node = (AppID, PageID, UIState)`.
*   **UIState**: A subset of the UI tree containing values of toggles, selection status, and visibility.
    *   *Example*: A WiFi node isn't just `Settings > WiFi`. It is `Settings > WiFi {toggle: ON}`.
*   **Pre-conditions**: Edges now have a `pre_condition` field.
    *   *Example*: The "Turn Off" edge only appears/activates if the current state is `toggle: ON`.

---

## 4. Pillar 3: The Verification Loop (Closed-Loop Learning)

Jarvis will no longer "blindly learn" from success.

1.  **Action**: Execute the SkillCall (e.g., `click(toggle_wifi)`).
2.  **Scan**: Immediately re-capture the UI state after the action.
3.  **Verify**: Compare the new state with the `TargetNode.state_hash`.
4.  **Learn**: 
    *   **Match**: Success. Boost edge confidence. Save to memory.
    *   **Mismatch**: Failure. Trigger **Recovery Flow**. Do NOT store as a successful path.

---

## 5. Pillar 4: Hierarchical Planning & Pruning

To prevent the "Graph Explosion" where Dijkstra becomes slow:

*   **Hierarchical Search**:
    1.  **L1**: App-level (e.g., Navigate from Chrome to Settings).
    2.  **L2**: Page-level (e.g., Navigate from System to Display).
    3.  **L3**: Element-level (e.g., Click the "Brightness" slider).
*   **Contextual Pruning**: When looking for a path in *Notepad*, the system completely ignores all *Chrome* and *Settings* nodes in memory.

---

## 6. Pillar 5: Recovery & Rollback

When a step fails or a mismatch is detected:

*   **Retry (Max 2)**: Re-attempt the action with a brief delay (handles UI lag).
*   **Alternative Path**: If confidence in current edge is low, try the next best Dijkstra path.
*   **Undo/Rollback**: If the system gets "lost," use a `BACK` edge to return to the last known-good state.
*   **Ask User**: Final resort. "I'm lost. I've reached [State X] but expected [State Y]. What should I do?"

---

## 7. Implementation Roadmap (Condensed)

### Phase A: The Memory Core
- [ ] Initialize SQLite Graph DB.
- [ ] Build the `StateHarvester` (extracts values from UI elements, not just names).
- [ ] Create `GraphDB <-> NetworkX` synchronization layer.

### Phase B: The Verification Engine
- [ ] Implement `VerificationLoop` logic.
- [ ] Build the `StateComparator` (fuzzy state matching to ignore noise like clock changes).

### Phase C: Hybrid Planning
- [ ] Implement **A* search** with a heuristic based on hierarchical depth.
- [ ] Integrate the **LLM Planner** as a "Path Generator" for zero-knowledge states.

### Phase D: Migration & Seeding
- [ ] Migration script: Convert v1 `.md` files into the v2.1 Graph Database.
- [ ] Seed the database with the "Settings State Machine" (WiFi, Display, Sound).

---

## 8. Success Metrics
1.  **Zero-False Learning**: No "bad" paths stored in memory due to UI lag.
2.  **Pathfinding Latency**: < 100ms for graphs up to 5,000 nodes.
3.  **Task Success Rate**: > 95% on repeated tasks across different window sizes.
