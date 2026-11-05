import unittest
from generation.layout_policy import source_panels, place_box, overlaps
from generation.lesson_codegen import validate_source_ownership


class LayoutPolicyTests(unittest.TestCase):
    def test_portrait_and_landscape_get_disjoint_panels_below_title(self):
        for size in [(678,717),(1920,1080),(400,1200),(1000,400)]:
            source,teaching=source_panels(size)
            self.assertGreaterEqual(source[1],.15)
            self.assertFalse(overlaps(source,teaching))
            self.assertTrue(all(0<=v<=1 for v in source+teaching))

    def test_colliding_labels_move_nearest_without_shrinking(self):
        occupied=[[1,-.3,2,.1]]
        box=[1.5,-.2,1.8,.2]
        placed=place_box(box,[-5,-2,5,2],occupied)
        self.assertIsNotNone(placed)
        self.assertFalse(overlaps(placed,occupied[0],.119))
        self.assertAlmostEqual(placed[2]-placed[0],.3)
        self.assertAlmostEqual(placed[3]-placed[1],.4)

    def test_clear_labels_stay_and_overflow_returns_no_fake_solution(self):
        box=[0,0,1,1]
        self.assertEqual(place_box(box,[-2,-2,2,2],[]),box)
        self.assertIsNone(place_box(box,[0,0,.5,.5],[]))
        self.assertIsNone(place_box(box,[0,0,1,1],[[0,0,1,1]]))

    def test_source_ownership_rejects_duplicate_image_construction(self):
        for code in ['image=ImageMobject("source.png")','image=manim.ImageMobject(path)',
                     'source=self.source_image\nsource.scale(.5)',
                     'source=self.source_image\nself.play(Indicate(source))']:
            with self.assertRaisesRegex(ValueError,'Runtime owns'):
                validate_source_ownership(code)
        validate_source_ownership('source=self.source_image\nanswer=self.source_text("0.8",[1,2,3,4])')

    def test_runtime_keeps_reference_labels_fixed_and_separates_explanations(self):
        from manim import Scene,Text,tempconfig,config
        from generation.layout_policy import arrange_labels,tag,scene_box,panel_box
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene()
            fixed=tag(Text('0.8').move_to([-2,0,0]),'source')
            axis=Text('Principal axis',font_size=20).move_to([1.5,-.25,0])
            focal=Text('F',font_size=28).move_to([2,-.25,0])
            scene.add(fixed,axis)
            original=scene_box(fixed)
            changes=arrange_labels(scene,{},[focal])
            self.assertTrue(changes)
            self.assertFalse(overlaps(scene_box(axis),scene_box(focal),.119))
            self.assertEqual(scene_box(fixed),original)
            source,panel=source_panels((678,717))
            misplaced=Text('Verification',font_size=24).move_to([-5,-3.8,0])
            arrange_labels(scene,{'teaching_panel':panel},[misplaced])
            box=scene_box(misplaced);bounds=panel_box(panel,config.frame_width,config.frame_height)
            self.assertGreaterEqual(box[0],bounds[0]-.001)
            self.assertGreaterEqual(box[1],bounds[1]-.001)

    def test_long_explanations_wrap_without_losing_words_or_shrinking(self):
        from manim import Text,tempconfig,config
        from generation.layout_policy import prepare_text
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            for sentence in ['Find missing values so outgoing probabilities sum to one.',
                             'Subtract the known probability from one and check each outgoing total.']:
                label=Text(sentence,font_size=22)
                prepare_text(label,5.0)
                self.assertLessEqual(label.width,5.001)
                self.assertEqual(label.original_text.split(),sentence.split())
                self.assertIn('\n',label.original_text)

    def test_collision_handling_covers_equations_nodes_and_panel_overflow(self):
        from manim import Scene,Text,tempconfig
        from generation.layout_policy import arrange_labels,scene_box
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            for labels in [('F','Principal axis'),('A','B','C','D'),('2x + 5 = 17','2x = 12','x = 6')]:
                scene=Scene()
                objects=[Text(label,font_size=24).move_to([0,0,0]) for label in labels]
                scene.add(*objects)
                arrange_labels(scene,{})
                for i,obj in enumerate(objects):
                    for other in objects[:i]:
                        self.assertFalse(overlaps(scene_box(obj),scene_box(other),.119))

    def test_duplicate_images_and_text_covering_source_are_detected(self):
        import numpy as np
        from manim import Scene,Text,ImageMobject,tempconfig
        from generation.layout_guard import check_layout
        with tempconfig({'pixel_width':854,'pixel_height':480}):
            scene=Scene()
            image=ImageMobject(np.full((120,100,3),255,dtype=np.uint8))
            scene.source_image=image
            scene.add(image,ImageMobject(np.full((60,50,3),255,dtype=np.uint8)),Text('Note',font_size=30))
            kinds={f['kind'] for f in check_layout(scene)['failures']}
            self.assertIn('image_overlap',kinds)
            self.assertIn('text_over_source',kinds)

    def test_source_codegen_repairs_duplicate_before_rendering(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from PIL import Image
        from generation.strict_video_contract import ContractAPI,make_contract
        from generation.lesson_spec import VERSION
        case={'id':'layout_fixture','lesson_version':VERSION,'target_duration_s':60,'audio_narration_required':True,'prompt_text':'Complete the source diagram.'}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);image=root/'source.png';Image.new('RGB',(100,120),'white').save(image)
            contract=make_contract(case,image)
            values=[]
            for code in ['image=ImageMobject("source.png")','image=self.source_image']:
                response=Mock();response.choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=code))]
                response.model_dump_json.return_value='{}';response.usage=None;values.append(response)
            with patch('openai.OpenAI') as client,patch('generation.prompt_budget.request_budget',side_effect=lambda text,tokens,images:(tokens,{})):
                create=client.return_value.chat.completions.create;create.side_effect=values
                result,_=ContractAPI(contract,root)('Write complete runnable Manim CE Python code only.')
                self.assertEqual(create.call_count,2)
                self.assertEqual(result.choices[0].message.content,'image=self.source_image')
                self.assertIn('Runtime owns',create.call_args.kwargs['messages'][-1]['content'])
