# Linux:   make                 -> ./consult-gui
# Windows: make (MSYS2 UCRT64)  -> consult-gui.exe   (make dist: a folder that runs anywhere,
#                                 make onefile: dist/consult-gui.exe, all in one file)
# Cross:   make WINDOWS=1 CC=x86_64-w64-mingw32-gcc PKG_CONFIG=x86_64-w64-mingw32-pkg-config

CFLAGS ?= -O2 -g -Wall -Wextra
PKG_CONFIG ?= pkg-config
GTK_CFLAGS := $(shell $(PKG_CONFIG) --cflags gtk4 json-glib-1.0)
GTK_LIBS := $(shell $(PKG_CONFIG) --libs gtk4 json-glib-1.0)

SRC := src/gui.c src/fuel_map.c src/replay.c src/consult.c src/serial.c src/registers.c

ifeq ($(OS),Windows_NT)
WINDOWS ?= 1
endif

ifeq ($(WINDOWS),1)
# Logs go to logs/ next to the .exe (see log_dir() in gui.c).
BIN := consult-gui.exe
DEFS :=
LDFLAGS += -mwindows
LDLIBS += -lsetupapi -lwinmm
else
BIN := consult-gui
DEFS := -DLOG_DIR='"$(CURDIR)/logs"'
endif

$(BIN): $(SRC) $(wildcard src/*.h)
	$(CC) $(CFLAGS) $(DEFS) $(GTK_CFLAGS) -o $@ $(SRC) $(LDFLAGS) $(GTK_LIBS) $(LDLIBS)

# Windows only, run in the MSYS2 shell: the .exe plus the GTK DLLs and data it needs,
# so it starts from Explorer on a PC without MSYS2. Zip dist/consult-gui-windows to share.
DIST := dist/consult-gui-windows
PREFIX_DIR := $(MINGW_PREFIX)
dist: $(BIN)
	@test -n "$(PREFIX_DIR)" || { echo "run make dist in an MSYS2 UCRT64 shell"; exit 1; }
	rm -rf $(DIST)
	mkdir -p $(DIST)/lib $(DIST)/share/glib-2.0/schemas $(DIST)/share/icons
	cp $(BIN) $(DIST)/
	cp -r $(PREFIX_DIR)/lib/gdk-pixbuf-2.0 $(DIST)/lib/
	cp $(PREFIX_DIR)/share/glib-2.0/schemas/gschemas.compiled $(DIST)/share/glib-2.0/schemas/
	cp -r $(PREFIX_DIR)/share/icons/hicolor $(PREFIX_DIR)/share/icons/Adwaita $(DIST)/share/icons/
	ldd $(BIN) $$(find $(DIST)/lib -name '*.dll') | awk '{print $$3}' | \
		grep -i '^$(PREFIX_DIR)/bin/' | sort -u | xargs -I{} cp {} $(DIST)/
	@echo "built $(DIST)"

# Windows only: everything in one dist/consult-gui.exe. GTK can't be linked statically
# (MSYS2 ships it as DLLs only), so this is a launcher with the dist folder packed in;
# the first run unpacks it to %LOCALAPPDATA%\open-consult (see src/onefile/onefile.h).
ONEFILE := dist/consult-gui.exe
onefile: dist src/onefile/launcher.c src/onefile/pack.c src/onefile/onefile.h
	$(CC) -O2 -Wall -Wextra -o dist/pack.exe src/onefile/pack.c -lz
	$(CC) -O2 -Wall -Wextra -municode -mwindows -static -o dist/launcher.exe \
		src/onefile/launcher.c -lz
	dist/pack.exe dist/launcher.exe $(DIST) $(ONEFILE)
	rm -f dist/pack.exe dist/launcher.exe

clean:
	rm -f consult-gui consult-gui.exe
	rm -rf dist

.PHONY: clean dist onefile
