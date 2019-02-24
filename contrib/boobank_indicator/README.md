Weboob
==========

Weboob is a project which provides a core library, modules and applications
such as boobank.

Overview
--------

The core library defines capabilities: features common to various websites.

Each module interfaces with a website and implements one or many of these
capabilities. Modules can be configured (becoming a "backend"), which means
that the end-user can provide personal information to access the underlying
website, like a login and password.

Applications allow the end-user to work with many modules in parallel,
in a multi-threaded way.

The core library provides base classes which help developers write
modules and applications.

Weboob is written in Python and is distributed under the LGPLv3+ license.

For more information, please go to the official website at http://weboob.org/


##Installation
boobank_indicator is distributed as a python package. Do the following to install:

``` sh
sudo pip install boobank_indicator
OR
sudo easy_install boobank_indicator
OR
#Download Source and cd to it
sudo python setup.py install
```

After that, you can run `boobank_indicator` from anywhere and it will run. You can
now add it to your OS dependent session autostart method. In Ubuntu, you can
access it via:

1. System > Preferences > Sessions
(OR)
2. System > Preferences > Startup Applications

depending on your Ubuntu Version. Or put it in `~/.config/openbox/autostart`

###Dependencies

  - weboob >= 1.0
  - gir1.2-appindicator3 >= 0.1
  - gir1.2-notify >= 0.7

###Troubleshooting

If the app indicator fails to show in Ubuntu versions, consider installing
python-appindicator with

`sudo apt-get install python-appindicator` weboob gir1.2-appindicator3 gir1.2-notify`

##Author Information
- Bezleputh (<bezleputh@gmail.com>)
