# Fathom trajectory utilities

This directory contains OrthoPilot-specific utilities for generating, compressing and evaluating search/no-search reasoning trajectories.

## Contents

```
fathom_trajectory/
|-- eval_nosearch.py # Evaluation without external search trajectories
|-- eval_search.py # Evaluation with search trajectories
|-- inference.py # Trajectory inference entry point
|-- prompts.py # Prompt templates for trajectory construction
|-- requirements.txt # Optional trajectory-generation dependencies
|-- agents/ # Lightweight agent wrappers
|-- eval_datasets/ # Dataset schema notes and placeholders
|-- ortho_agent_trajectory/ # Medical trajectory generation and enhancement
`-- serving/ # Minimal serving utilities retained for reference
```

## Notes

Large trajectory datasets, generated outputs, model checkpoints and service launch scripts are not included in this public release. Configure model endpoints and search services locally before running the full trajectory workflow.

For the reviewer-facing synthetic demo, use `demo/run_demo.py` from the repository root.
