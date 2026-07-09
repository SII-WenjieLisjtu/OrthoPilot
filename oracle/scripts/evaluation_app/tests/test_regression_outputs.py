import os
import sys
import unittest

SCRIPT_DIR = "/path/to/orthopilot/project/评测框架/scripts/evaluation_app"
DATA_DIR = "/path/to/orthopilot/project/评测框架/data/analysis"

sys.path.insert(0, SCRIPT_DIR)

import export_nature_tables
import generate_figures


class RegressionOutputTests(unittest.TestCase):
    def test_generate_figures_exposes_style_config(self):
        self.assertEqual(generate_figures.BT_XTICK_FONTSIZE, 13)
        self.assertEqual(generate_figures.BT_VALUE_FONTSIZE, 8.5)
        self.assertEqual(generate_figures.ERROR_VALUE_OFFSET, 1.5)
        self.assertEqual(generate_figures.RANKING_BAR_WIDTH, 0.55)
        self.assertEqual(generate_figures.HIDE_TOP_RIGHT_SPINES, True)
        self.assertEqual(generate_figures.RANKING_SEGMENT_LABEL_FONTSIZE, 9)
        self.assertEqual(generate_figures.RADAR_GRID_LINEWIDTH, 1.8)
        self.assertEqual(generate_figures.RADAR_VALUE_FONTSIZE, 11)
        self.assertEqual(generate_figures.RADAR_LABEL_FONTSIZE, 16)
        self.assertEqual(generate_figures.RADAR_MARKER_SIZE, 64)
        self.assertEqual(generate_figures.RADAR_OUTER_SPINE_LINEWIDTH, 2.2)
        self.assertEqual(generate_figures.RADAR_LEGEND_BBOX, (0.5, 1.30))
        self.assertEqual(generate_figures.RADAR_BACKGROUND, '#FFFFFF')
        self.assertEqual(generate_figures.RADAR_XTICK_PAD, 30)
        self.assertEqual(generate_figures.RADAR_VALUE_OFFSETS, [0.40, 0.22, 0.04, -0.10])
        self.assertEqual(generate_figures.RADAR_VALUE_ANGLE_OFFSETS, [0.12, -0.12, -0.04, 0.04])
        self.assertEqual(generate_figures.RADAR_THETA_OFFSET, 0.0)

    def test_radar_palette_has_high_contrast_colors(self):
        self.assertEqual(len(generate_figures.RADAR_COLORS), 4)
        self.assertEqual(len(set(generate_figures.RADAR_COLORS)), 4)
        self.assertNotEqual(generate_figures.RADAR_COLORS[0], generate_figures.RADAR_COLORS[1])

    def test_nature_tables_matches_regenerated_content(self):
        evaluations = export_nature_tables.load_evaluations()
        expected = "\n\n".join([
            export_nature_tables.generate_table1_bt_params(evaluations),
            export_nature_tables.generate_table2_likert_scores(evaluations),
            export_nature_tables.generate_table3_reliability(evaluations),
            export_nature_tables.generate_table4_error_rates(evaluations),
            export_nature_tables.generate_table5_first_place(evaluations),
        ])

        table_path = os.path.join(DATA_DIR, "nature_tables.tex")
        with open(table_path, "r", encoding="utf-8") as f:
            current = f.read()

        current = "\n".join(current.splitlines()[3:]).strip()
        self.assertEqual(current, expected.strip())

    def test_generate_figures_exposes_nature_palette(self):
        self.assertEqual(
            generate_figures.NATURE_PALETTE,
            ["#92B1D9", "#C1D8E9", "#DBDDEF", "#F6C8B6", "#D4D4D4"],
        )

    def test_bt_summary_includes_overall_group(self):
        evaluations = generate_figures.load_evaluations()
        labels, values_by_model = generate_figures.build_bt_grouped_summary(evaluations)

        self.assertEqual(labels[-1], "Overall")
        self.assertEqual(len(labels), 8)
        self.assertEqual(set(values_by_model.keys()), {
            "bone-14B-v4",
            "gpt-5-high",
            "medgemma-27b-text-it",
            "deepseek-r1-0528-ep",
        })
        for values in values_by_model.values():
            self.assertEqual(len(values), 8)


if __name__ == "__main__":
    unittest.main()
