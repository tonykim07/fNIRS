
/* INCLUDES */
#include "misc.h"
#include <stdbool.h>
#include <string.h>

/* DEFINES */

/* FUNCTION DEFINTIONS*/

void misc_toggle_led_periodic(const float toggle_frequency_hz)
{
    static bool update_tick_start = true;
    static uint32_t tick_start;

    if (update_tick_start)
    {
        tick_start = HAL_GetTick();
    }

    // Multiply by two since blinking takes 2 toggling cycles
    float toggle_frequency_khz = 2*toggle_frequency_hz / 1000;
    uint32_t period_ms = 0;

    if (toggle_frequency_khz > 0)
    {
        period_ms = (uint32_t)(1 / toggle_frequency_khz);
    }

    if ((HAL_GetTick() - tick_start) >= period_ms)
    {
        HAL_GPIO_TogglePin(MCU_TEST_LED_GPIO_Port, MCU_TEST_LED_Pin);
        update_tick_start = true;
    }
    else
    {
        update_tick_start = false;
    }
}

void misc_write_to_uart_port_periodic(UART_HandleTypeDef *huart, const char* message, const float frequency_hz)
{
    static bool update_tick_start = true;
    static uint32_t tick_start;

    if (update_tick_start)
    {
        tick_start = HAL_GetTick();
    }

    float frequency_khz = frequency_hz / 1000;
    uint32_t period_ms = 0;

    if (frequency_khz > 0)
    {
        period_ms = (uint32_t)(1 / frequency_khz);
    }

    if ((HAL_GetTick() - tick_start) >= period_ms)
    {
        HAL_UART_Transmit(huart, (uint8_t*)message, strlen(message), HAL_MAX_DELAY);
        update_tick_start = true;
    }
    else
    {
        update_tick_start = false;
    }
}

