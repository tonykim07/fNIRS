
#ifndef INC_MISC_H_
#define INC_MISC_H_

/* INCLUDES */
#include "main.h"

/* DEFINES */

/* FUNCTION DEFINTIONS */
void misc_toggle_led_periodic(const float toggle_frequency);
void misc_write_to_uart_port_periodic(UART_HandleTypeDef *huart, const char* message, const float frequency);

#endif /* INC_MISC_H_ */
