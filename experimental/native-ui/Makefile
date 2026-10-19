CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -Wpedantic

SOURCES = pmkb_text_keyboard.c pmkb_notebook.c pmkb_surface.c pmkb_backend.c pmkb_app.c
CALC_SOURCES = pmkb_text_keyboard.c pmkb_surface.c pmkb_calculator.c pmkb_calculator_ui.c
BRIDGE_SOURCES = $(SOURCES) pmkb_calculator.c pmkb_calculator_ui.c pmkb_launcher_bridge.c
HAL_SOURCES = $(BRIDGE_SOURCES) pmkb_hal.c

TARGET = pmkb-native-tests
CALC_TARGET = pmkb-calculator-tests
BRIDGE_TARGET = pmkb-bridge-tests
HAL_TARGET = pmkb-hal-tests
PREVIEW_TARGET = pmkb-host-preview

.PHONY: all test preview clean
all: $(TARGET) $(CALC_TARGET) $(BRIDGE_TARGET) $(HAL_TARGET) $(PREVIEW_TARGET)

$(TARGET): $(SOURCES) tests/native_ui_tests.c pmkb_ui.h
	$(CC) $(CFLAGS) -I. $(SOURCES) tests/native_ui_tests.c -o $@

$(CALC_TARGET): $(CALC_SOURCES) tests/native_calc_tests.c pmkb_ui.h pmkb_calculator.h pmkb_calculator_ui.h
	$(CC) $(CFLAGS) -I. $(CALC_SOURCES) tests/native_calc_tests.c -lm -o $@

$(BRIDGE_TARGET): $(BRIDGE_SOURCES) tests/native_bridge_tests.c pmkb_launcher_bridge.h
	$(CC) $(CFLAGS) -I. $(BRIDGE_SOURCES) tests/native_bridge_tests.c -lm -o $@

$(HAL_TARGET): $(HAL_SOURCES) tests/native_hal_tests.c pmkb_hal.h pmkb_launcher_bridge.h
	$(CC) $(CFLAGS) -I. $(HAL_SOURCES) tests/native_hal_tests.c -lm -o $@

$(PREVIEW_TARGET): $(BRIDGE_SOURCES) tools/pmkb_host_preview.c pmkb_launcher_bridge.h
	$(CC) $(CFLAGS) -I. $(BRIDGE_SOURCES) tools/pmkb_host_preview.c -lm -o $@

test: all
	./$(TARGET)
	./$(CALC_TARGET)
	./$(BRIDGE_TARGET)
	./$(HAL_TARGET)
	./$(TARGET) --json-fixture | python3 tests/check_native_json.py
	python3 tools/render_host_previews.py --binary ./$(PREVIEW_TARGET)

# Writes six PNG host screenshots to OUT, only when explicitly requested.
OUT ?= ./host-previews
preview: $(PREVIEW_TARGET)
	python3 tools/render_host_previews.py --binary ./$(PREVIEW_TARGET) --output-dir $(OUT)

clean:
	rm -f $(TARGET) $(CALC_TARGET) $(BRIDGE_TARGET) $(HAL_TARGET) $(PREVIEW_TARGET) \
		pmkb-native-sanitized pmkb-calculator-sanitized pmkb-bridge-sanitized pmkb-hal-sanitized
