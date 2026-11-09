import unittest
from fractions import Fraction
from manim import Scene,tempconfig
from generation.scene_state import ArraySlots,FormulaSlot,cantor_intervals,interior_angles,assert_closed_path


class SceneStateTests(unittest.TestCase):
    def test_original_two_swaps_keep_correct_objects_in_each_slot(self):
        with tempconfig({'dry_run':True,'pixel_width':854,'pixel_height':480}):
            scene=Scene();array=ArraySlots([3,1,2]);scene.add(array.group)
            original=list(array.labels);array.swap(scene,0,1,run_time=.1);array.swap(scene,1,2,run_time=.1)
            self.assertEqual(array.values,[1,2,3]);self.assertEqual(array.labels,[original[1],original[2],original[0]])
            self.assertTrue(array.verify()['one_value_per_slot'])

    def test_formula_replacement_and_clear_leave_no_verification_ghost(self):
        with tempconfig({'dry_run':True}):
            scene=Scene();slot=FormulaSlot()
            old=slot.replace(scene,'2x+5=17',run_time=.1)
            slot.replace(scene,'x=6',run_time=.1);slot.clear(scene,run_time=.1)
            slot.replace(scene,r'2\cdot6+5=17',run_time=.1)
            self.assertNotIn(old,scene.get_mobject_family_members())
            self.assertEqual(len(slot.history),3)

    def test_cantor_lengths_and_nonoverlap_for_several_actual_levels(self):
        for level in range(7):
            intervals=cantor_intervals(level)
            self.assertEqual(len(intervals),2**level)
            self.assertEqual(sum(b-a for a,b in intervals),Fraction(2,3)**level)
            self.assertTrue(all(intervals[i][1]<=intervals[i+1][0] for i in range(len(intervals)-1)))

    def test_triangle_angle_sum_and_degenerate_rejection(self):
        import math
        self.assertAlmostEqual(sum(interior_angles([(0,0),(3,0),(0,2)])),math.pi)
        with self.assertRaises(ValueError):interior_angles([(0,0),(1,0),(2,0)])

    def test_open_convection_path_is_rejected(self):
        self.assertTrue(assert_closed_path([(0,0),(0,1),(1,1),(1,0),(0,0)]))
        with self.assertRaises(ValueError):assert_closed_path([(0,0),(0,1),(1,1),(1,0)])
