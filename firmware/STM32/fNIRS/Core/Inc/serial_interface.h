
#ifndef INC_SERIAL_INTERFACE_H_
#define INC_SERIAL_INTERFACE_H_

/* INCLUDES */
#include "main.h"
#include "emitter_control.h"
#include "mux_control.h"

/* DATA STRUCTURES */

typedef enum
{
    EMIITER_CONTROL_OVERRIDE_ENABLE = 0U,
    EMIITER_CONTROL_STATE,
    EMITTER_PWM_CONTROL_H, 
    EMIITER_PWM_CONTROL_L,

    MUX_CONTROL_OVERRIDE_ENABLE,
    MUX_CONTROL_STATE,

    SIZE_OF_RX_BUFFER,

} usb_rx_buffer_index_E;

typedef enum
{
    PACKET_IDENTIFIER = 0U,
    SENSOR_CHANNEL_1_H,      // Upper bits for sensor mux1 reading
    SENSOR_CHANNEL_1_L,      // Lower bits for sensor mux1 reading
    SENSOR_CHANNEL_2_H,      // Upper bits for sensor mux2 reading
    SENSOR_CHANNEL_2_L,      // Lower bits for sensor mux2 reading
    SENSOR_CHANNEL_3_H,      // Upper bits for sensor mux3 reading
    SENSOR_CHANNEL_3_L,      // Lower bits for sensor mux3 reading
    EMITTER_STATUS,          // Emitter status: 0 -> off, 1 -> 660NM, 2 -> 940NM

    NUM_OF_BYTES_PER_SENSOR_MODULE,
} usb_tx_sensor_buffer_index_E;

typedef struct
{
    // User emitter control variables
    bool user_emitter_control_override_enabled;
    emitter_control_state_E emitter_control_state;
    uint16_t emitter_pwm_control; // Each bit maps to a PWM channel

    // User mux control variables
    bool user_mux_control_override_enabled;
    mux_input_channel_E mux_control_state;

} serial_interface_rx_vars_S; 

/* FUNCTION DEFINITIONS */

void serial_interface_rx_parse_data(uint8_t *usb_receive_buffer);
bool serial_interface_rx_get_user_emitter_control_override_enable(void);
emitter_control_state_E serial_interface_rx_get_emitter_control_state(void);
uint16_t serial_interface_rx_get_user_emitter_controls(void);
bool serial_interface_rx_get_user_mux_control_override_enable(void);
mux_input_channel_E serial_interface_rx_get_user_mux_control_state(void);
void serial_interface_tx_send_sensor_data(void);

#endif /* INC_SERIAL_INTERFACE_H_ */
