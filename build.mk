core := weboob/tools/application/qt5
applications := qboobmsg qhavedate qwebcontentedit qflatboob qcineoob qcookboob qhandjoob qbooblyrics qgalleroob qboobtracker
ifeq ($(WIN32),)
	applications += qvideoob
endif

directories := $(core) $(applications:%=weboob/applications/%/ui)

.PHONY: clean all $(directories)

all: target := all
all: $(directories)

clean: target := clean
clean: $(directories)

$(directories):
	$(MAKE) -C $@ $(target)
