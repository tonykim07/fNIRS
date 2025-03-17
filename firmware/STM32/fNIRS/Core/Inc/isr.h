
#ifndef INC_ISR_H_
#define INC_ISR_H_

/* INCLUDES */
#include "main.h"
#include <stdbool.h>

/* DEFINES */

/* DATA STRUCTURES */
typedef struct
{
    uint16_t tim4_timer_ticks;
    bool half_second_flag;
} isr_vars_S;

/* FUNCTION DECLARATIONS */
uint16_t isr_get_1khz_timer_ticks(void);
bool isr_get_half_second_flag(void);
void isr_reset_half_second_flag(void);

#endif /* INC_ISR_H_ */
