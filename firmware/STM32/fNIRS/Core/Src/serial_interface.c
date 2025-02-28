
/* INCLUDES */
#include "serial_interface.h"
#include "sensing.h"

/* DEFINES */

/* DATA STRUCTURES */

static serial_interface_rx_vars_S serial_interface_rx_vars = { 0 };

/* FUNCTION DEFINITIONS */

void serial_interface_rx_parse_data(uint8_t *usb_receive_buffer)
{
    // See serial_interface.h for buffer indexing

    // Emitter controls
    serial_interface_rx_vars.user_emitter_control_override_enabled = (bool)usb_receive_buffer[EMIITER_CONTROL_OVERRIDE_ENABLE];
    serial_interface_rx_vars.emitter_control_state = (emitter_control_state_E)usb_receive_buffer[EMIITER_CONTROL_STATE];
    serial_interface_rx_vars.emitter_pwm_control = (usb_receive_buffer[EMITTER_PWM_CONTROL_H] << 8) | (usb_receive_buffer[EMIITER_PWM_CONTROL_L]);

    // Mux controls
    serial_interface_rx_vars.user_mux_control_override_enabled = (bool)usb_receive_buffer[MUX_CONTROL_OVERRIDE_ENABLE];
    serial_interface_rx_vars.mux_control_state = (mux_input_channel_E)usb_receive_buffer[MUX_CONTROL_STATE];
}

bool serial_interface_rx_get_user_emitter_control_override_enable(void)
{
    return serial_interface_rx_vars.user_emitter_control_override_enabled;
}

emitter_control_state_E serial_interface_rx_get_emitter_control_state(void)
{
    return serial_interface_rx_vars.emitter_control_state;
}

uint16_t serial_interface_rx_get_user_emitter_controls(void)
{
    return serial_interface_rx_vars.emitter_pwm_control;
}

bool serial_interface_rx_get_user_mux_control_override_enable(void)
{
    return serial_interface_rx_vars.user_mux_control_override_enabled;
}

mux_input_channel_E serial_interface_rx_get_user_mux_control_state(void)
{
    return serial_interface_rx_vars.mux_control_state;
}

void serial_interface_tx_send_sensor_data(void)
{

}