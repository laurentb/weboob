Automated tests
===============

Summary
*******

Weboob is a wide project which has several backends and applications, and changes can impact a lot of subsystems. To be sure that everything works fine after an important change, it's necessary to have automated tests on each subsystems.

How it works
************

You need `nose <http://nose.readthedocs.org/en/latest/>`_ installed.

To run the automated tests, use this script::

    $ tools/run_tests.sh

It looks for every files named ``test.py``, and find classes derivated from ``TestCase`` of ``BackendTest`` (in :class:`weboob.tools.test`).

Then, it run every method which name starts with ``test_``.

.. note::
    Some environment variables are available, to use specific backend file or send the test results. Refer to `the
    comments in the script <https://git.weboob.org/weboob/weboob/blob/master/tools/run_tests.sh#L4-8>`_ for more infos on this.

If a module name is passed as argument, only this module will be tested. For example, to only run ``lutim`` tests::

    $ tools/run_tests.sh lutim

To test with a Python 3 interpreter, set the ``-3`` flag (before all other arguments)::

    $ tools/run_tests.sh -3

Write a test case
*****************

Normal test
-----------

Use the class :class:`TestCase <weboob.tools.test.TestCase>` to derivate it into your new test case. Then, write methods which name starts with ``test_``.

A test fails when an assertion error is raised. Also, when an other kind of exception is raised, this is an error.

You can use ``assert`` to check something, or the base methods ``assertTrue``, ``assertIf``, ``failUnless``, etc. Read the `unittest documentation <http://docs.python.org/library/unittest.html>`_ to know more.

Backend test
------------

Create a class derivated from :class:`BackendTest <weboob.tools.test.BackendTest>`, and set the ``BACKEND`` class attribute to the name of the backend to test.

Then, in your test methods, the ``backend`` attribute will contain the loaded backend. When the class is instancied, it loads every configured backends of the right type, and randomly choose one.
If no one is found, the tests are skipped.

Example::

    from weboob.tools.test import BackendTest

    class YoutubeTest(BackendTest):
        MODULE = 'youtube'

        def test_youtube(self):
            l = [v for v in self.backend.iter_search_results('lol')]
            self.assertTrue(len(l) > 0)
            v = l[0]
            self.backend.fillobj(v, ('url',))
            self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))

Note: ``BackendTest`` inherits ``TestCase``, so the checks work exactly the same, and you can use the same base methods.
