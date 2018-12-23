How to contribute
=================

Whenever you start working on a bug or an issue, please mention it in the
corresponding issue on this repo. If there is not an already opened issue for
this bug, please open a MR as soon as possible (with the `WIP:` prefix
mentionning it is a work in progress) to let others know you are working on
this module and fixing things.

This way, everyone is aware of the changes you are making and this avoid doing
a lot of duplicate work.


Write a patch
-------------

Help yourself with the [documentation](http://docs.weboob.org/).

Find an opened issue on [this website](https://git.weboob.org/weboob/weboob/issues),
or write your own bugfix or feature. Then, once it is necessary, commit with:

    $ git commit -a

Do not forget to write a helpful commit message. If you are fixing a bug in a
specific module, the first line of your commit message should read
`[module_name] Description of the fix`.


Check your patch
----------------

You can run these scripts to be sure your patch doesn't break anything:

    $ tools/pyflakes.sh
    $ tools/weboob_lint.sh
    $ tools/run_tests.sh yourmodulename  # or without yourmodulename to test everything

Perhaps you should also write or fix tests. These tests are automatically run by
[Gitlab CI](https://git.weboob.org/weboob/weboob/pipelines) at each commit and merge requests.


Create a merge request or send a patch
--------------------------------------

The easiest way to send your patch is to create a fork on [the Weboob
Gitlab](https://git.weboob.org) and create a merge request from there.
This way, the code review process is easier and continuous integration is run
automatically (see previous section).

If you prefer good old email patches, just use

    $ git format-patch -n -s origin

Then, send them with this command:

    $ git send-email --to=weboob@weboob.org *.patch

You can also send the files by yourself if you haven't any configured MTA on your system.


Notes on merging a merge request
--------------------------------

Few people (members of the [Weboob group on this
repo](https://git.weboob.org/groups/weboob/group_members)) have the right to
merge a MR.

Anyone is welcome to review and comment pending merge requests. A merge
request should in principle have at least two reviewers before getting merged.

Weboob repo should keep an history as linear as possible. Then, merging a merge
request should be done locally, with prior rebasing upon the `master` branch
and take care of using the `-ff-only` merge option. Merge requests should
**NOT** be merged through the Gitlab UI, which would result in an extra "merge"
commit.


Getting your contribution accepted
----------------------------------

All contributions are welcome and will only be judged on a technical and legal merit.
Contributing does not require endorsing views of any other contributor,
or supporting the project in any way.

Rejected contributions are not personal; further contributions will be considered.

It is discouraged to inquire about any contributor opinions or
identity characteristics as they should not have any influence on the quality
of the contribution. It is also possible to contribute anonymously.

If provided, icons are preferred to be parodic or humorous in nature for
legal reasons, however there are no restrictions on the quality or style of humor.
