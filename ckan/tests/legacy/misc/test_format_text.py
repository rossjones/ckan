import ckan.lib.helpers as h

class TestFormatText:

    def test_markdown(self):
        instr = '''# Hello World

**Some bolded text.**

*Some italicized text.*
'''
        exp = '''<h1>Hello World</h1>
<p><strong>Some bolded text.</strong>
</p>
<p><em>Some italicized text.</em>
</p>'''
        out = h.render_markdown(instr)
        assert out == exp

    def test_markdown_blank(self):
        instr = None
        out = h.render_markdown(instr)
        assert out == ''

    def test_evil_markdown(self):
        instr = 'Evil <script src="http://evilserver.net/evil.js";>'
        exp = '''<p>Evil \n</p>'''
        out = h.render_markdown(instr)
        assert out == exp, out

