#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to extract metadata from templated (HTML-format) Anime Addventure
episodes into a JSON file for further processing.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Metadata extractor for Anime Addventure dumps"
__version__ = "0.1"
__license__ = "MIT"

import functools, json, locale, logging, os, re, sys, time
from itertools import chain

# Requires LXML for parsing HTML, both for performance and features
from lxml import html
from lxml.html.clean import Cleaner

if sys.version_info.major < 3:
    from urlparse import urlparse
else:
    from urllib.parse import urlparse  # pylint: disable=import-error,E0611
    unicode = str  # pylint: disable=redefined-builtin,invalid-name

# Try to use scandir.walk instead of os.walk for better I/O performance
# (Available via PyPI if your Python is too old to include it)
try:
    from scandir import walk
except ImportError:
    from os import walk

# Needed for strptime()-ing dates
locale.setlocale(locale.LC_TIME, "C")

log = logging.getLogger(__name__)

re_filename = re.compile(r"^(?P<id>\d+).html$")
re_title = re.compile(r"^(:[ ])?(?P<title>.*?) \[Episode (?P<id>\d+)\]$")

def assert_eq(x, y):
    """Helper for nicer basic assert messages"""
    assert x == y, "%s != %s" % (x, y)

def memoize(func):
    """A decorator to cache an expensive function's result, keyed on its
    arguments.

    @attention: For use with methods, the class must define a __repr__
        for incorporation into the cache key or Python's memory address reuse
        behaviour will cause difficult-to-predict bugs.
    """
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):  # pylint: disable=missing-docstring
        key = "%r%r" % (args, kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    return wrapper

def pop_node(node):
    """Remove and return a node but leave its tail text behind."""
    parent, prev = node.getparent(), node.getprevious()
    tail = node.tail or ''

    if prev is None:
        if parent.text is None:
            parent.text = ''
        parent.text += tail
    else:
        prev.tail += tail

    parent.remove(node)
    return node

def stringify_children(node):
    """Retrieve content in a form equivalent to innerHTML in browsers
    Source: http://stackoverflow.com/a/28173933
    """
    parts = ([node.text] + list(chain(*([
        html.tostring(c, with_tail=False, encoding=unicode), c.tail]
        for c in node.getchildren()))))

    # filter removes possible Nones in texts and tails
    return ''.join(x for x in parts if x is not None)

class MissingMetadataError(Exception):
    """Exception raised when required metadata could not be extracted"""

class AddventureEpisode(object):
    """A high-level API for reading metadata from Addventure episode HTML

    @note: This makes use of at least one assert which has proven invaluable
           for ensuring no mis-parsing is going on, but which could cause a
           spurious parsing failure with intentionally malformed input.

           (eg. Triggering the "didn't strip separator" assert by crafting
           an episode title which begins with ": " so that string remains after
           the real thread name separator has been stripped.)

           Asserts can be stripped by running Python with -O or setting
           the PYTHONOPTIMIZE environment variable to 1 or higher.
    """
    _id = None
    _title = None
    _author = None

    SAFE_HTML_TAGS = ['b', 'em', 'del', 'font', 'i', 's', 'small', 'span',
                      'strike', 'strong', 'sup', 'sub', 'u']
    TAG_MAP = {
        '(DARK)': 'dark',
        '(LEMON)': 'lemon',
        '(LIME)': 'lime',
        '(WAFF)': 'waff',
    }

    def __init__(self, path, doublecheck_id=True):
        """If doublecheck_id=True, then the first query to any element which
        parses the title line will trigger an abort if the filename doesn't
        match the pattern <id>.html.

        This feature has proved its utility by catching several parsing errors
        while developing this class.
        """
        self.path = path
        self.dom = html.parse(path)
        self.doublecheck_id = doublecheck_id
        self.cleaner = Cleaner(allow_tags=self.SAFE_HTML_TAGS,
                               remove_unknown_tags=None)

    @staticmethod
    def id_from_path(path):
        """Unified code for extracting episode IDs from file paths"""

        # This will be a no-op in the worst case
        name, _ = os.path.splitext(os.path.basename(path))

        try:
            return int(name)
        except ValueError:
            if name != 'index':
                log.warning("Type conversion failed: int(%r)", name)
        return None

    def sanitize_html(self, node, replace_br=True,
                      ignore_shady=lambda x: False):
        """A wrapper for lxml.html.clean with some extras

        @param replace_br: Replace each <br> tags with one space
        @param ignore_shady: A callback for determining whether to omit the
            "shady tags" warning for a given tag.
        """
        if replace_br:
            for elem in node:
                if elem.tag == 'br':
                    elem.tail = ' ' + (elem.tail or '')
                    pop_node(elem)

        # Warn about any shady tags before sanitizing in case they indicate
        # markup so bad it needs to be hand-corrected
        shady_tags = [x.tag for x in node
                      if not (x.tag in self.SAFE_HTML_TAGS or ignore_shady(x))]
        if shady_tags:
            log.warning("Shady tags in %s: %r", self.path, shady_tags)

        # Strip out any potentially harmful or annoying HTML
        self.cleaner(node)

    def _parse_title_str(self, title_str):
        """Code shared between multiple branches of _parse_title"""
        title = re_title.match(title_str or '')
        if title is None:
            raise MissingMetadataError("Cannot parse title for %s: %r" %
                                       (self.path, title_str))
        return title.group('title'), int(title.group('id'))

    @memoize
    def _parse_title(self):
        """Memoized parsing code shared between id, title, thread, and tags.

        @note: To avoid a deepcopy as an easy way to improve performance in
               batch (ie. all episodes) parsing, this pops nodes out of the
               internal DOM as it operates. If that's a problem, perform your
               raw parsing before retrieving properties which rely on this.
        """
        title_line = self.dom.find('.//h1')
        results = {
            'thread': None,
            'tags': []
        }

        # Extract the thread link element if present (without losing text)
        if len(title_line) and title_line[0].tag == 'a':
            thread_link = title_line[0]
            assert title_line.text is None
            assert thread_link.tail is not None
            results['thread'] = thread_link.text

            # Preserve the following text, but strip the ': ' separator
            assert thread_link.tail.startswith(": "), ('%r' % thread_link.tail)
            thread_link.tail = thread_link.tail[2:]
            pop_node(thread_link)
        else:
            assert title_line.text is not None

        # Extract any tags (without losing text)
        for tag in (x for x in title_line if x.tag == 'img'):
            if not tag.get("src").startswith("images/"):
                log.warning("External image in title for %s: %s",
                    self.path, tag.get('src'))
                continue

            tag_str = pop_node(tag).get('alt')
            assert tag_str in self.TAG_MAP, "%r" % html.tostring(tag)
            results['tags'].append(self.TAG_MAP.get(tag_str, tag_str))

        # Strip out any potentially harmful or annoying HTML
        self.sanitize_html(title_line)

        # Depending on whether there are HTML child elements now...
        if len(title_line) == 0:
            # Process the remaining plaintext into a title and ID
            results['title'], results['id'] = self._parse_title_str(
                title_line.text)
        else:
            # Parse the episode ID out of the last span of text...
            title_tail, results['id'] = self._parse_title_str(
                title_line[-1].tail)

            # ...and then subtract the ID from the title and stringify
            title_line[-1].tail = title_tail
            results['title'] = stringify_children(title_line)

        assert not results['title'].startswith(': '), '%r' % results['title']
        results['title'] = results['title'].strip()

        if self.doublecheck_id:
            assert_eq(self.id_from_path(self.path), results['id'])

        return results

    @memoize
    def _parse_author(self):
        """Memoized parsing code shared between author and author_email."""
        byline = self.dom.find('.//h3')

        # Remove the "by " prefix
        assert byline.text.startswith('by ')
        byline.text = byline.text[3:]

        # If the page has an Addventure-templated e-mail link, scrape the
        # address before the <a> tag gets scrubbed
        author_link = byline[0] if (len(byline) and not byline.text) else None
        if author_link is not None:
            email_uri = urlparse(author_link.get('href'))
            assert_eq(email_uri.scheme, 'mailto')

            email_addr = email_uri.path
        else:
            email_addr = None

        # Strip out any potentially harmful or annoying HTML
        self.sanitize_html(byline, ignore_shady=lambda x: (
            x.tag == 'a' and x.get('href', '').startswith('mailto:')))

        return stringify_children(byline), email_addr

    @property
    def timestamp(self):
        """Posting Timestamp"""
        matches = self.dom.xpath(".//i[starts-with(.,'(Posted ')]")

        if matches:
            return time.mktime(time.strptime(matches[0].text,
                                 "(Posted %a, %d %b %Y %H:%M)"))
        return None

    @property
    def author(self):
        """Author's name"""
        return self._parse_author()[0]

    @property
    def author_email(self):
        """Author's name"""
        return self._parse_author()[1]

    @property
    def id(self):  # pylint: disable=invalid-name
        """Episode ID"""
        return self._parse_title()['id']

    @property
    @memoize
    def parent_id(self):
        """ID of parent episode"""
        parent = None
        for node in (x for x in self.dom.iter('a')):
            if node.text and node.text.startswith('Back to episode '):
                parent = node
                break

        if parent is None:
            raise MissingMetadataError(
                "Cannot extract parent ID from {}".format(self.path))
        else:
            return self.id_from_path(parent.get('href'))

    @property
    def tags(self):
        """Tags"""
        return self._parse_title()['tags']

    @property
    def thread(self):
        """Tags"""
        return self._parse_title()['thread']

    @property
    def title(self):
        """Episode Title"""
        return self._parse_title()['title']

    def to_dict(self):
        """Convert all retrievable metadata to a dict for east serialization"""
        return {
            'author': self.author,
            'author_email': self.author_email,
            'id': self.id,
            'parent_id': self.parent_id,
            'posted': self.timestamp,
            'tags': self.tags,
            'thread': self.thread,
            'title': self.title,
        }

    def __repr__(self):
        # Needed so @memoize can tell different instances apart properly
        return "%s(%r)" % (self.__class__.__name__, self.path)

def walk_args(args):
    """A generator to allow the parent code to deal with a list of files, even
       when fed a mix of files and directories.

       (Includes recursion and extension filtering)
   """
    for path in args:
        if os.path.isdir(path):
            for parent, _, files in walk(path):
                for fname in [x for x in files if re_filename.match(x)]:
                    yield os.path.join(parent, fname)

        else:
            yield path

def main():
    """The main entry point, compatible with setuptools entry points."""
    # If we're running on Python 2, take responsibility for preventing
    # output from causing UnicodeEncodeErrors. (Done here so it should only
    # happen when not being imported by some other program.)
    if sys.version_info.major < 3:
        reload(sys)
        sys.setdefaultencoding('utf-8')  # pylint: disable=no-member

    from argparse import ArgumentParser, RawTextHelpFormatter, FileType
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
            description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_argument('--version', action='version',
            version="%%(prog)s v%s" % __version__)
    parser.add_argument('-v', '--verbose', action="count",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_argument('-q', '--quiet', action="count",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    parser.add_argument('-o', '--outfile', action="store", type=FileType('w'),
                        default="./addventure_meta.json",
                        help="Path to the output file (default: %(default)s, "
                       "Specify '-' for stdout)")
    parser.add_argument('path', nargs='+',
                        help="Path to the episode HTML")

    args = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    args.verbose = min(args.verbose - args.quiet, len(log_levels) - 1)
    args.verbose = max(args.verbose, 0)
    logging.basicConfig(level=log_levels[args.verbose],
                        format='%(levelname)s: %(message)s')

    results = []
    processed, failures = 0, []
    for path in walk_args(args.path):
        try:
            log.info("Processing file: %s", path)
            results.append(AddventureEpisode(path).to_dict())
            processed += 1
        except MissingMetadataError as err:
            failures.append((path, str('{}: {}'.format(
                err.__class__.__name__, err))))
        if processed % 1000 == 0:
            print("Processed: {},\tFailed: {}".format(
                processed, len(failures)))

    # ...and then dump it all to a JSON file for further processing
    json.dump(results, args.outfile, indent=2)
    args.outfile.close()

    # ...and end on a summary
    print("PROCESSED: {}\nFAILURES:\n\t{}".format(
        processed, '\n\t'.join('%-24s\t: %s' % x for x in failures)))

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
