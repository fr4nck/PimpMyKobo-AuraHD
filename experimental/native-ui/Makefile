CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -Wpedantic
SOURCES = pmkb_text_keyboard.c pmkb_notebook.c pmkb_surface.c pmkb_app.c
TEST = tests/native_ui_tests.c
TARGET = pmkb-native-tests

.PHONY: all test clean
all: $(TARGET)
$(TARGET): $(SOURCES) $(TEST) pmkb_ui.h
	$(CC) $(CFLAGS) -I. $(SOURCES) $(TEST) -o $(TARGET)
test: $(TARGET)
	./$(TARGET)
	./$(TARGET) --json-fixture | python3 tests/check_native_json.py
clean:
	rm -f $(TARGET)
