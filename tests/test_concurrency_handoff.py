import unittest
from tools.expand_qwen_concurrency import slots


class ConcurrencyHandoffTests(unittest.TestCase):
    def test_adopts_existing_workers_and_opens_one_extra_slot_per_gpu(self):
        active = {'math': {'pid': 101, 'gpu': 0}, 'physics': {'pid': 102, 'gpu': 1}}
        actual = slots([0, 1], [8000, 8001], 2, active)
        self.assertEqual(actual, [(0, 8000, ('math', 101)), (0, 8000, None),
                                  (1, 8001, ('physics', 102)), (1, 8001, None)])

    def test_refuses_unapproved_gpu_and_too_few_slots(self):
        with self.assertRaises(ValueError):
            slots([0, 1], [8000, 8001], 2, {'other': {'pid': 103, 'gpu': 2}})
        with self.assertRaises(ValueError):
            slots([0, 1], [8000, 8001], 1,
                  {'a': {'pid': 101, 'gpu': 0}, 'b': {'pid': 102, 'gpu': 0}})
