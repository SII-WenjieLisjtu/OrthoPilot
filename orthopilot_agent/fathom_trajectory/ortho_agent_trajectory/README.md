# Medical Trajectory Utilities

This directory contains public example utilities for generating and enhancing OrthoPilot-style trajectory JSON files. The examples are intended for synthetic or local demonstration data only.

## Services

Start the required Fathom trajectory services before running the scripts. Adjust ports and hosts through the command-line options when needed.

```bash
serving/start_fathom_search_4b.sh
serving/start_fathom_synthesizer_4b.sh
serving/host_server.sh 8904 256
```

## Main scripts

| Use case | Script | Description |
| --- | --- | --- |
| Generate a new trajectory from a question | `medical_trajectory_generator.py` | Sends a natural-language question to the trajectory model and records the tool-use process. |
| Enhance an existing trajectory | `trajectory_enhancer.py` | Reads an existing trajectory JSON file and adds missing search steps. |
| Enhance trajectories with the R1 workflow | `trajectory_enhancer_r1.py` | Variant of the enhancer used by the public example script. |

## Example commands

Generate a new trajectory:

```bash
python3 medical_trajectory_generator.py \
 --question "Provide an admission diagnosis and supporting evidence from the synthetic case." \
 --model-url http://localhost:8000 \
 --executors http://localhost:8000 \
 --tokenizer FractalAIResearch/Fathom-Search-4B \
 --max-searches 5 \
 --output-path outputs/trajectory.json
```

Enhance an existing trajectory:

```bash
python3 trajectory_enhancer.py \
 --input demo/trajectory_input.json \
 --output outputs/trajectory_enhanced.json \
 --model-url http://localhost:8000 \
 --executors http://localhost:8000 \
 --max-searches 5
```

Useful flags:

- `--dry-run` checks parsed inputs without calling the model.
- `--force` allows overwriting an existing output file.

## Data convention

Trajectory files should be JSON arrays of `{role, content}` objects. The enhancer preserves the original diagnosis and appends retrieval-supported reasoning in the final answer.

## Directory overview

- `medical_trajectory_generator.py`: end-to-end trajectory generation.
- `trajectory_enhancer.py`: trajectory enhancement for existing JSON files.
- `trajectory_enhancer_r1.py`: R1 enhancement entry point.
- `trajectory_enhancer.sh`: environment-driven shell wrapper for public examples.
