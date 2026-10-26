"""Regression tests for Quran ASR evaluation metrics."""

import unittest

from evaluate_baseline import edit_counts
from run_evaluation import calculate


class TestEditCounts(unittest.TestCase):

    def test_exact_match(self):
        result = edit_counts(
            ["الحمد", "لله"],
            ["الحمد", "لله"],
        )
        self.assertEqual(result["distance"], 0)

    def test_substitution(self):
        result = edit_counts(
            ["مالك", "يوم", "الدين"],
            ["ملك", "يوم", "الدين"],
        )
        self.assertEqual(result["S"], 1)
        self.assertEqual(result["distance"], 1)

    def test_deletion(self):
        result = edit_counts(
            ["الحمد", "لله", "رب"],
            ["الحمد", "لله"],
        )
        self.assertEqual(result["D"], 1)
        self.assertEqual(result["distance"], 1)

    def test_insertion(self):
        result = edit_counts(
            ["الحمد", "لله"],
            ["الحمد", "لله", "رب"],
        )
        self.assertEqual(result["I"], 1)
        self.assertEqual(result["distance"], 1)


class TestMetrics(unittest.TestCase):

    def test_exact_match(self):
        result = calculate(
            "الرحمن الرحيم",
            "الرحمن الرحيم",
        )
        self.assertEqual(result["WER"], 0)
        self.assertEqual(result["CER"], 0)

    def test_missing_alef(self):
        result = calculate(
            "مالك يوم الدين",
            "ملك يوم الدين",
            normalized=True,
        )
        self.assertAlmostEqual(result["WER"], 1 / 3)

    def test_hamza_normalization(self):
        result = calculate(
            "إياك نعبد وإياك نستعين",
            "اياك نعبد واياك نستعين",
            normalized=True,
        )
        self.assertEqual(result["WER"], 0)
        self.assertEqual(result["CER"], 0)

    def test_empty_reference(self):
        with self.assertRaises(ValueError):
            calculate("", "الحمد لله")


if __name__ == "__main__":
    unittest.main()
