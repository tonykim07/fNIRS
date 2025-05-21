
#ifndef INC_MUX_CONTROL_H_
#define INC_MUX_CONTROL_H_

/* INCLUDES */
#include "main.h"
#include <stdbool.h>
#include "gpio_expander.h"

/* DEFINES */

/* DATA STRUCTURES */
typedef enum
{ 
    MUX_CONTROL_ONE = 0U,
    MUX_CONTROL_TWO,

    NUM_OF_MUX_CONTROLS,
} mux_controller_E;

typedef enum
{
    MUX_DISABLED = 0U,
    MUX_INPUT_CHANNEL_ONE,
    MUX_INPUT_CHANNEL_TWO,
    MUX_INPUT_CHANNEL_THREE,
    MUX_INPUT_CHANNEL_FOUR,

    NUM_OF_INPUT_CHANNELS,
} mux_input_channel_E;

typedef struct
{
    bool enabled;
    bool mux_control_ovr;
    uint8_t mux_timer;
    mux_input_channel_E curr_input_channel;
    mux_input_channel_E input_channel_ovr;

} mux_control_handler_S;

/* FUNCTION DECLARATIONS */
void mux_control_init(I2C_HandleTypeDef* hi2c);
mux_input_channel_E mux_control_get_curr_input_channel(void);
void mux_control_enable_sequencer(void);
void mux_control_sequencer(void);
void mux_control_enable_sequencer_override(void);
void mux_control_disable_sequencer_override(void);
void mux_control_set_input_channel_ovr(mux_input_channel_E channel);

#if (DEBUG_GPIO_EXPANDER)
uint8_t test_mux_control_read_addr(uint8_t reg_addr, mux_controller_E mux);
#endif // DEBUG_GPIO_EXPANDER

#endif /* INC_MUX_CONTROL_H_ */
