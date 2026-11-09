import unittest
from generation.strict_manim import allocate_chapter_frames


class ChapterAllocationTests(unittest.TestCase):
    def test_uneven_authored_chapters_still_match_each_spoken_boundary(self):
        chapters=[{'id':str(i),'start_s':i*10,'end_s':(i+1)*10} for i in range(3)]
        events=[('play',2),('wait',3),('play',5),('wait',8),('play',4),('wait',1)]
        markers=[{'id':str(i),'event_index':i*2} for i in range(3)]
        values=allocate_chapter_frames(events,markers,chapters,15)
        self.assertEqual([sum(values[:i]) for i in (0,2,4,6)],[0,150,300,450])
        self.assertEqual(values[-1],15)

    def test_source_hold_uses_same_time_origin_as_speech(self):
        chapters=[{'id':str(i),'start_s':i*10,'end_s':(i+1)*10} for i in range(3)]
        events=[('wait',1),('play',2),('wait',3),('play',5),('wait',8),('play',4),('wait',1)]
        markers=[{'id':str(i),'event_index':1+i*2} for i in range(3)]
        values=allocate_chapter_frames(events,markers,chapters,15,True)
        self.assertEqual([sum(values[:i]) for i in (1,3,5,7)],[15,150,300,450])

    def test_missing_or_reordered_chapter_is_rejected(self):
        with self.assertRaises(ValueError):
            allocate_chapter_frames([('play',1),('wait',1)],[],[{'id':'a','start_s':0,'end_s':10}],15)
