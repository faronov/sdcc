/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdint.h>
#include <string.h>
#include <8051.h>

__xdata volatile uint8_t result;
__xdata uint8_t destination[17];
__xdata uint8_t source[17];
__xdata volatile uint8_t count;
__xdata volatile unsigned long long wide;
static __xdata uint8_t retained;

uint8_t sample(uint8_t first, uint8_t second)
{
    volatile uint8_t local = first;
    retained += second;
    return local + retained;
}

void main(void)
{
    memcpy(destination, source, count);
    wide = wide / (count + 1u);
    result = sample(destination[0], source[0]);
    P1 = result;
    for (;;) {}
}
