How to contribute
=================

Write a patch
-------------

Help yourself with the [documentation](http://dev.weboob.org).

Find an [opened issue on gitlab](https://git.weboob.org/weboob/devel/issues),
or write you own bugfix or feature. Then, once it is necessary, commit with:

```
$ git commit -a
```

Do not forget to write a helpful commit message.

Check your patch
----------------

You can run these scripts to be sure your patch doesn’t break anything:
```
$ tools/pyflakes.sh
$ tools/run_tests.sh yourmodulename  # or without yourmodulename to test everything
```

Perhaps you should also write or fix tests.

Send a patch
------------

```
$ git format-patch -n -s origin
```

Then, send them with this command:

```
$ git send-email --to=weboob@weboob.org *.patch
```

You can also send the files by yourself if you haven’t any configured MTA on
your system.

Create a fork on git.weboob.org
-------------------------------

If you think you’ll contribute to Weboob regularly, you can create a repository
on [git.weboob.org](git.weboob.org). To do so,
[signup](https://git.weboob.org/users/sign_in) and click on _Fork_ on the weboob
repository's page.

Then, you can push your commits, and ask for merge requests.

All git branch are listed here: https://git.weboob.org/explore/projects