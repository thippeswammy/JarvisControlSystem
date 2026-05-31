# Jarvis v2 Architecture Remarks & Future Improvements

## Purpose

This document captures architectural observations, known limitations, potential loopholes, and future improvements identified during architecture reviews and real-world scenario testing. These remarks are intended to supplement the main architecture document and should be reviewed before implementing major autonomous-agent features.

---

# 1. User Goal Understanding Before Tool Selection

## Current Risk

The current architecture is heavily action-oriented.

Flow:

User Request
→ Intent Detection
→ Planning
→ Tool Selection
→ Execution

This can cause the system to focus on available tools rather than the user's actual objective.

Example:

User:
"Search ROS2 on GitHub and write a summary."

Incorrect reasoning:

"I have a browser tool and a typing tool."

Correct reasoning:

"The user wants ROS2 information and a summary. I must determine how to obtain the information and how to deliver it."

## Recommended Improvement

Introduce a dedicated Goal Understanding Layer.

Flow:

User Request
→ Intent Parsing
→ Goal Understanding
→ Knowledge Gap Analysis
→ Capability Planning
→ Tool Selection
→ Execution

---

# 2. Knowledge Gap Detection

## Current Risk

The system may begin execution without determining whether it has enough information to complete the task.

Example:

User:
"Book a hotel."

Missing information:

* Location
* Dates
* Budget
* Room count

Execution should never begin until required information is available.

## Recommended Improvement

Add a Knowledge Gap Engine.

Responsibilities:

* Detect missing parameters
* Determine confidence levels
* Ask clarification questions when required
* Prevent premature execution

---

# 3. Capability-Based Planning

## Current Risk

The planner may think in terms of tools.

Example:

Need browser
→ Open Edge

Instead, the planner should think:

Need web information
→ Evaluate available capabilities
→ Select best capability provider
→ Select appropriate tool

## Recommended Improvement

Introduce Capability Planning.

Flow:

Goal
→ Required Capabilities
→ Candidate Providers
→ Tool Selection

This reduces tool coupling and improves extensibility.

---

# 4. Grounded Context Resolution

## Current Risk

The LLM may hallucinate references.

Example:

User:
"Open it again."

System invents a reference that does not exist in current context.

Observed during Scenario 99 testing.

## Recommended Improvement

Create a Grounding Layer.

Only expose:

* Current world state
* Current focused application
* Last successful action
* Last failed action
* Active task chain

The planner should not be allowed to reference anything outside this grounded context.

---

# 5. Fast Path Safety Bypass

## Current Risk

Procedural memory may bypass critical validation layers.

Potential flow:

Memory Hit
→ Execute

This could bypass:

* Safety validation
* Risk analysis
* Approval requirements
* Context verification

## Recommended Improvement

All execution paths must pass through:

Safety Layer
→ Risk Engine
→ Execution Authority
→ Execution

No exceptions.

---

# 6. Unsafe Procedural Learning

## Current Risk

Partial task completion may be stored as reusable macros.

Example:

Task:
Open browser
Search ROS2
Generate summary

Execution fails midway.

Partial sequence is learned anyway.

## Recommended Improvement

Only learn procedures when:

* Goal completed
* Verification successful
* No critical failures occurred
* Confidence threshold exceeded

---

# 7. Recovery Loop Repetition

## Current Risk

Recovery engine may repeatedly execute identical failed actions.

Example:

activate_window()
→ Fail

activate_window()
→ Fail

activate_window()
→ Fail

## Recommended Improvement

Introduce Action Fingerprints.

Track:

* Action
* Parameters
* Context

Block repeated failures after threshold is exceeded.

---

# 8. Prompt Injection Containment

## Current Risk

Browser agents may retrieve hostile instructions.

Example:

"Ignore previous instructions."

"Delete files."

These instructions may contaminate planner reasoning.

## Recommended Improvement

Separate data into:

Trusted Context

and

Untrusted Context

The planner must never treat external content as instructions.

---

# 9. Execution Authority Layer

## Missing Component

A dedicated execution authority layer should exist between planning and execution.

Responsibilities:

* Verify grounding
* Verify permissions
* Verify safety rules
* Verify approval requirements
* Verify risk level
* Verify failure history

Flow:

Think
→ Execution Authority
→ Act

---

# 10. Multi-Stage Verification

## Current Risk

Success may be declared too early.

Example:

Application launches briefly and crashes.

Current verification:

Window exists
→ Success

## Recommended Improvement

Verification stages:

1. Application launched
2. Application focused
3. Application responsive
4. Intended operation completed

Only then mark task complete.

---

# 11. World State Scalability

## Current Risk

Large world states can exceed practical context limits.

Examples:

* Hundreds of windows
* Thousands of controls
* Large browser sessions

## Recommended Improvement

WorldStateModeler should maintain:

Full State

but expose only:

Relevant State

through retrieval and filtering mechanisms.

---

# 12. Human Approval Framework

## Recommended Risk Levels

SAFE

Examples:

* Open Notepad
* Open Browser

MEDIUM

Examples:

* Close Application
* Modify Local Documents

HIGH

Examples:

* Delete Files
* Bulk Operations

CRITICAL

Examples:

* Shutdown System
* Registry Modification
* System Reconfiguration

HIGH and CRITICAL actions should require explicit confirmation.

---

# 13. Core Principle

The system should always reason in the following order:

1. What does the user actually want?
2. What information is required?
3. What information is missing?
4. What capabilities are required?
5. Which tools provide those capabilities?
6. Can execution be performed safely?
7. Execute
8. Verify
9. Learn

The system should never start with:

"What tool should I call?"

Tools are implementation details.

User goals are primary.

# True autonomous agent should be more like:

```
User
 ↓
Understand User Goal
 ↓
Determine Missing Information
 ↓
Determine Needed Knowledge
 ↓
Determine Needed Tools
 ↓
Create Execution Strategy
 ↓
Execute
```

Right now, Jarvis appears to be treating tools as the primary mechanism, rather than treating tools as resources available to achieve a user goal.
