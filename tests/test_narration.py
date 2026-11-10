import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

import cv2
import numpy as np

from generation import narration as speech
from generation.lesson_spec import VERSION
from generation.strict_video_contract import make_contract
from generation.strict_manim import inspect_exact
from generation.quality_gate import assess
from eval import narration as judge
from eval.benchmark_operators import narration_presence


class NarrationTests(unittest.TestCase):
    def test_strict_speech_retries_past_third_failure_without_relaxing_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            async def fake_tts(text, voice, path):
                path.write_bytes(b'placeholder')
            tone = (np.sin(np.arange(speech.RATE*12)*.04)*5000).astype('<i2')
            fitting = tone[:speech.RATE*8]
            with patch.object(speech, 'synthesize', side_effect=fake_tts), \
                    patch.object(speech, 'pcm', side_effect=[tone]*3+[fitting]*3), \
                    patch.object(speech, 'repair_text', return_value='Revised speech.') as repair, \
                    patch.object(speech.subprocess, 'run'):
                _, report = speech.attach(root/'video.mp4', self.contract(), root/'audio', api=object())
            self.assertEqual(repair.call_count, 3)
            self.assertEqual(report['chapters'][0]['synthesis_attempt'], 4)
            self.assertTrue(report['valid'])
            self.assertTrue(all(row['tempo_factor'] == 1 for row in report['chapters']))

    def contract(self):
        case={'id':'voice_fixture','lesson_version':VERSION,'target_duration_s':30,
              'prompt_text':'Solve 2x+5=17. Explain and verify the answer.',
              'audio_narration_required':True,'narration_language':'en-US'}
        contract=make_contract(case)
        contract['teaching_timeline']=[{'id':f'step_{i}','start_s':i*10,'end_s':(i+1)*10,
            'goal':f'step {i}','visible_evidence':f'equation state {i}','requirement_ids':['prompt'],
            'narration':text} for i,text in enumerate([
                'We isolate x by keeping the two sides of the equation equal.',
                'Subtract five from both sides, then divide both sides by two.',
                'The answer is six. Substituting it verifies the original equation.'])]
        return contract

    def test_pacing_rejects_silent_too_short_and_overlong_audio(self):
        tone=(np.sin(np.arange(speech.RATE*6)*.04)*5000).astype('<i2')
        self.assertEqual(speech.fit_status(tone,10),'fits')
        self.assertEqual(speech.fit_status(np.zeros(speech.RATE*6,dtype='<i2'),10),'silent')
        self.assertEqual(speech.fit_status(tone[:speech.RATE],10),'too_short')
        self.assertEqual(speech.fit_status(np.tile(tone,2),10),'too_long')

    def test_mux_preserves_video_frames_and_timing_but_tones_do_not_pass_speech_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);video=root/'silent.mp4'
            writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'mp4v'),15,(160,90))
            for i in range(450):
                pixels=np.zeros((90,160,3),dtype=np.uint8);pixels[:,(i//15)%140:(i//15)%140+20]=150;writer.write(pixels)
            writer.release()
            async def fake_tts(text,voice,path):
                # Known non-speech is intentional: this checks mux transport only.
                tone=(np.sin(np.arange(speech.RATE*6)*.04)*5000).astype('<i2')
                with wave.open(str(path),'wb') as handle:
                    handle.setnchannels(1);handle.setsampwidth(2);handle.setframerate(speech.RATE);handle.writeframes(tone.tobytes())
            with patch.object(speech,'synthesize',side_effect=fake_tts):
                target,report=speech.attach(video,self.contract(),root/'audio')
            self.assertTrue(report['valid']);self.assertFalse(report['background_music'])
            self.assertAlmostEqual(report['speech_coverage'],.6)
            self.assertTrue(inspect_exact(target,30)['valid'])
            self.assertTrue(narration_presence(str(target),speech.ffmpeg())['detected'])
            original=cv2.VideoCapture(str(video));final=cv2.VideoCapture(str(target))
            try:
                for _ in range(450):
                    a,x=original.read();b,y=final.read();self.assertTrue(a and b);self.assertTrue(np.array_equal(x,y))
            finally:original.release();final.release()
            gate=assess({'complete':True,'audio_narration_required':True,'narration':report},
                        {'narration':{'detected':True},'scoring':{'valid':True,'strict_pass':True}})
            self.assertFalse(gate['passed']);self.assertIn('actual_speech',gate['failures'])
            self.assertIn('spoken_teaching',gate['failures'])

    def test_overlong_speech_fails_without_truncation_or_a_valid_narrated_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            async def fake_tts(text,voice,path):path.write_bytes(b'placeholder')
            samples=(np.sin(np.arange(speech.RATE*12)*.04)*5000).astype('<i2')
            with patch.object(speech,'synthesize',side_effect=fake_tts),patch.object(speech,'pcm',return_value=samples):
                with self.assertRaisesRegex(ValueError,'too_long'):
                    speech.attach(root/'original.mp4',self.contract(),root/'audio')
            self.assertFalse((root/'audio/narrated.mp4').exists())
            self.assertFalse(json.loads((root/'audio/narration.json').read_text())['valid'])

    def test_draft_small_shortfall_slows_real_audio_without_padding(self):
        samples=(np.sin(np.arange(round(speech.RATE*16.1))*.04)*5000).astype('<i2')
        fitted,factor=speech.fit_draft_speech(samples,20.533333)
        self.assertGreaterEqual(factor,.8)
        self.assertLess(factor,1.)
        self.assertEqual(speech.fit_status(fitted,20.533333),'fits')
        with self.assertRaises(ValueError):
            speech.fit_draft_speech(samples[:speech.RATE],20.533333)

    def test_repair_word_target_uses_measured_voice_speed(self):
        from types import SimpleNamespace
        chapter = {**self.contract()['teaching_timeline'][0], 'end_s':22,
                   'narration':' '.join(['word']*40)}
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"narration":"A revised explanation."}'))])
        with patch('builtins.print'):
            api = __import__('unittest.mock', fromlist=['Mock']).Mock(return_value=(response, {}))
            speech.repair_text(api,chapter,13.73,'too_short','en-US')
        prompt = api.call_args.args[0]
        self.assertIn('approximately 57 words',prompt)
        self.assertNotIn('use at most',prompt)

    def test_missing_script_is_rejected_before_tts(self):
        contract=self.contract();contract['teaching_timeline'][0].pop('narration')
        with tempfile.TemporaryDirectory() as directory,patch.object(speech,'synthesize') as call:
            with self.assertRaises(ValueError):speech.attach('unused.mp4',contract,Path(directory))
            call.assert_not_called()

    def test_real_word_times_limit_what_each_window_hears(self):
        transcript={'segments':[{'id':2,'start_s':0,'end_s':15,'text':'all words',
                    'words':[{'start_s':0,'end_s':1,'word':'before '},
                             {'start_s':5,'end_s':6,'word':'subtract five'},
                             {'start_s':12,'end_s':13,'word':' after'}]}]}
        rows=judge.window_transcript(transcript,4,8)
        self.assertEqual(rows[0]['text'],'subtract five')
        self.assertEqual(rows[0]['start_s'],5)
        self.assertEqual(rows[0]['speech_segment_id'],2)

    def test_audio_weakness_cannot_average_away_and_bad_values_are_invalid(self):
        scoring={'valid':True,'score':100,'strict_pass':True}
        result=judge.apply(scoring,{'valid':True,'passed':False,'score':25,'failures':['wrong spoken value']})
        self.assertEqual(result['score'],25);self.assertFalse(result['strict_pass'])
        for value in (None,True,float('nan'),-1,101):
            result=judge.apply(scoring,{'valid':True,'passed':True,'score':value})
            self.assertFalse(result['valid']);self.assertIsNone(result['score'])

    def test_wrong_language_and_unverified_transcription_cannot_pass(self):
        result=judge.review({'narration_language':'en-US'},{'valid':True,'language':'zh'},[])
        self.assertFalse(result['passed']);self.assertEqual(result['score'],0)
        with self.assertRaises(ValueError):judge.review({}, {'valid':False}, [])

    def test_missing_narration_diagnostics_cannot_crash_or_pass(self):
        result=assess({'complete':False,'audio_narration_required':True,'narration':None},{})
        self.assertIn('narration_generated',result['failures'])

    def test_speech_review_rejects_invented_citations(self):
        raw={'criteria':[{'id':key,'score':4,'finding':'literal spoken evidence',
                         'speech_ids':[99],'window_ids':[0]} for key in judge.CRITERIA],'summary':'fixture'}
        transcript={'valid':True,'language':'en','segments':[{'id':0,'start_s':0,'end_s':3,'text':'x equals six','avg_logprob':-.2}]}
        def ask(messages,schema,validator,**kwargs):return validator(copy.deepcopy(raw))
        with patch.object(judge,'_ask',side_effect=ask),self.assertRaises(ValueError):
            judge.review({'prompt_text':'Solve the equation','narration_language':'en-US'},transcript,[{'id':0}])


if __name__=='__main__':unittest.main()
