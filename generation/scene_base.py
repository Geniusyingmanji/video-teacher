"""A compact standalone scene base without the upstream crowded fixed grid."""
BASE = '''class TeachingScene(Scene):
    def setup_layout(self, title_text, lecture_lines):
        self.camera.background_color = BLACK
        self.title = Text(title_text, font_size=32).to_edge(UP, buff=.2)
        self.add(self.title)
        # Notes are optional and must not substitute for the actual demonstration.
        notes = [Text(line, font_size=26) for line in lecture_lines]
        if notes:
            self.lecture = VGroup(*notes).arrange(DOWN, aligned_edge=LEFT, buff=.15)
            self.lecture.to_corner(DL, buff=.25)
            self.add(self.lecture)
'''
