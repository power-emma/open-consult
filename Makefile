CFLAGS ?= -O2 -g -Wall -Wextra
GTK_CFLAGS := $(shell pkg-config --cflags gtk4)
GTK_LIBS := $(shell pkg-config --libs gtk4)

SRC := src/gui.c src/consult.c src/serial.c src/registers.c

consult-gui: $(SRC) $(wildcard src/*.h)
	$(CC) $(CFLAGS) -DLOG_DIR='"$(CURDIR)/logs"' $(GTK_CFLAGS) -o $@ $(SRC) $(GTK_LIBS)

clean:
	rm -f consult-gui

.PHONY: clean
