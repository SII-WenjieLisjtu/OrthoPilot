# ORACLE evaluation framework

ORACLE, Open Response Assessment for Clinical Language Evaluation, is a framework for evaluating open-ended clinical responses. It is designed for tasks where a useful answer may cover several clinically relevant elements rather than match a single label.

This public-release note describes the retained framework at a high level. It does not include controlled datasets, physician-reader files, generated responses, scoring tables, figures, table exports, mock-result utilities or paper-result construction scripts.

## Public files

The retained public ORACLE files are:

- `oracle/README_ORACLE_SOURCE.md`: release-scope notes for the ORACLE framework code.
- `oracle/scripts/task_all_gen_async.py`: asynchronous evaluator entry point template.

## Evaluation concept

For open-response tasks, ORACLE represents expected answer content as task-specific clinical elements. A configured evaluator checks whether a model response covers those elements and returns structured coverage judgments. Implementations can aggregate those judgments into response-level scores for local research workflows.

The public repository provides framework code only. Users must supply their own governed task files, rubrics, response files and evaluator model access.

## Intended use

Use the retained script as a template for local, governed evaluation experiments. Before running it, inspect the expected input schema, output paths and endpoint configuration. Provide credentials through environment variables or local configuration files that are not committed to version control.

## Release boundary

The public release is not a turnkey reproduction package. It excludes patient-derived data, private endpoints, controlled rubrics, physician-reader artifacts and manuscript-result builders. The code is provided for method inspection and adaptation under appropriate data governance.
