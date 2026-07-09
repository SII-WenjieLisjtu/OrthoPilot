# ORACLE Framework Code

This directory contains public framework code for ORACLE-style open-response evaluation. Manuscript-output utilities, figure generation, table export, mock-result generation and controlled-data preparation scripts are not included in this public release.

## Included files

- `docs/ORACLE_EVALUATION_METHOD.md`: framework method note.
- `scripts/task_all_gen_async.py`: asynchronous evaluator entry point template.

## Excluded assets

Controlled evaluation datasets, physician-reader study files, generated responses, scoring tables, figures and paper-result construction scripts are excluded.

## Usage boundary

The retained script is a source template for governed local evaluation workflows. It requires locally prepared task files, rubric metadata, response files and evaluator model access. Do not commit credentials, private endpoints or patient-derived data.
