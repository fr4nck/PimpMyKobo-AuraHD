CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -Wpedantic
SOURCES = pmkb_text_keyboard.c pmkb_notebook.c pmkb_surface.c pmkb_backend.c pmkb_app.c
TEST = tests/native_ui_tests.c
TARGET = pmkb-native-tests
CALC_SOURCES = pmkb_text_keyboard.c pmkb_surface.c pmkb_calculator.c pmkb_calculator_ui.c
CALC_TEST = tests/native_calc_tests.c
CALC_TARGET = pmkb-calculator-tests

.PHONY: all test clean
all: $(TARGET) $(CALC_TARGET)
$(TARGET): $(SOURCES) $(TEST) pmkb_ui.h
	$(CC) $(CFLAGS) -I. $(SOURCES) $(TEST) -o $(TARGET)
$(CALC_TARGET): $(CALC_SOURCES) $(CALC_TEST) pmkb_ui.h pmkb_calculator.h pmkb_calculator_ui.h
	$(CC) $(CFLAGS) -I. $(CALC_SOURCES) $(CALC_TEST) -lm -o $(CALC_TARGET)
test: $(TARGET) $(CALC_TARGET)
	./$(TARGET)
	./$(CALC_TARGET)
	./$(TARGET) --json-fixture | python3 tests/check_native_json.py
clean:
	rm -f $(TARGET) $(CALC_TARGET) pmkb-native-sanitized pmkb-calculator-sanitized
