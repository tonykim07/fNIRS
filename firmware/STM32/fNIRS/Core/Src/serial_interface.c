
/* INCLUDES */
#include "serial_interface.h"

/* DEFINES */

/* DATA STRUCTURES */

static serial_interface_rx_vars_S serial_interface_rx_vars = { 0 };

/* FUNCTION DEFINITIONS */

bool serial_interface_rx_get_user_override_enable(void)
{
    return serial_interface_rx_vars.user_control_override_enabled;
}

void serial_interface_rx_parse_data(uint8_t *usb_receive_buffer)
{
    // User override enable
    serial_interface_rx_vars.user_control_override_enabled = (bool)usb_receive_buffer[0];

    // Emitter controls
    serial_interface_rx_vars.control_state = (emitter_control_state_E)usb_receive_buffer[1];
    serial_interface_rx_vars.emitter_pwm_control = (usb_receive_buffer[2] << 8) | (usb_receive_buffer[3]);

    // Mux controls: TODO
}

emitter_control_state_E serial_interface_rx_get_emitter_control_state(void)
{
    return serial_interface_rx_vars.control_state;
}

uint16_t serial_interface_rx_get_user_emitter_controls(void)
{
    return serial_interface_rx_vars.emitter_pwm_control;
}
