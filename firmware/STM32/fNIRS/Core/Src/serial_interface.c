
/* INCLUDES */
#include "serial_interface.h"
#include "sensing.h"
#include "emitter_control.h"
#include "usbd_cdc_if.h"

/* DEFINES */
#define SENSOR_MODULE_TO_940NM_PWM_CHANNEL(module)  ((module * 2U) + (1U))
#define SENSOR_MODULE_TO_660NM_PWM_CHANNEL(module)  ((module * 2U))

#define TX_BUFFER_INDEX(sensor_module, byte, bytes_per_sensor) ((sensor_module * bytes_per_sensor) + (byte))

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
    uint8_t tx_buffer[NUM_OF_SENSOR_MODULES * NUM_OF_BYTES_PER_SENSOR_MODULE];
    for (sensor_module_E module = (sensor_module_E)0U; module < NUM_OF_SENSOR_MODULES; module++)
    {
		uint16_t sensor_data_channel_one = sensing_get_sensor_calibrated_value(module, MUX_INPUT_CHANNEL_ONE);
        uint16_t sensor_data_channel_two = sensing_get_sensor_calibrated_value(module, MUX_INPUT_CHANNEL_TWO);
        uint16_t sensor_data_channel_three = sensing_get_sensor_calibrated_value(module, MUX_INPUT_CHANNEL_THREE);
        bool emitter_940nm_is_on = emitter_control_is_emitter_active(SENSOR_MODULE_TO_940NM_PWM_CHANNEL(module));
        bool emitter_660nm_is_on = emitter_control_is_emitter_active(SENSOR_MODULE_TO_660NM_PWM_CHANNEL(module));
        
        tx_buffer[TX_BUFFER_INDEX(module, PACKET_IDENTIFIER, NUM_OF_BYTES_PER_SENSOR_MODULE)] = (0xf0 | (uint8_t)module);
        tx_buffer[TX_BUFFER_INDEX(module, SENSOR_CHANNEL_1_H, NUM_OF_BYTES_PER_SENSOR_MODULE)] = (sensor_data_channel_one >> 8U) & 0xff;
        tx_buffer[TX_BUFFER_INDEX(module, SENSOR_CHANNEL_1_L, NUM_OF_BYTES_PER_SENSOR_MODULE)] = (sensor_data_channel_one) & 0xff;
        tx_buffer[TX_BUFFER_INDEX(module, SENSOR_CHANNEL_2_H, NUM_OF_BYTES_PER_SENSOR_MODULE)] = (sensor_data_channel_two >> 8U) & 0xff;
        tx_buffer[TX_BUFFER_INDEX(module, SENSOR_CHANNEL_2_L, NUM_OF_BYTES_PER_SENSOR_MODULE)] = (sensor_data_channel_two) & 0xff;
        tx_buffer[TX_BUFFER_INDEX(module, SENSOR_CHANNEL_3_H, NUM_OF_BYTES_PER_SENSOR_MODULE)] = (sensor_data_channel_three >> 8U) & 0xff;
        tx_buffer[TX_BUFFER_INDEX(module, SENSOR_CHANNEL_3_L, NUM_OF_BYTES_PER_SENSOR_MODULE)] = (sensor_data_channel_three) & 0xff;
        tx_buffer[TX_BUFFER_INDEX(module, EMITTER_STATUS, NUM_OF_BYTES_PER_SENSOR_MODULE)] = ((uint8_t)emitter_940nm_is_on << 1) | ((uint8_t)emitter_660nm_is_on);
    }

    CDC_Transmit_FS(tx_buffer, sizeof(tx_buffer));
}
