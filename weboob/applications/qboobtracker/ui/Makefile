UI_FILES = $(wildcard *.ui)
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)
PYUIC = pyuic5

all: $(UI_PY_FILES)

%_ui.py: %.ui
	$(PYUIC) -o $@ $^

clean:
	rm -f *.pyc
	rm -f $(UI_PY_FILES)

