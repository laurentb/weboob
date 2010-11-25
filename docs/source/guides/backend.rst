Backend development
===================

Each backend implements one or many :doc:`capabilities </api/capabilities/index>` to tell what kind of features the
website provides. A capability is a class derived from :class:`weboob.capabilities.base.ICap` and with some virtual
methods (which raise ``NotImplementedError``).

A capability needs to be as generic as possible to allow a maximum number of backends to implements it.
Anyway, if you really need to handle website specificities, you can create more specific sub-capabilities.

For example, there is the :class:`weboob.capabilities.messages.ICapMessages` capability, with the associated
:class:`weboob.capabilities.messages.ICapMessagesPost` capability to allow answers to messages.

Pick an existing capability
---------------------------

When you want to create a new backend, you may have a look on existing capabilities to decide which one can be
implemented. It is quite important, because each already existing capability is supported by at least one application.
So if your new backend implements an existing capability, it will be usable from the existing applications right now.

Create a new capability
-----------------------

If the website you want to manage implements some extra-features which are not implemented by any capability,
you can introduce a new capability.

There are some important rules:

* A method can raise only its own exceptions.

  When you want to return an error, you *must* raise only your own exceptions defined in the capability module.
  Never let Python raise his exceptions, for example ``KeyError`` if a parameter given to method isn't found in a local
  list.

* Prefer returning objects

  Python is an object-oriented language, so when your capability supports entities (for example
  :class:`weboob.capabilities.video.BaseVideo` with the :class:`weboob.capabilities.video.ICapVideo` capability),
  you have to create a class derivated from :class:`weboob.capabilities.base.CapBaseObject`, and create an unique method
  to get it (for example :func:`get_video() <weboob.capabilities.video.ICapVideo.get_video>`), instead of several methods like
  ``get_video_url()``, ``get_video_preview()``, etc.

  An object has an unique ID.

* Filled objects

  When an object is fetched, all of its fields are not necessarily loaded.

  For example, on a video search, if the backend gets information from the search page, the direct URL of the video
  isn't available yet.

  A field which isn't loaded can be set to :class:`weboob.capabilities.base.NotLoaded`.

  By default, in the object constructor, every fields should be set to
  :class:`NotLoaded <weboob.capabilities.base.NotLoaded>`, and when the backend loads them, it replaces them with
  the new values.
