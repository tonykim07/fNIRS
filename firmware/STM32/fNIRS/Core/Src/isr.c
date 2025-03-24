
/* INCLUDES */
#include "isr.h"
#include "serial_interface.h"
#include "sensing.h"

/* DEFINES */
#define MS_TO_1KHZ_TICKS(ms) ((ms) * (1U))

/* DATA STRUCTURES */

static isr_vars_S isr_vars = { 0 };

/* FUNCTION DEFINITIONS */

uint16_t isr_get_1khz_timer_ticks(void)
{
    return isr_vars.tim4_timer_ticks;
}

bool isr_get_emitter_control_timer_flag(void)
{
    return isr_vars.emitter_control_timer_flag;
}

void isr_reset_emitter_control_timer_flag(void)
{
    isr_vars.tim4_timer_ticks = 0U;
    isr_vars.emitter_control_timer_flag = false;
}

/* CALLBACK FUNCTIONS */

// ISR function - called every 1kHz (TIM4)
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef* htim)
{
	serial_interface_tx_send_sensor_data();
    isr_vars.tim4_timer_ticks++;

    // Note: tim4_timer_ticks is reset by emitter control
    if (isr_vars.tim4_timer_ticks >= MS_TO_1KHZ_TICKS(4000))
    {
        // This flag will be read by emitter control
        isr_vars.emitter_control_timer_flag = true;
    }
}

// ISR function - called every 5kHz (TIM3)
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc)
{
    sensing_update_all_sensor_channels();
}
