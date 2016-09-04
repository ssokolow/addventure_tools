#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Simple tool for generating prepared data from a JSON
"list of records"-format data dump.

NOTE: Each subcommand also has its own options, which can be seen by passing
      the subcommand, followed by --help.
"""

# TODO: Remove this permanently once Flake8 allows ignoring E731 selectively
# flake8: noqa

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "JSON Data Transformation Helper"
__version__ = "0.1"
__license__ = "MIT"

import json, logging
from itertools import groupby

log = logging.getLogger(__name__)

class BadInputError(Exception):
    """Raised when the user's requested action is incompatible with the data"""

# pylint: disable=unnecessary-lambda
def group_by_multiple(records, field_names, render_inner=lambda x: list(x),
                      list_ordering=lambda x: x):
    """Recursively call itertools.groupby() based on a list of field names.

    @param keying_is_primary: If true, require that each innermost set of
        results contain only a single record and don't wrap them in a list.
    """
    is_last = len(field_names) <= 1
    grouping_key = lambda rec: rec[field_names[0]]

    #FIXME: There's a known bug in the index-by sorting output
    records.sort(key=lambda x: (grouping_key(x), list_ordering(x)))
    for key, group in groupby(records, grouping_key):
        group = list(group)
        group.sort(key=list_ordering)
        if is_last:
            yield key, render_inner(group)
        else:
            yield key, dict(group_by_multiple(group, field_names[1:],
                            render_inner, list_ordering=list_ordering))

def records_as_ids(records, target):
    """Generator to convert a list of records into a list of IDs."""
    for record in records:
        yield record[target]

def render_inner_single(items):
    """render_inner callback for --is-primary"""
    items = list(items)
    if len(items) != 1:
        raise BadInputError("--is-primary specified but specified key matches "
                            "more than one record: %r" % items)
    return items[0]

# -- subcommands --

def key_by(records, args):
    """The C{key-by} subcommand"""
    if args.is_primary:
        render_inner = render_inner_single
    else:
        render_inner = lambda x: list(x)  # noqa
    return dict(group_by_multiple(records, args.key, render_inner,
                                  list_ordering=lambda x: x[args.sort]))

def index_by(records, args):
    """The C{index-by} subcommand"""
    if args.is_primary:
        render_inner = lambda x: render_inner_single(records_as_ids(
            x, args.target))  # noqa
    else:
        render_inner = lambda x: list(records_as_ids(x, args.target))  # noqa
    return dict(group_by_multiple(records, args.key, render_inner))

# -- output serializers --

def dump_json(records, file_obj):
    """Serialize the given records as JSON

    @returns: C{tuple(data, file_extension)}
    """
    try:
        return json.dump(records, file_obj, indent=2), 'json'
    except TypeError as err:
        raise BadInputError("Output cannot be represented as JSON: %s" % err)

def dump_yaml(records, file_obj):
    """Serialize the given records as JSON

    @returns: C{tuple(data, file_extension)}
    """
    try:
        from yaml import safe_dump, representer
    except ImportError:
        raise BadInputError("Cannot import PyYAML. YAML output unavailable.")

    try:
        return safe_dump(records, file_obj), 'yaml'
    except representer.RepresenterError as err:
        raise BadInputError("Output cannot be represented as YAML: %s" % err)

OUTPUT_FORMATS = {
    'json': dump_json,
    'yaml': dump_yaml
}

# -- main() --

def main():
    """The main entry point, compatible with setuptools entry points."""
    # If we're running on Python 2, take responsibility for preventing
    # output from causing UnicodeEncodeErrors. (Done here so it should only
    # happen when not being imported by some other program.)
    import sys
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
    parser.add_argument('-f', '--format', action="store", default='json',
                       choices=OUTPUT_FORMATS, help="Specify the output "
                       "format (default: %(default)s)")
    parser.add_argument('-i', '--infile', action="store", type=FileType('r'),
                        default="./addventure_meta.json",
                        help="Specify the JSON file to read from "
                        "(default: %(default)s, use '-' for stdin)")
    parser.add_argument('-o', '--outfile', action="store", type=FileType('w'),
                        help="specify the json file to read from "
                        "(default will vary based on other arguments, "
                        "use '-' for stdout)")
    parser.add_argument('-s', '--sort', action="store", default='id',
                        help="specify the key to sort data by "
                        "(Note: There is currently a known bug in this, "
                        "so you'll only get partially sorted output)")

    subparsers = parser.add_subparsers(
        description='Operations this tool can perform')

    parser_key_by = subparsers.add_parser('key-by', help='Produce a (possibly '
        'nested) dict, mapping keys to record data.')
    parser_key_by.add_argument('key', nargs='+')
    parser_key_by.add_argument('--is-primary', action="store_true",
        default=False, help="require that the specified set of keys uniquely "
        "identify records and don't wrap the records in a list.")
    parser_key_by.set_defaults(func=key_by)

    parser_index_by = subparsers.add_parser('index-by', help='Produce a '
        '(possibly nested) dict, mapping keys to record IDs.')
    parser_index_by.add_argument('key', nargs='+')
    parser_index_by.add_argument('--target', action="store", default='id',
        help="Specify which field should be used as the primary key returned "
        "by the index. (default: %(default)s)")
    parser_index_by.add_argument('--is-primary', action="store_true",
        default=False, help="Require that the specified set of keys uniquely "
        "identify records and don't wrap the records in a list.")
    parser_index_by.set_defaults(func=index_by)

    args = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    args.verbose = min(args.verbose - args.quiet, len(log_levels) - 1)
    args.verbose = max(args.verbose, 0)
    logging.basicConfig(level=log_levels[args.verbose],
                        format='%(levelname)s: %(message)s')

    # Load data
    records = json.load(args.infile)
    log.debug("Loaded %d records", len(records))

    # Process data
    data = args.func(records, args)

    # Save data
    OUTPUT_FORMATS[args.format](data, args.outfile)

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
