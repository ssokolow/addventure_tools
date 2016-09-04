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

As of my last update (2016-09-04), there are two scripts, one for extracting
metadata from a dump and one for transforming it:


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
        "thread": "Coupled Union - Tick Tock"
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
* A partial test suite, using Nose_

It currently has two subcommands:

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


.. _Anime Addventure: http://addventure.bast-enterprises.de/
.. _LXML: http://lxml.de/installation.html
.. _Nose: https://nose.readthedocs.io/en/latest/
.. _scandir: https://pypi.python.org/pypi/scandir

