
#ifndef INC_MUX_CONTROL_H_
#define INC_MUX_CONTROL_H_

/* INCLUDES */
#include "main.h"
#include "stdbool.h"

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
    uint8_t timer;
    mux_input_channel_E curr_input_channel;

} mux_control_handler_S;

/* FUNCTION DECLARATIONS */
void mux_control_init(I2C_HandleTypeDef* hi2c);
void mux_control_sequencer(void);

#endif /* INC_MUX_CONTROL_H_ */
