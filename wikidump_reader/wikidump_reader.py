# Check: https://www.heatonresearch.com/2017/03/03/python-basic-wikipedia-parsing.html
# Check: from https://effbot.org/zone/element-iterparse.htm
import bz2
import os
import xml.etree.ElementTree as etree


class WikiDumpReader:
    PREFIX = "{http://www.mediawiki.org/xml/export-0.10/}"
    MAX_LINK_LENGTH = 500
    HTML_ENTS = {'&nbsp;': ' ', '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&apos;': "'",
                 '&cent;': '¢', '&pound;': '£', '&yen;': '¥', '&euro;': '€', '&copy;': '©', '&reg;': '®'}
    REMOVE_LINE_STARTS = {'*', '#', ':'}

    def __init__(self, b_bz2=True,
                 prefix=PREFIX):
        self.b_bz2 = b_bz2
        self.prefix = prefix
        self.len_prefix = len(self.prefix)

    def _open(self, file):
        if self.b_bz2:
            return bz2.open(file)
        else:
            return open(file, 'rb')

    def read(self, file):
        with self._open(file) as fin:
            # get an iterable
            context = etree.iterparse(fin, events=("start", "end"))

            # turn it into an iterator
            context = iter(context)

            # get the root element
            event, root = next(context)

            for event, elem in context:
                if event == 'end':
                    yield elem
                    root.clear()

    def read_tag(self, file, tag='page'):
        with self._open(file) as fin:
            # get an iterable
            context = etree.iterparse(fin, events=("start", "end"))

            # turn it into an iterator
            context = iter(context)

            # get the root element
            event, root = next(context)

            for event, elem in context:
                _tag = elem.tag[self.len_prefix:]
                if event == 'end':
                    if _tag == tag:
                        yield elem
                    root.clear()

    def read_page(self, file,
                  b_ignore_category=False,
                  b_ignore_disamb=False,
                  b_ignore_redirs=False,
                  b_ignore_template=False,
                  b_ignore_wikipedia=False,
                  min_chars=0):
        """
        Convenience method that will return the text of an article

        :param file:
        :param b_ignore_category: ignore category pages
        :param b_ignore_disamb: ignore pages that have '(disambiguation)' in their title; this does not catch all
        disambiguation pages
        :param b_ignore_redirs: ignore redirect pages
        :param b_ignore_template: ignore template pages
        :param b_ignore_wikipedia: ignore 'Wikipedia:' pages
        :param min_chars: min number of characters a text should have; if less, article will be skipped
        :return:
        """
        with self._open(file) as fin:
            # get an iterable
            context = etree.iterparse(fin, events=("start", "end"))

            # turn it into an iterator
            context = iter(context)

            # get the root element
            event, root = next(context)

            for event, elem in context:
                _tag = elem.tag[self.len_prefix:]
                if event == 'end':
                    if _tag == 'page':
                        page_title = self.get_page_title(elem)

                        if b_ignore_category and page_title.startswith("Category:"):
                            continue
                        elif b_ignore_disamb and page_title.endswith("(disambiguation)"):
                            continue
                        elif b_ignore_template and page_title.startswith("Template:"):
                            continue
                        elif b_ignore_wikipedia and page_title.startswith("Wikipedia:"):
                            continue
                        try:
                            page_text = self.get_page_text(elem)
                            # This actually happens, sometimes...
                            if page_text is None:
                                continue
                            if b_ignore_redirs and len(page_text) > 9 and page_text[:9].lower() == "#redirect":
                                continue
                            if len(page_text) < min_chars:
                                continue

                        except ValueError as e:
                            print(e)
                            continue

                        yield page_title, page_text
                    root.clear()

    @classmethod
    def get_page_text(cls, page):
        return page.find(cls.PREFIX + 'revision').find(cls.PREFIX + 'text').text

    @classmethod
    def get_page_title(cls, page):
        return page.find(cls.PREFIX + 'title').text

    @classmethod
    def process_links(cls, text: str, title="N/A"):
        """
        Process links of type [[link|target]] to remove the square brackets and keep only the target value.

        :param text:
        :return: processed text
        """
        tag_open, tag_close, alt_close = "[[", "]]", "]"
        len_tag_open = len(tag_open)
        len_tag_close = len(tag_close)
        len_alt_close = len(alt_close)
        # end = -len_tag_close
        start = text.find(tag_open)
        # No links found
        if start < 0:
            return text

        while start >= 0:
            # Look for end of link
            end = text.find(tag_close, start)
            # There's an alt end between start and end?
            end_alt = text.find(alt_close, start, end)
            # With no matching open?
            b_alt = False
            if end_alt > -1:
                alt_cnts = text.count('[', start+len_tag_open, end_alt)
                if alt_cnts == 0:
                    # print("Alt_end seems more appropriate... Taking alt end.")
                    b_alt = True
                    end = end_alt
            end_offset = len_alt_close if b_alt else len_tag_close

            b_error = False
            if end == -1:
                print("No closing tag found for link. Skipping...")
                print("-----")
                print(text[start:start+50])
                print("-----")
                print(f"Article: [{title}]")
                b_error = True

            # Check this closing tag is indeed the closing tag corresponding to the used opening tag position
            cnt = text.count(tag_open, start+len_tag_open, end)
            # If not, go looking for the appropriate closing tag
            if cnt > 0:
                while end > -1 and cnt > 0:
                    prev_end = end + end_offset
                    end = text.find(tag_close, prev_end)
                    # Were there extra starts?
                    cnt += text.count(tag_open, prev_end, end)
                    cnt -= 1
                if end == -1:
                    msg = f"Link appears unproperly closed, skipping...\nStart of problem: "\
                          f"[{text[start:start + 250 if start + 250 < len(text) else len(text)]}]"\
                          f"\nArticle: [{title}]"
                    print(msg)
                    b_error = True
            if b_error:
                start = text.find(tag_open, start+len_tag_open)
                continue

            # Check for '|'
            cnt = text.count('|', start, end)
            if cnt > 1:
                # print(f"Don't know what to do with following text:\n\"{text[start:end+len_tag_close]}\"")
                start = start + len_tag_open
            elif cnt == 1:
                text = text[:start] + text[text.find('|', start)+1:end] + text[end+end_offset:]
            else:
                text = text[:start] + text[start+len_tag_open:end] + text[end+end_offset:]

            # Update start position
            start = text.find(tag_open, start)

        return text

    # ############################################################
    # Remove stuff between tags
    # ############################################################
    @classmethod
    def remove_categories(cls, text: str, title="N/A"):
        """
        Remove categories from Wiki code.

        :param text:
        :return: processed text
        """
        text = cls.remove_tag(text, tag_open='[[Category:', tag_close=']]', title=title)
        text = cls.remove_tag(text, tag_open='[[category:', tag_close=']]', title=title)
        return text

    @classmethod
    def remove_comments(cls, text: str, title="N/A"):
        """
        Remove html-style comments from a text.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='<!--', tag_close='-->', title=title)

    @classmethod
    def remove_curlies(cls, text: str, title="N/A"):
        """
        Remove stuff between single curly brackets.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='{', tag_close='}', title=title)

    @classmethod
    def remove_dbl_curlies(cls, text: str, title="N/A"):
        """
        Remove stuff between double curly brackets.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='{{', tag_close='}}', alt_close='}', title=title)

    @classmethod
    def remove_files(cls, text: str, title="N/A"):
        """
        Remove references to files.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='[[File:', tag_close=']]', alt_open='[[', title=title)

    @classmethod
    def remove_font(cls, text: str, title="N/A"):
        """
        Remove font tags.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='<font', tag_close='</font>', title=title)

    @classmethod
    def remove_images(cls, text: str, title="N/A"):
        """
        Remove references to images.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='[[Image:', tag_close=']]', alt_open='[[', title=title)

    @classmethod
    def remove_math(cls, text: str, title="N/A"):
        """
        Remove math environments.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='<math', tag_close='</math>', title=title)

    @classmethod
    def remove_nowiki(cls, text: str, title="N/A"):
        """
        Remove nowiki environments.

        :param text:
        :return: processed text
        """
        # Many times their is only one tag, "<nowiki/>". This is taken care of by the second clause.
        text = cls.remove_tag(text, tag_open='<nowiki>', tag_close='</nowiki>', title=title)
        text = cls.remove_tag(text, tag_open='<nowiki', tag_close='/>', title=title)
        return text

    @classmethod
    def remove_pre(cls, text: str, title="N/A"):
        """
        Remove pre environments.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='<pre', tag_close='</pre>', title=title)

    @classmethod
    def remove_refs(cls, text: str, title="N/A"):
        """
        Remove references.

        :param text:
        :return: processed text
        """
        text = cls.remove_tag(text, tag_open='<ref>', tag_close='</ref>', title=title)
        text = cls.remove_tag(text, tag_open='<ref ', tag_close='</ref>', alt_close='/>', title=title)
        return text

    @classmethod
    def remove_source(cls, text: str, title="N/A"):
        """
        Remove source environments.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='<source', tag_close='</source>', title=title)

    @classmethod
    def remove_sub(cls, text: str, title="N/A"):
        """
        Remove sub tags.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='<sub>', tag_close='</sub>', title=title)

    @classmethod
    def remove_sup(cls, text: str, title="N/A"):
        """
        Remove sup tags.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='<sup>', tag_close='</sup>', title=title)

    @classmethod
    def remove_dbl_sqbrackets(cls, text: str, title="N/A"):
        """
        Remove stuff between double square brackets. Note that this will remove all hyperlinks. If you want to simply
        process hyperlinks to only keep their target value, use "process_links" instead.

        :param text:
        :return: processed text
        """
        return cls.remove_tag(text, tag_open='[[', tag_close=']]', title=title)


    @classmethod
    def remove_tag(cls, text: str, tag_open: str, tag_close: str, alt_open: str = None, alt_close: str = '',
                   b_crash=True, title='N/A'):
        """
        Remove parts from a text enclosed between the specified opening and closing tags.

        :param text:
        :param tag_open: opening tag
        :param tag_close: closing tag
        :param alt_open: alternative opening tag, that is contained between opening and closing tag should count as
        an opening tag; this is, e.g., necessary when cleaning up stuff like
        '[[File: description contains [[a link]] which would mess up code otherwise]]'
            -> tag_open="[[File:", alt_open="[["
        :param alt_close: alternative closing tag, if tag_close is not found, revert to looking for alt_close;
        useful for stuff like "<ref name=..." refs that can be closed either by "</ref>" or "/>".
        :param b_crash: crash if a tag seems to not be closed correctly
        :param title: the title of the Wikipedia page being processed; only used for error messaging
        :return: processed text
        """
        if alt_open is None:
            alt_open = tag_open
        len_tag_open = len(tag_open)
        len_tag_close = len(tag_close)
        len_tag_alt_close = len(alt_close)
        end = 0
        start = text.find(tag_open)
        # No tags found
        if start < 0:
            return text

        res = ''

        prev_start = 0
        while start >= 0:
            # Update filtered text
            # print("Cutting out:")
            # print(text[prev_start:end])
            # print("************************************************************")
            res += text[end:start]

            # Update end position (that is, look for closing tag)
            end = text.find(tag_close, start)

            b_alt = False
            if alt_close:
                alt_end = text.find(alt_close, start)
                if alt_end > 0 and (alt_end < end) or end < 0:
                    b_alt = True
                    end = alt_end
            # Check this closing tag is indeed the closing tag corresponding to the used opening tag position
            cnt = text.count(alt_open, start+len_tag_open, end)
            # If not, go looking for the appropriate closing tag
            if cnt > 0:
                while end > -1 and cnt > 0:
                    prev_end = end + (len_tag_alt_close if b_alt else len_tag_close)
                    end = text.find(tag_close, prev_end)
                    # Were there extra starts?
                    cnt += text.count(alt_open, prev_end, end)
                    cnt -= 1
                if end == -1:
                    msg = f"Text contains a tag (open: '{tag_open}', close: '{tag_close}') "\
                          f"that wasn't properly closed.\nStart of problem: "\
                          f"[{text[start:start + 250 if start + 250 < len(text) else len(text)]}]"\
                          f"\nArticle: [{title}]"
                    if b_crash:
                        raise ValueError(msg)
                    else:
                        print(msg)
                        end = start + len_tag_open

            # Update start position
            # prev_start = start
            start = text.find(tag_open, end)

            # Offset end position
            end = end + (len_tag_alt_close if b_alt else len_tag_close)

        # Don't forget last part!
        res += text[end:]

        return res

    # ############################################################
    # Remove extra blank lines and lists, and clean up headings
    # Also, drop everything from "==See Also==" and/or
    # "==References==
    # ############################################################
    @classmethod
    def cut_bottom(cls, text):
        """
        Remove everything from "==See Also==" or "==References==" or some other

        :param text:
        :return:
        """
        prev_break = -1
        next_break = text.find('\n', prev_break+1)
        res = ''
        b_stop = False
        while next_break >= 0:
            line = text[prev_break+1:next_break+1]
            if line.startswith('==') and line.endswith('==\n'):
                heading = line[2:-3].strip().lower()
                if heading == 'see also' or heading == "references"\
                        or heading == 'external links':
                    b_stop = True
                    break
            res += line

            prev_break = next_break
            next_break = text.find('\n', prev_break+1)

        if not b_stop:
            res += text[prev_break+1:]

        return res

    @classmethod
    def remove_blank_lines(cls, text, max_sqns=2):
        """
        Remove succesive blank lines.

        :param text: text to process
        :param max_sqns: maximum length of sequence of linebreaks to keep
        :return: processed text
        """
        prev_break = 0
        next_break = text.find('\n', prev_break)
        res = ''

        nb_breaks = 0
        while next_break >= 0:
            if not next_break - prev_break == 1:
                res += text[prev_break:next_break]
                nb_breaks = 1
            else:
                nb_breaks += 1
                if nb_breaks <= max_sqns:
                    res += text[prev_break:next_break]

            prev_break = next_break
            next_break = text.find('\n', prev_break+1)
        res += text[prev_break:]

        return res

    @classmethod
    def remove_headers(cls, text, b_delete=False):
        """
        Remove headers, e.g., '=== See also ==='.
        If b_replace = True, then replace them by there textual content, e.g., "See also". Else, ignore the line.

        :param text:
        :param b_delete: keep the header title or not?
        :return:
        """
        prev_break = -1
        next_break = text.find('\n', prev_break+1)
        res = ''
        while next_break >= 0:
            line = text[prev_break+1:next_break+1]
            if line.startswith('=') and line.endswith('=\n'):
                line = '' if b_delete else cls._remove_header(line)
            res += line

            prev_break = next_break
            next_break = text.find('\n', prev_break+1)

        # Don't forget last line!
        line = text[prev_break+1:]
        if line.startswith('=') and line.endswith('='):
            line = '' if b_delete else cls._remove_header(line)

        res += line

        return res

    @staticmethod
    def _remove_header(line):
        b_newline = (line[-1] == '\n')

        # Get heading level
        lvl = 0
        for c in line:
            if c == '=':
                lvl += 1
            else:
                break

        line = line[lvl:-(lvl + (1 if b_newline else 0))].strip()
        if b_newline:
            line += '\n'

        return line

    @classmethod
    def convert_html_ents_etc(cls, text):
        """
        Convert html entities to the value they represent, and remove "''" and "'''", i.e., Wiki codes for
        bold and italic.

        We create our method instead of using 'str.replace()' so we can replace all entities at once.

        :param text:
        :return:
        """
        buffer = ''
        res = ''

        b_in = False
        b_html = False
        for c in text:
            if b_in:
                if b_html:
                    # Another '&'? Reset buffer!
                    if c == '&':
                        res += buffer
                        buffer = '&'
                        continue

                    buffer += c
                    # End of entity
                    if c == ';':
                        if buffer in cls.HTML_ENTS:
                            res += cls.HTML_ENTS[buffer]
                        else:
                            res += buffer
                        b_in = False
                    # No point in looking further
                    # Largest html ent is 7 characters long
                    elif len(buffer) == 7:
                        b_in = False
                        res += buffer
                else:
                    if c == "'":
                        buffer += c
                    else:
                        if len(buffer) == 1:
                            res += buffer
                        res += c
                        b_in = False
            elif c == '&':
                b_in = True
                b_html = True
                buffer = c
            elif c == "'":
                b_in = True
                b_html = False
                buffer = c
            else:
                res += c

        return res

    @classmethod
    def remove_table_lines(cls, text):
        """
        Remove lines starting with '|'.

        :param text:
        :return:
        """
        prev_break = -1
        next_break = text.find('\n', prev_break+1)
        res = ''
        while next_break >= 0:
            line = text[prev_break+1:next_break+1]
            b_ok = True
            for c in line:
                # Ignore leading whitespaces, we're looking for the first non-ws character
                if c == ' ':
                    continue
                else:
                    b_ok = (c != '|')
                    break

            if b_ok:
                res += line

            prev_break = next_break
            next_break = text.find('\n', prev_break+1)

        # We will assume the last line does not start with '|'...
        res += text[prev_break+1:]

        return res

    @classmethod
    def remove_lists_and_indents(cls, text, b_delete=False):
        """
        Remove lists. List items are lines starting with '*' (no numbering) or '#' (numbering).
        Also remove indents -> line starts with ':'.

        :param text: text to process
        :param b_delete: delete lines
        :return: processed text
        """
        prev_break = -1
        next_break = text.find('\n', prev_break+1)
        res = ''
        while next_break >= 0:
            line = text[prev_break+1:next_break+1]
            while line and line[0] in cls.REMOVE_LINE_STARTS:
                line = '' if b_delete else line[1:].lstrip()

            res += line

            prev_break = next_break
            next_break = text.find('\n', prev_break+1)
        res += text[prev_break+1:]

        return res

    @classmethod
    def remove_paragraphs(cls, text):
        """
        Remove paragraphs. Paragraphs are lines starting with ';'

        :param text: text to process
        :return: processed text
        """
        prev_break = -1
        next_break = text.find('\n', prev_break+1)
        res = ''
        while next_break >= 0:
            line = text[prev_break+1:next_break+1]
            if not line[0] == ';':
                res += line

            prev_break = next_break
            next_break = text.find('\n', prev_break+1)
        res += text[prev_break+1:]

        return res

    # ############################################################
    # Combine methods
    # ############################################################
    @classmethod
    def clean(cls, text, title='N/A', b_debug=False):
        """

        :param text:
        :param title: Title of the Wikipedia article the text belongs to; only used for debugging/error reporting
        :return: cleaned text
        """
        if b_debug:
            print("Cutting off bottom...")
        text = cls.cut_bottom(text)
        if b_debug:
            print("Removing comments...")
        text = cls.remove_comments(text, title=title)
        if b_debug:
            print("Removing nowiki...")
        text = cls.remove_nowiki(text, title=title)
        if b_debug:
            print("Removing pre...")
        text = cls.remove_pre(text, title=title)
        if b_debug:
            print("Removing refs...")
        text = cls.remove_refs(text, title=title)
        if b_debug:
            print("Removing sub...")
        text = cls.remove_sub(text, title=title)
        if b_debug:
            print("Removing sup...")
        text = cls.remove_sup(text, title=title)
        if b_debug:
            print("Removing math...")
        # Remove math before curlies!
        text = cls.remove_math(text, title=title)
        if b_debug:
            print("Removing font...")
        text = cls.remove_font(text, title=title)
        if b_debug:
            print("Removing source...")
        text = cls.remove_source(text, title=title)
        if b_debug:
            print("Removing double curlies...")
        text = cls.remove_dbl_curlies(text, title=title)
        if b_debug:
            print("Removing single curlies...")
        text = cls.remove_curlies(text, title=title)
        if b_debug:
            print("Removing table lines...")
        text = cls.remove_table_lines(text)
        if b_debug:
            print("Removing categories...")
        text = cls.remove_categories(text, title=title)
        if b_debug:
            print("Removing files...")
        # Removing files should be done BEFORE processing links! Otherwise, the opening tags get confused.
        text = cls.remove_files(text, title=title)
        if b_debug:
            print("Removing images...")
        # Removing images should be done BEFORE processing links! Otherwise, the opening tags get confused.
        text = cls.remove_images(text, title=title)
        if b_debug:
            print("Processing links...")
        text = cls.process_links(text, title=title)
        if b_debug:
            print("Removing double squares...")
        text = cls.remove_dbl_sqbrackets(text, title=title)

        if b_debug:
            print("Convert html entities and wiki italic etc...")
        text = cls.convert_html_ents_etc(text)
        if b_debug:
            print("Removing headers...")
        text = cls.remove_headers(text)
        if b_debug:
            print("Removing lists...")
        text = cls.remove_lists_and_indents(text)
        if b_debug:
            print("Removing paragraphs...")
        text = cls.remove_paragraphs(text)
        if b_debug:
            print("Removing blank lines...")
        text = cls.remove_blank_lines(text, max_sqns=1)

        return text

    # todo: method to replace links by their text
    # todo: method to replace headers by their text


if __name__ == '__main__':
    HOME = os.path.expanduser("~")
    DATA_DIR = os.path.join(HOME, "Work", "Projects", "STDL", "Data", "RadixAI", "WikiDump")

    # wr = WikiDumpReader()
    # page_reader = wr.read_tag(os.path.join(DATA_DIR, "enwiki-20191020-pages-articles-multistream.xml.bz2"))
    # for page in page_reader:
    #     title = wr.get_page_title(page)
    #     if title == "Allen Ginsberg":
    #         print(wr.get_page_title(page))
    #         print("============================================================")
    #         print(wr.get_page_text(page))
    #         print("============================================================")
    #         print(wr.clean(wr.get_page_text(page)))
    #         break

    text = ""
    with open(os.path.join(DATA_DIR, "Ref_Article_For_Cleaning.txt"), 'r') as fin:
        for line in fin:
            text += line

    wr = WikiDumpReader()
    # text = wr.remove_comments(text)
    # text = wr.remove_categories(text)
    # text = wr.remove_files(text)
    # text = wr.remove_refs(text)
    # text = wr.remove_curlies(text)
    #
    # text = wr.process_links(text)
    #
    text = wr.clean(text, b_debug=True)

    print(text)
