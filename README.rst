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

As of my last update (2016-09-03), I've just completed a script
(``get_metadata.py``) for dumping metadata from the HTML files into JSON format
so it can be processed and used by other tools.

(It could also dump and sanitize the episode content, but I don't need that yet
and I want to get something useful as quickly as possible.)

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

.. _Anime Addventure: http://addventure.bast-enterprises.de/
.. _LXML: http://lxml.de/installation.html
.. _scandir: https://pypi.python.org/pypi/scandir

**Installation (Ubuntu):**

.. code:: sh

  sudo apt-get install python-lxml
  sudo pip install scandir
  # Download get_metadata.py and you're done
