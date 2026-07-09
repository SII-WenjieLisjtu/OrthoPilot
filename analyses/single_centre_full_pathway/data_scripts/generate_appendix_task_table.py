#!/usr/bin/env python3
from pathlib import Path
import math
import pandas as pd

BASE = Path('/path/to/orthopilot/project/多中心验证/单中心全流程任务/reader_data_scripts')
INPUT_CSV = BASE / 'combined_all_tasks.csv'
OUTPUT_TEX = BASE / 'appendix_core_11_tasks_table_body.tex'
OUTPUT_SUMMARY = BASE / 'appendix_core_11_tasks_table_summary.txt'
METRIC_COLS = [f'task{i}' for i in range(1, 12)] + ['closed_avg', 'open_avg']
CATEGORY_ORDER = ['Ours', 'Reasoning LLMs', 'General LLMs', 'Medical LLMs', 'Agent Methods']


def escape_latex(text: str) -> str:
    repl = {
        '&': r'\&',
        '%': r'\%',
        '_': r'\_',
        '#': r'\#',
    }
    out = str(text)
    for src, dst in repl.items():
        out = out.replace(src, dst)
    return out


def format_number(value: float) -> str:
    return f'{value:.2f}'


def compute_rank_maps(df: pd.DataFrame):
    best = {}
    second = {}
    second_names = {}
    for col in METRIC_COLS:
        values = sorted(df[col].dropna().unique(), reverse=True)
        best[col] = {round(values[0], 10)} if values else set()
        second_value = values[1] if len(values) > 1 else None
        second[col] = {round(second_value, 10)} if second_value is not None else set()
        if second_value is None:
            second_names[col] = []
        else:
            second_names[col] = df.loc[df[col] == second_value, 'model'].tolist()
    return best, second, second_names


def format_metric(col: str, value: float, best_map, second_map) -> str:
    number = format_number(value)
    key = round(float(value), 10)
    if key in best_map[col]:
        return rf'\textbf{{{number}}}'
    if key in second_map[col]:
        return rf'\underline{{{number}}}'
    return number


def category_sort_key(cat: str):
    if cat in CATEGORY_ORDER:
        return (CATEGORY_ORDER.index(cat), cat)
    return (len(CATEGORY_ORDER), cat)


def generate_table(input_csv: Path = INPUT_CSV, output_tex: Path = OUTPUT_TEX, output_summary: Path = OUTPUT_SUMMARY):
    df = pd.read_csv(input_csv)
    complete = df.dropna(subset=METRIC_COLS).copy()
    excluded = df.loc[~df.index.isin(complete.index), 'model'].tolist()
    best_map, second_map, second_names = compute_rank_maps(complete)

    complete['category_order'] = complete['category'].map(lambda x: category_sort_key(x))
    complete = complete.sort_values(['category_order', 'params', 'model'], ascending=[True, False, True], kind='stable')

    lines = []
    categories = list(dict.fromkeys(complete['category'].tolist()))
    first_category = True
    for category in categories:
        if not first_category:
            lines.append(r'\midrule')
        first_category = False
        lines.append(rf'\multicolumn{{15}}{{l}}{{\textbf{{{escape_latex(category)}}}}} \\')
        lines.append(r'\midrule')
        sub = complete[complete['category'] == category]
        for _, row in sub.iterrows():
            cells = [escape_latex(row['model']), str(int(row['params']))]
            for col in METRIC_COLS:
                cells.append(format_metric(col, row[col], best_map, second_map))
            lines.append(' & '.join(cells) + r' \\')

    output_tex.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    summary_lines = [
        f'Retained {len(complete)} complete models; excluded {len(excluded)} incomplete models'
        + (f": {', '.join(excluded)}." if excluded else '.'),
        '',
    ]
    label_map = {**{f'task{i}': f'T{i}' for i in range(1, 12)}, 'closed_avg': 'Closed avg', 'open_avg': 'Open avg'}
    for col in METRIC_COLS:
        value = sorted(complete[col].dropna().unique(), reverse=True)
        if len(value) > 1:
            names = ', '.join(second_names[col])
            summary_lines.append(f"{label_map[col]} second-best: {names} ({format_number(value[1])}).")
        else:
            summary_lines.append(f"{label_map[col]} second-best: none.")

    output_summary.write_text('\n'.join(summary_lines) + '\n', encoding='utf-8')
    return {
        'kept_models': len(complete),
        'excluded_models': excluded,
        'categories': categories,
    }


if __name__ == '__main__':
    result = generate_table()
    print(f"Wrote {OUTPUT_TEX}")
    print(f"Wrote {OUTPUT_SUMMARY}")
    print(f"Retained {result['kept_models']} models")
