
#ifndef INC_SERIAL_INTERFACE_H_
#define INC_SERIAL_INTERFACE_H_

/* INCLUDES */
#include "main.h"
#include "emitter_control.h"

/* DATA STRUCTURES */
typedef struct
{
    bool user_control_override_enabled;

    // User emitter control variables
    emitter_control_state_E control_state;
    uint16_t emitter_pwm_control; // Each bit maps to a PWM channel

    // User mux control variables


} serial_interface_rx_vars_S; 

/* FUNCTION DEFINITIONS */

void serial_interface_rx_parse_data(uint8_t *usb_receive_buffer);
bool serial_interface_rx_get_user_override_enable(void);
emitter_control_state_E serial_interface_rx_get_emitter_control_state(void);
uint16_t serial_interface_rx_get_user_emitter_controls(void);

#endif /* INC_SERIAL_INTERFACE_H_ */
