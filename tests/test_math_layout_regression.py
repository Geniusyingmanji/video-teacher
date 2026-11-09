import unittest
from manim import Scene,MathTex,Text,tempconfig
from generation.layout_guard import check_layout
from generation.layout_policy import arrange_labels,tag,text_objects


class MathLayoutRegressionTests(unittest.TestCase):
    def test_two_overlaid_real_formulas_are_detected(self):
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene();scene.add(MathTex('f(x)=x^3+2x'),MathTex("f'(x)=3x^2+2"))
            self.assertIn('text_overlap',{r['kind'] for r in check_layout(scene)['failures']})

    def test_one_multiterm_formula_does_not_collide_with_its_own_glyphs(self):
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene();formula=MathTex('2x','+','5','=','17');scene.add(formula)
            self.assertEqual(text_objects(scene.get_mobject_family_members()),[formula])
            self.assertNotIn('text_overlap',{r['kind'] for r in check_layout(scene)['failures']})

    def test_semantic_array_labels_are_not_relocated_by_general_layout(self):
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene();digit=tag(Text('3',font_size=40),'anchored');scene.add(digit)
            before=digit.get_center().copy();arrange_labels(scene,{},[digit])
            self.assertTrue((before==digit.get_center()).all())

    def test_caption_on_heater_is_detected_without_blocking_plain_background(self):
        from manim import Rectangle,RED,BLACK
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene();caption=tag(Text('Warm water rises',font_size=28),'caption')
            scene.add(Rectangle(width=14,height=8,fill_color=BLACK,fill_opacity=1),caption)
            self.assertNotIn('text_occluded_by_geometry',{x['kind'] for x in check_layout(scene)['failures']})
            scene.add(Rectangle(width=4,height=.5,fill_color=RED,fill_opacity=1))
            self.assertIn('text_occluded_by_geometry',{x['kind'] for x in check_layout(scene)['failures']})
