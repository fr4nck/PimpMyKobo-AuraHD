/* PMKB scientific math V0: C11, offline, no parser eval or hidden I/O. */
#ifndef PMKB_CALCULATOR_H
#define PMKB_CALCULATOR_H
#include <stdbool.h>
#include <stddef.h>
#define PMKB_CALC_MAX_UNITS 192u
#define PMKB_CALC_MAX_BYTES 768u
#define PMKB_CALC_MAX_TOKENS 128u
#define PMKB_CALC_MAX_DEPTH 48u
typedef enum {
    PMKB_CALC_OK=0, PMKB_CALC_SYNTAX, PMKB_CALC_DOMAIN,
    PMKB_CALC_DIV_ZERO, PMKB_CALC_RANGE, PMKB_CALC_LIMIT,
    PMKB_CALC_ARGUMENT
} PMKBCalcStatus;
/* degrees=true: angle input/output of trig functions is in degrees.
 * ans must be finite. On any error the output value is left untouched. */
PMKBCalcStatus pmkb_calc_evaluate(const char *expression, bool degrees,
                                   double ans, double *result);
/* 12 significant digits, locale-independent decimal point, no -0. */
bool pmkb_calc_format(double value, char *buffer, size_t size);
const char *pmkb_calc_error(PMKBCalcStatus error);
#endif
