# Agent reasoning framework

This public method note summarizes the OrthoPilot agent framework at a high level. It contains no private paths, patient data or manuscript-working notes.

## Overview

OrthoPilot uses a hierarchical agent design for evidence-grounded reasoning in musculoskeletal care. A main agent receives the clinical question, plans the reasoning process and synthesizes the final response. Worker agents perform focused evidence-gathering tasks through configured tools and return structured summaries.

The design separates planning from evidence retrieval. The main agent manages the clinical reasoning flow. Worker agents query the available evidence interfaces and compress findings into concise summaries for the main agent.

## Tool Plaza interface

Tool Plaza provides a common interface for evidence sources. In a configured deployment, these sources can include local clinical services, similar-case retrieval, literature retrieval, knowledge services, web search and multimodal tools. This public release contains interface templates and adapters only. Site-specific services, credentials, indexes and patient-derived data are excluded.

## Reasoning loop

At each step, the main agent can choose to request more evidence, delegate a focused subtask or synthesize an answer. A worker agent receives a task description and the allowed tools for that task. It returns a structured evidence summary rather than a full transcript.

This loop supports trace inspection because each action is represented explicitly in the interaction history. It also limits context noise because the main agent receives compressed summaries from worker sessions.

## Information-flow safeguards

The framework uses three safeguards:

1. Worker sessions are isolated from one another.
2. Worker agents return structured summaries rather than unrestricted logs.
3. The main agent performs final synthesis only after evidence collection is sufficient for the requested task.

These safeguards make the system easier to audit and adapt in controlled research environments.

## Public-release boundary

The public repository includes source code, prompts and configuration templates for inspection. It does not include hospital services, patient records, model weights, retrieval indexes, private endpoints or paper-result artifact builders. The deterministic demo in `demo/` is synthetic and is intended only to verify repository wiring.
