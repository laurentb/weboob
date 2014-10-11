Create a capability
===================

A method can raise only its own exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you want to return an error, you **must** raise only your own exceptions defined in the capability module.
Never let Python raise his exceptions, for example ``KeyError`` if a parameter given to method isn't found in a local
list.

Prefer returning objects
^^^^^^^^^^^^^^^^^^^^^^^^

Python is an object-oriented language, so when your capability supports entities (for example
:class:`weboob.capabilities.video.BaseVideo` with the :class:`weboob.capabilities.video.CapVideo` capability),
you have to create a class derived from :class:`weboob.capabilities.base.BaseObject`, and create an unique method
to get it (for example :func:`get_video() <weboob.capabilities.video.CapVideo.get_video>`), instead of several methods like
``get_video_url()``, ``get_video_preview()``, etc.

An object has an unique ID.

Filled objects
^^^^^^^^^^^^^^

When an object is fetched, all of its fields are not necessarily loaded.

For example, on a video search, if the *backend* gets information from the search page, the direct URL of the video
isn't available yet.

A field which isn't loaded can be set to :class:`weboob.capabilities.base.NotLoaded`.

By default, in the object constructor, every fields should be set to
:class:`NotLoaded <weboob.capabilities.base.NotLoaded>`, and when the backend loads them, it replaces them with
the new values.


