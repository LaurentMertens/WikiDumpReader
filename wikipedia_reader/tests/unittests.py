import unittest
from wikipedia_reader.wikipedia_reader import WikipediaReader


class TestWikipediaReader(unittest.TestCase):
    def test_convert_html_ents(self):
        text = "' ' = &nbsp;\n" \
               "< = &lt;\n" \
               "> = &gt;\n"\
               "& = &amp;\n"\
               "\" = &quot;\n"\
               "' = &apos;\n"\
               "¢ = &cent;\n"\
               "£ = &pound;\n"\
               "¥ = &yen;\n"\
               "€ = &euro;\n"\
               "© = &copy;\n"\
               "® = &reg;\n"\
               "''this is wiki for italic'', and this is '''bold''', and this is '''''both'''''."
        target = "' ' =  \n" \
                 "< = <\n" \
                 "> = >\n"\
                 "& = &\n"\
                 "\" = \"\n"\
                 "' = '\n"\
                 "¢ = ¢\n"\
                 "£ = £\n"\
                 "¥ = ¥\n"\
                 "€ = €\n"\
                 "© = ©\n"\
                 "® = ®\n" \
                 "this is wiki for italic, and this is bold, and this is both."

        self.assertEqual(target, WikipediaReader.convert_html_ents_etc(text))

    def test_process_links(self):
        text = "This sentence contains a [[hyperlink|link]]. This one [[too]]. This one doesn't.\n" \
               "This one is [[badly_closed|badly closed], let's see what gives.\n" \
               "This is another [[badly closed] one, followed by a [[correct one]].\n" \
               "This is a [[link with [brackets] inside]]."

        target = "This sentence contains a link. This one too. This one doesn't.\n" \
                 "This one is badly closed, let's see what gives.\n" \
                 "This is another badly closed one, followed by a correct one.\n" \
                 "This is a link with [brackets] inside."

        self.assertEqual(target, WikipediaReader.process_links(text))

    def test_remove_categories(self):
        text = "Here be some text." + \
               "\n[[Category:Some Wikipedia category]]" + \
               "\n[[Category:Some other Wikipedia category]]" + \
               "\n[[category:Even some other Wikipedia category]]" + \
               "\nHere be some other text."
        target = "Here be some text." + \
                 "\n\n\n\nHere be some other text."
        self.assertEqual(target, WikipediaReader.remove_categories(text))
        self.assertEqual('This string has no categories',
                         WikipediaReader.remove_categories('This string has no categories'))

    def test_remove_comments(self):
        text = "This is a string <!-- a comment! --> containing an HTML style comment.\n" \
               "Actually, it even <!-- another comment! --> has two comments!"
        target = "This is a string  containing an HTML style comment.\n" \
                 "Actually, it even  has two comments!"
        self.assertEqual(target, WikipediaReader.remove_comments(text))
        self.assertEqual('This string has no comments', WikipediaReader.remove_comments('This string has no comments'))
        self.assertEqual('A comment !',
                         WikipediaReader.remove_comments('A comment <!-- within <!-- a comment --> -->!'))

    def test_remove_curlies(self):
        text = "'''Irwin Allen Ginsberg''' ({{ here be something {{IPAc-en|ˈ|ɡ|ɪ|n|z|b|ɜːr|ɡ}} followed by}}; June 3"
        target = "'''Irwin Allen Ginsberg''' (; June 3"
        self.assertEqual(target, WikipediaReader.remove_dbl_curlies(text))
        self.assertEqual('This string has no curlies',
                         WikipediaReader.remove_dbl_curlies('This string has no curlies'))

        text = """{{short description|American poet and philosopher}}
{{Use mdy dates|date=October 2019}}
{{Infobox writer <!-- for more information see [[:Template:Infobox writer/doc]] -->
| name        = Allen Ginsberg
| image       = Allen Ginsberg 1979 - cropped.jpg
| caption     = Ginsberg in 1979
| birth_name  = Irwin Allen Ginsberg
| birth_date  = {{Birth date|1926|06|03|mf=y}}
| birth_place = [[Newark, New Jersey]], U.S. 
| death_date  = {{death date and age|1997|04|05|1926|06|03|mf=y}}
| death_place = [[New York City]], U.S.<!-- The purpose of geographical descriptions is to unambiguously identify the place. There are no other New York Cities in the world -->
| education   = [[Columbia University]] (B.A.)
| partner     = [[Peter Orlovsky]] (1954–1997; Ginsberg's death)
| occupation  = Writer, poet
| movement    = [[Beat Generation|Beat literature, hippie]]<br />[[Confessional poetry]]
| awards      = [[National Book Award]] (1974)<br />[[Robert Frost Medal]] (1986)
| signature   = Allen Ginsberg signature.svg
}}"""
        target = "\n\n"
        self.assertEqual(target, WikipediaReader.remove_dbl_curlies(text))

    def test_remove_extra_blank_lines(self):
        text = "This is a\ntext over several\n\n\nlines.\n\n"
        target_1 = "This is a\ntext over several\nlines.\n"
        target_2 = "This is a\ntext over several\n\nlines.\n\n"
        self.assertEqual(target_1, WikipediaReader.remove_blank_lines(text, max_sqns=1))
        self.assertEqual(target_2, WikipediaReader.remove_blank_lines(text, max_sqns=2))

    def test_remove_files(self):
        text = "[[File:Prabhupada's arrival in San Francisco 1967.jpg|thumb|left|Allen Ginsberg's greeting [[A. C. " \
               "Bhaktivedanta Swami Prabhupada]] at [[San Francisco International Airport]]. January 17, 1967]]"
        target = ""
        self.assertEqual(target, WikipediaReader.remove_files(text))

    def test_remove_font(self):
        text = "This line contains a <font color=blabla>FONT</font> statement."
        target = "This line contains a  statement."
        self.assertEqual(target, WikipediaReader.remove_font(text))

    def test_remove_header(self):
        self.assertEqual('Header', WikipediaReader.remove_headers('= Header ='))
        self.assertEqual('Header', WikipediaReader.remove_headers('== Header =='))
        self.assertEqual('Header', WikipediaReader.remove_headers('==Header=='))
        self.assertEqual('Header', WikipediaReader.remove_headers('==Header =='))
        self.assertEqual('', WikipediaReader.remove_headers('==Header ==', b_delete=True))
        self.assertEqual('Header\nHihihi', WikipediaReader.remove_headers('=== Header   ===\nHihihi'))

    def test_remove_lists(self):
        text = "This is a line followed by a list.\n" + \
               "* A list item\n" + \
               "# Another list item\n" + \
               "## A deeper list item\n" + \
               "A line inbetween lists.\n" + \
               "* Yet another list item\n" + \
               ":An indented line...\n" + \
               "A final line"
        target_keep = "This is a line followed by a list.\n" + \
                      "A list item\n" + \
                      "Another list item\n" + \
                      "A deeper list item\n" + \
                      "A line inbetween lists.\n" + \
                      "Yet another list item\n" + \
                      "An indented line...\n" + \
                      "A final line"
        target_del = "This is a line followed by a list.\n" + \
                     "A line inbetween lists.\n" + \
                     "A final line"
        self.assertEqual(target_keep, WikipediaReader.remove_lists_and_indents(text, b_delete=False))
        self.assertEqual(target_del, WikipediaReader.remove_lists_and_indents(text, b_delete=True))

    def test_remove_refs(self):
        text = "Ginsberg took part in decades of political protest against everything from the [[Vietnam War]] " + \
               "to the War on Drugs.<ref>Ginsberg, Allen ''Deliberate Prose'', the foreword by Edward Sanders, " + \
               "p. xxi.</ref> His poem \"September on Jessore Road\" called attention..."
        target = "Ginsberg took part in decades of political protest against everything from the [[Vietnam War]] " + \
               "to the War on Drugs. His poem \"September on Jessore Road\" called attention..."

        self.assertEqual(target, WikipediaReader.remove_refs(text))
        self.assertEqual('This string has no refs',
                         WikipediaReader.remove_dbl_curlies('This string has no refs'))
