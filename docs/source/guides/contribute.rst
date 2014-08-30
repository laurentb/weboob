How to contribute
=================

By coding
*********

Write a patch
-------------

Help yourself with the `documentation <http://docs.weboob.org/>`_.

Find an opened issue on this website, or write you own bugfix or feature. Then, once it is necessary, commit with::

    $ git commit -a

Do not forget to write a helpful commit message.

Check your patch
----------------

You can run these scripts to be sure your patch doesn't break anything::

    $ tools/pyflakes.sh
    $ tools/run_tests.sh yourmodulename  # or without yourmodulename to test everything

Perhaps you should also write or fix tests.

Send a patch
------------

::

    $ git format-patch -n -s origin

Then, send them with this command::

    $ git send-email --to=weboob@weboob.org *.patch

You can also send the files by yourself if you haven't any configured MTA on your system.

Ask for a public repository on git.symlink.me
---------------------------------------------

If you think you'll contribute to Weboob regularly, you can ask for a public repository. You'll also be able to push your commits in, and they'll be merged into the main repository easily.

All git branch are listed here: http://git.symlink.me/

By hosting a buildbot slave
***************************

To be sure weboob works fine on lot of architectures, OS and configurations, but also that websites haven't changed and backends still support them, it's important to have enough buildbot slaves.

If you are interested by hosting a buildbot slave, follow these instructions:

Create a slave
--------------

Firstly, you have to install ``pyflakes``, ``nose`` and `buildbot <http://buildbot.net>`_.

Run::

    $ buildslave create-slave <dirname> buildbot.weboob.org:9080 <name> <password>

.. note::
    if you use an old version of buildbot, run ``buildbot`` instead of ``buildslave``.

Parameters are:

* **dirname** — the path where you want to setup your slave on your host.
* **name** — the name of your slave. It would be for example your name, your nickname, your hostname. Check on http://buildbot.weboob.org the name you want to use isn't already taken.
* **password** — choose a password to login on the master.

For example::

    $ buildslave create-slave /home/me/buildbot buildbot.weboob.org:9080 me secret123

Then, edit files in ``/home/me/buildbot/info/`` and run the slave::

    $ buildslave start /home/me/buildbot

Contact us
----------

To connect your slave to our master, you can send us an email on admin@weboob.org with the following information:

* The name of your slave;
* The IP address of the host;
* The password of your slave;
* Indicate if you want to run tests for every merges (three times a day) or only do a nightly build.

When your slave will be accepted, you will see it on http://buildbot.weboob.org/waterfall.

How it works
------------

When a build is requested by master, your slave updates its local git repository, and run ``tools/run_tests.sh``.

To work correctly, we suggest you to add as many as possible backends with the user of the slave. No private information will be sent to master, and it's better to have tests on backends which need authentication, because not every developers have accounts on them.

