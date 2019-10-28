# Check: https://www.heatonresearch.com/2017/03/03/python-basic-wikipedia-parsing.html
# Check: from https://effbot.org/zone/element-iterparse.htm
import bz2
import os
import xml.etree.ElementTree as etree


class WikipediaReader:
    def __init__(self, b_bz2=True,
                 prefix = "{http://www.mediawiki.org/xml/export-0.10/}"):
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


if __name__ == '__main__':
    HOME = os.path.expanduser("~")
    DATA_DIR = os.path.join(HOME, "Work", "Projects", "STDL", "Data", "RadixAI", "WikiDump")
    wr = WikipediaReader()
    page_reader = wr.read_tag(os.path.join(DATA_DIR, "enwiki-20191020-pages-articles-multistream.xml.bz2"))
    for page in page_reader:
        print(page)
        print()
