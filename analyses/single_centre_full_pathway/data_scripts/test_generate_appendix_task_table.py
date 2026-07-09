import importlib.util
from pathlib import Path
import pandas as pd
import tempfile
import unittest

MODULE_PATH = Path(__file__).with_name('generate_appendix_task_table.py')
spec = importlib.util.spec_from_file_location('generate_appendix_task_table', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GenerateAppendixTaskTableTest(unittest.TestCase):
    def test_filters_incomplete_and_formats_best_second(self):
        rows = [
            {
                'model': 'Model A', 'task1': 90.0, 'task2': 70.0, 'task3': 70.0, 'task4': 70.0,
                'task5': 70.0, 'task6': 70.0, 'task7': 70.0, 'task8': 70.0, 'task9': 70.0,
                'task10': 70.0, 'task11': 70.0, 'closed_avg': 75.0, 'open_avg': 70.0,
                'category': 'Cat 1', 'params': 10,
            },
            {
                'model': 'Model B', 'task1': 85.0, 'task2': 65.0, 'task3': 65.0, 'task4': 65.0,
                'task5': 65.0, 'task6': 65.0, 'task7': 65.0, 'task8': 65.0, 'task9': 65.0,
                'task10': 65.0, 'task11': 65.0, 'closed_avg': 70.0, 'open_avg': 65.0,
                'category': 'Cat 1', 'params': 20,
            },
            {
                'model': 'Model C', 'task1': 85.0, 'task2': 60.0, 'task3': 60.0, 'task4': 60.0,
                'task5': 60.0, 'task6': 60.0, 'task7': 60.0, 'task8': 60.0, 'task9': 60.0,
                'task10': 60.0, 'task11': 60.0, 'closed_avg': 65.0, 'open_avg': 60.0,
                'category': 'Cat 2', 'params': 30,
            },
            {
                'model': 'Model Missing', 'task1': None, 'task2': 50.0, 'task3': 50.0, 'task4': 50.0,
                'task5': 50.0, 'task6': 50.0, 'task7': 50.0, 'task8': 50.0, 'task9': 50.0,
                'task10': 50.0, 'task11': 50.0, 'closed_avg': 50.0, 'open_avg': 50.0,
                'category': 'Cat 2', 'params': 40,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            csv_path = tmp / 'combined_all_tasks.csv'
            tex_path = tmp / 'body.tex'
            summary_path = tmp / 'summary.txt'
            pd.DataFrame(rows).to_csv(csv_path, index=False)

            result = module.generate_table(csv_path, tex_path, summary_path)
            tex = tex_path.read_text(encoding='utf-8')
            summary = summary_path.read_text(encoding='utf-8')

        self.assertEqual(result['kept_models'], 3)
        self.assertEqual(result['excluded_models'], ['Model Missing'])
        self.assertIn('\\multicolumn{15}{l}{\\textbf{Cat 1}} \\\\', tex)
        self.assertIn('Model A & 10 & \\textbf{90.00}', tex)
        self.assertIn('Model B & 20 & \\underline{85.00}', tex)
        self.assertIn('Model C & 30 & \\underline{85.00}', tex)
        self.assertNotIn('Model Missing', tex)
        self.assertIn('Retained 3 complete models; excluded 1 incomplete models: Model Missing.', summary)
        self.assertIn('T1 second-best: Model B, Model C (85.00).', summary)


if __name__ == '__main__':
    unittest.main()
