How to contribute
=================

By coding
*********

Write a patch
-------------

Help yourself with the `documentation <http://docs.weboob.org/>`_.

Find an opened issue on `this website <https://git.weboob.org/weboob/weboob/issues>`_, or write your own bugfix or feature.
Then, once it is necessary, commit with::

    $ git commit -a

Do not forget to write a helpful commit message.

Check your patch
----------------

You can run these scripts to be sure your patch doesn't break anything::

    $ tools/pyflakes.sh
    $ tools/weboob_lint.sh
    $ tools/run_tests.sh yourmodulename  # or without yourmodulename to test everything

To aid in verifying Python 3 compatibility, also run::

    $ tools/pyflakes.sh -3
    $ tools/run_tests.sh -3 yourmodulename

Perhaps you should also write or fix tests. These tests are automatically run by
`Gitlab CI <https://git.weboob.org/weboob/weboob/pipelines>`_ at each commit and merge requests.

Create a merge request or send a patch
--------------------------------------

The easiest way to send your patch is to create a fork on `the Weboob Gitlab <https://git.weboob.org>`_ and create a merge
request from there. This way, the code review process is easier and continuous integration is run automatically (see
previous section).

If you prefer good old email patches, just use

::

    $ git format-patch -n -s origin

Then, send them with this command::

    $ git send-email --to=weboob@weboob.org *.patch

You can also send the files by yourself if you haven't any configured MTA on your system.

By hosting a Gitlab CI runner
*****************************

To be sure weboob works fine on lot of architectures, OS and configurations, but also that websites haven't changed and
backends still support them, it's important to have enough runners with different configurations, especially since
running some tests requires a working backend.

If you are interested by hosting a Gitlab-CI runner, follow these instructions:

You can `install a Gitlab runner <https://docs.gitlab.com/runner/install/>`_ and make it use a specific backend file (be
it either by creating a dedicated Docker image with your credentials or running it in ``shell`` mode and making the
backend file available to it).

Then, you should contact us at admin@weboob.org so that we could help you register your runner with our Gitlab.
