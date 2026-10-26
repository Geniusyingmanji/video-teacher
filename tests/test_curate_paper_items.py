import unittest

from scripts.curate_paper_items import DIMENSIONS, audit, item_hash


class PaperItemCurationTest(unittest.TestCase):
    def test_release_requires_fresh_independent_complete_reviews(self):
        row = {"id": "case", "discipline": "mathematics", "task_type": "problem_solving",
               "difficulty": "high", "prompt_text": "One equation step"}
        digest = item_hash(row)
        reviewer = {"case_id": "case", "role": "reviewer", "item_sha256": digest,
                    "difficulty": "intermediate", "cognitive_skill": "application",
                    **{field: True for field in DIMENSIONS}}
        final = {"case_id": "case", "role": "adjudicator", "item_sha256": digest,
                 "reviewer_id": "expert-c", "decision": "accept", "difficulty": "intermediate",
                 "cognitive_skill": "application", "source_url": "https://example.org/source",
                 "license": "CC BY 4.0", "reference_answer": "x = 2",
                 "atomic_target": "Move one term", "expected_final_state": "x = 2",
                 "failure_criteria": "Wrong sign", "difficulty_rationale": "One algebraic step"}
        reviews = [{**reviewer, "reviewer_id": "expert-a"},
                   {**reviewer, "reviewer_id": "expert-b"}, final]
        report, queue, accepted = audit([row], reviews)
        self.assertEqual(report["accepted_count"], 1)
        self.assertEqual(accepted[0]["reviewed_difficulty"], "intermediate")
        self.assertEqual(queue[0]["gates"], [])

        changed = {**row, "prompt_text": "Different equation step"}
        self.assertEqual(audit([changed], reviews)[0]["accepted_count"], 0)
        self.assertEqual(audit([row], reviews[:1] + reviews[2:])[0]["accepted_count"], 0)
        self.assertEqual(audit([row], reviews[:2] + [{**final, "license": "unknown"}])[0]["accepted_count"], 0)
        self.assertEqual(audit([row], reviews[:2] + [{**final, "expected_final_state": ""}])[0]["accepted_count"], 0)


if __name__ == "__main__":
    unittest.main()
