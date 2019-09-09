#!/usr/bin/env python3

import os


def genapi():
    os.system('rm -rf api')
    os.system('mkdir api')
    os.chdir('api')
    for root, dirs, files in os.walk('../../../weboob/'):
        root = root.split('/', 4)[-1]
        if root.startswith('applications'):
            continue

        if root.strip():
            os.system('mkdir -p %s' % root)
            module = '.'.join(['weboob'] + root.split('/'))
        else:
            module = 'weboob'

        subs = set()
        for f in files:
            if '.' not in f:
                continue

            f, ext = f.rsplit('.', 1)
            if ext != 'py' or f == '__init__':
                continue

            subs.add(f)
            with open(os.path.join(root, '%s.rst' % f), 'w') as fp:
                fmod = '.'.join([module, f])
                fp.write(""":mod:`%(module)s`
======%(equals)s=

.. automodule:: %(module)s
   :show-inheritance:
   :members:
   :undoc-members:""" % {'module': fmod,
                         'equals': '=' * len(fmod)})

        for d in dirs:
            if not root and d == "applications":
                continue
            subs.add('%s/index' % d)

        with open(os.path.join(root, 'index.rst'), 'w') as fp:
            if module == 'weboob':
                m = 'API'
            else:
                m = ':mod:`%s`' % module
            fp.write("""%s
%s

Contents:

.. toctree::
   :maxdepth: 3

   %s""" % (m, '=' * len(m), '\n   '.join(sorted(subs))))


if __name__ == '__main__':
    genapi()
