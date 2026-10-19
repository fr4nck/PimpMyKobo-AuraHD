/* PMKB native scientific calculator V0: lightweight PMKB-UI application. */
#ifndef PMKB_CALCULATOR_UI_H
#define PMKB_CALCULATOR_UI_H
#include "pmkb_ui.h"
#include "pmkb_calculator.h"
#define PMKB_CALC_HISTORY_LIMIT 8u
typedef struct {
    char expression[PMKB_CALC_MAX_BYTES+1];
    char result[40];
    bool degrees;
} PMKBCalcHistory;
typedef struct {
    PMKBText expression;            /* shared UTF-8 editor with Notes/Store */
    PMKBKeyboard keyboard;          /* shared PMKB-UI keyboard instance */
    PMKBSurface screen;             /* host-only 8-bit grayscale raster */
    char result[40], message[56];
    PMKBCalcStatus math_status;
    double ans;
    bool has_ans;
    PMKBCalcHistory history[PMKB_CALC_HISTORY_LIMIT];
    size_t history_count;
    unsigned render_calls;
} PMKBCalcUI;
PMKBStatus pmkb_calc_ui_init(PMKBCalcUI *ui, int width, int height);
void pmkb_calc_ui_free(PMKBCalcUI *ui);
PMKBStatus pmkb_calc_ui_set_expression(PMKBCalcUI *ui,const char *expression);
PMKBStatus pmkb_calc_ui_evaluate(PMKBCalcUI *ui);
PMKBStatus pmkb_calc_ui_press(PMKBCalcUI *ui,int row,int col);
PMKBStatus pmkb_calc_ui_event(PMKBCalcUI *ui,PMKBEvent event);
void pmkb_calc_ui_clear(PMKBCalcUI *ui,bool all);
#endif
