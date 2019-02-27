====================================
Utilities for Anime Addventure Dumps
====================================

Some time in June 2016, the `Anime Addventure`_ went down and it's unknown
whether it'll ever come back up.

For those unfamiliar with it, an Addventure is basically a giant collaborative
"choose your own adventure" book and this one was my first introduction to
fanfiction.

People have been sharing dumps of the site, but it's kind of hard to deal with
nearly 45,000 numbered HTML files without the server-side scripting that made
it possible to find individual story threads.

As such, this repository will hold my efforts to remedy that problem.

--------------
Current Status
--------------

As of my last update (2016-09-05), there are two scripts, one for extracting
metadata from a dump and one for transforming it, plus a half-finished GUI for
browsing the extracted data:


get_metadata.py
---------------

This script will produce a JSON-format list of records from the raw HTML
episode files in an Anime Addventure dump. It requires Python and LXML_.

(It could also be extended to dump and sanitize the episode content, but I
don't need that yet and I want to get something useful as quickly as possible.)

**Features:**

* When working from a RAM drive, the script can process the entire
  44755-episode dump in just under 40 seconds.
* Input sanitization using ``lxml.html.clean``, plus log messages to warn about
  what the sanitization is omitting.
* Full ``--help`` output
* Innards that, while not ideal, are clean, well commented, and expose a
  high-level API wrapper for episode HTML that can be built on.
* Tested under Python 2.7 and 3.4
* Tested on Lubuntu Linux 14.04, but should theoretically work on any operating
  system.
* LXML_ is the only mandatory external dependency (``python-lxml`` or
  ``python3-lxml`` on apt-based distros like Debian, Ubuntu, and Mint), but it
  is recommended that you install scandir_ for maximum performance if you
  are running a Python version prior to 3.5.

The resulting JSON dump is 8.7MiB (1.6MiB gzipped) and contains entries that
look like this:

.. code:: json

      {
        "id": 200054,
        "author_email": null,
        "parent_id": 198915,
        "author": "Kwakerjak",
        "title": "Creeping Doubts",
        "tags": [],
        "thread": "Coupled Union - Tick Tock",
        "posted": 1201866660.0
      }

A JSON schema is also provided in the ``schema.json`` file to make it easy to
ensure you're covering all possible cases when reading the JSON output.
(However, be aware that some sanitized episode titles are empty strings or
strings containing only whitespace, which the schema does not make obvious.)

**Installation (Ubuntu):**

.. code:: sh

  sudo apt-get install python-lxml
  sudo pip install scandir
  # Download get_metadata.py and you're done

prepare_metadata.py
-------------------

This script takes the JSON output from ``get_metadata.py`` and transforms it
for use by other tools. They are separate so that you need only ever go through
the heavy process of dumping the metadata once.

**Features:**

* Selectable JSON or YAML output, with more formats planned
* Capable of processing the entire Addventure's records in 1-2 seconds in
  JSON-to-JSON mode. (PyYAML's serializer is slow, so YAML output takes 8-42
  seconds)
* Full ``--help`` output
* No external dependencies beyond Python itself
* Tested under Python 2.7 and 3.4
* Tested on Lubuntu Linux 14.04, but should theoretically work on any operating
  system.
* A partial test suite, using Nose_

It currently has three subcommands:

``key-by``
~~~~~~~~~~

This allows you to restructure the data so that writing efficient programs to
look up records becomes trivial.

For example, take this command-line:

.. code:: sh

  ./prepare_metadata.py -o temp.json key-by id

It will produce a ``temp.json`` file ready for looking up records by ID,
similar to how the Addventure itself would have organized its database:

.. code:: json

  {
    ...
    "200054": {
      "thread": "Coupled Union - Tick Tock",
      "tags": [],
      "author_email": null,
      "author": "Kwakerjak",
      "parent_id": 198915,
      "title": "Creeping Doubts",
      "id": 200054
    },
    ...
  }

...while this command would produce something suitable for browsing by author:

.. code:: sh

  ./prepare_metadata.py -o temp.json key-by author thread

.. code:: json

  {
    ...
    "Kwakerjak": {
      ...
      "Coupled Union - Tick Tock": [
        ...
        {
          "thread": "Coupled Union - Tick Tock",
          "tags": [],
          "author_email": null,
          "author": "Kwakerjak",
          "parent_id": 198915,
          "title": "Creeping Doubts",
          "id": 200054
        },
        ...
      ],
      ...
    }
    ...
  }

``index-by``
~~~~~~~~~~~~

This command functions in a manner almost identical to ``key-by`` except that,
instead of mapping a key to the record itself, it maps it to another key,
so you can have a single ``key-by`` file, then multiple smaller index files
for quickly looking up by various different criteria.

For example, this command would produce an index that would enable enable a
pure-JavaScript implementation of the strict thread view when paired with
a ``key-by`` file mapping IDs to records:

.. code:: sh

  ./prepare_metadata.py -o temp.json index-by thread

.. code:: json

  {
    "Coupled Union - Tick Tock": [
      ...
      197639,
      197644,
      198915,
      200054,
      200639,
      201643,
      202759,
      ...
    ],
  }

``flatten``
~~~~~~~~~~~

This command converts the data into a form which can be used with output
formats that don't support nested data structures.

For example, this command line will produce a comma-separated ``temp.csv``
file, sorted by episode ID, which can be opened in Microsoft Excel or
LibreOffice, among other tools:

.. code:: sh

  python ./prepare_metadata.py -f csv -o temp.csv flatten

...and this command will produce a tab-separated ``temp.tsv`` file, sorted by
author, which can also be opened in Microsoft Excel, LibreOffice, and various
others:

.. code:: sh

  python ./prepare_metadata.py -f tsv -o temp.tsv -s author flatten

However, sorting by non-unique keys is of limited utility right now, because
I still have to add support for sorting by more than one key at once.
(ie. "sort by author, then thread, then ID")

As such,
you're probably better off leaving it on the default sort, and using Excel or
LibreOffice to sort it, since they can save the changed sheet back to CSV/TSV.

It is possible to configure the separator used for flattening the ``tags``
list, but the vertical bar character is the default, resulting in multiple tags
on a single episode being represented in this format: ``waff|lime``

``visjs``
~~~~~~~~~~~

This command is similar to ``key-by`` but, instead, produces ready-to-use
"nodes and edges" JSON for Vis.js_ to minimize load times for ``browser.html``.

It's used as follows:

.. code:: sh

  ./prepare_metadata.py -o addventure_graph.json visjs

It defaults to mapping the ``title`` field as each node's ``label``, but this
can be overridden via the ``--label-field`` option.

**NOTE:** This command isn't currently useful for the full Addventure data set
because Vis.js can't handle a graph of nearly 45,000 nodes.

An option to subdivide the graph is in development.

browser.html
------------

A half-finished HTML application for browsing Addventure Episodes.

It's purely client-side JavaScript and it would even run from ``file://`` URLs
were it not for the browser's "every local file has a different and anonymous
``Origin``" security restriction, so it'll run on *any* web server you can
scrape together.

It currently can't deal with the full data set, because Vis.js lacks the
performance to handle it verbatim. However, Vis.js is fine with one or two
thousand nodes, so it should work perfectly once I've enhanced it and
``prepare_metadata.py`` to support breaking the data set up into a graph of
threads, and then one graph of episodes per thread.
(I did a quick analysis of the data set and there are only 272 threads and
429 episodes in the longest thread)

If you want to test it out, patch the following two lines into
``prepare_metadata.py`` to produce a smaller data set...

.. code:: python

    records.sort(key=lambda x: x['id'])
    records = records[:1000]

...and then run this command:

.. code:: sh

  ./prepare_metadata.py -o addventure_graph.json visjs

You can then copy ``browser.html`` and ``addventure_graph.json`` into the
dump's ``eps`` folder and run this command to serve it up:

.. code:: sh

  cd /path/to/eps
  python -m SimpleHTTPServer

(This should even work on Windows as long as you have Python installed)


.. _Anime Addventure: http://addventure.bast-enterprises.de/
.. _LXML: http://lxml.de/installation.html
.. _Nose: https://nose.readthedocs.io/en/latest/
.. _scandir: https://pypi.python.org/pypi/scandir
.. _Vis.js: http://visjs.org/
