
/* INCLUDES */
#include "mux_control.h"
#include "gpio_expander.h"
#include "sensing.h"

/* DEFINES */
#define DISABLE_MUXING (0U)

// Note: lsb is the R/W bit: R = 1, W = 0
#define GPIO_EXPANDER_SLAVE_ADDR_ONE_READ (0b01000001)
#define GPIO_EXPANDER_SLAVE_ADDR_TWO_READ (0b01000011)

// GPIO Expander pin states
#define PORT_ZERO_CHANNEL_ONE_PIN_STATE     (0b00100100)
#define PORT_ONE_CHANNEL_ONE_PIN_STATE      (0b00001001)

#define PORT_ZERO_CHANNEL_TWO_PIN_STATE     (0b01101101)
#define PORT_ONE_CHANNEL_TWO_PIN_STATE      (0b00001011)

#define PORT_ZERO_CHANNEL_THREE_PIN_STATE   (0b10110110)
#define PORT_ONE_CHANNEL_THREE_PIN_STATE    (0b00001101)

#define PORT_ZERO_CHANNEL_FOUR_PIN_STATE    (0b11111111)
#define PORT_ONE_CHANNEL_FOUR_PIN_STATE     (0b00001111)

#define PORT_ZERO_DISABLED_PIN_STATE        (0b00000000)
#define PORT_ONE_DISABLED_PIN_STATE         (0b00000000)

#define MUX_SEQUENCER_FREQ_TICKS            (50U)

/* DATA STRUCTURES */
static gpio_expander_handler_S gpio_expander_vars[NUM_OF_MUX_CONTROLS] = 
{
    {
        .device_address = GPIO_EXPANDER_SLAVE_ADDR_ONE_READ,
        .gpio_pin_config = {0x00, 0x00},
        .gpio_polarity_config = {0x00, 0x00},
    },
    {
        .device_address = GPIO_EXPANDER_SLAVE_ADDR_TWO_READ,
        .gpio_pin_config = {0x00, 0x00},
        .gpio_polarity_config = {0x00, 0x00},
    }
};

static mux_control_handler_S mux_control_vars = { 0 };

// gpio expander one:
// mux0: p1_1, p1_2, p1_3 (en): 
// channel 1: write: X | X | X | X | 1 | 0 | 0 | X to port 1
// channel 2: write: X | X | X | X | 1 | 0 | 1 | X to port 1
// channel 3: write: X | X | X | X | 1 | 1 | 0 | X to port 1
// channel 4: write: X | X | X | X | 1 | 1 | 1 | X to port 1
// disabled : write: X | X | X | X | 0 | X | X | X to port 1

// mux1: p0_6, p0_7, p1_0 (en): 
// channel 1: write: 0 | 0 | X | X | X | X | X | X to port 0 and write: X | X | X | X | X | X | X | 1 to port 1 
// channel 2: write: 0 | 1 | X | X | X | X | X | X to port 0 and write: X | X | X | X | X | X | X | 1 to port 1 
// channel 3: write: 1 | 0 | X | X | X | X | X | X to port 0 and write: X | X | X | X | X | X | X | 1 to port 1 
// channel 4: write: 1 | 1 | X | X | X | X | X | X to port 0 and write: X | X | X | X | X | X | X | 1 to port 1 
// disabled : write: X | X | X | X | X | X | X | X to port 0 and write: X | X | X | X | X | X | X | 0 to port 1 

// mux2: p0_3, p0_4, p0_5 (en): 
// channel 1: write: X | X | 1 | 0 | 0 | X | X | X  to port 0 
// channel 2: write: X | X | 1 | 0 | 1 | X | X | X  to port 0 
// channel 3: write: X | X | 1 | 1 | 0 | X | X | X  to port 0 
// channel 4: write: X | X | 1 | 1 | 1 | X | X | X  to port 0 
// disabled:  write: X | X | 0 | X | X | X | X | X  to port 0 

// mux3: p0_0, p0_1, p0_2 (en): 
// channel 1: write: X | X | X | X | X | 1 | 0 | 0 to port 0
// channel 2: write: X | X | X | X | X | 1 | 0 | 1 to port 0
// channel 3: write: X | X | X | X | X | 1 | 1 | 0 to port 0
// channel 4: write: X | X | X | X | X | 1 | 1 | 1 to port 0
// disabled : write: X | X | X | X | X | 0 | X | X to port 0

// combined:
// channel 1: 
// write: 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 to port 0 -> 00100100
// write: X | X | X | X | 1 | 0 | 0 | 1 to port 1 -> xxxx1001
// channel 2:
// write: 0 | 1 | 1 | 0 | 1 | 1 | 0 | 1 to port 0 -> 01101101
// write: X | X | X | X | 1 | 0 | 1 | 1 to port 1 -> xxxx1011
// channel 3:
// write: 1 | 0 | 1 | 1 | 0 | 1 | 1 | 0 to port 0 -> 10110110
// write: X | X | X | X | 1 | 1 | 0 | 1 to port 1 -> xxxx1101
// channel 4:
// write: 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 to port 0 -> 11111111
// write: X | X | X | X | 1 | 1 | 1 | 1 to port 1 -> xxxx1111
// disabled:
// write: X | X | 0 | X | X | 0 | X | X to port 0 -> xx0xx0xx
// write: X | X | X | X | 0 | X | X | 0 to port 1 -> xxxx0xx0

// gpio expander two:
// mux4: p0_0, p0_1, p0_2 (en): same as mux3 above
// mux5: p0_3, p0_4, p0_5 (en): same as mux2 above
// mux6: p0_6, p0_7, p1_0 (en): same as mux1 above
// mux7: p1_1, p1_2, p1_3 (en): same as mux0 above

/* FUNCTION DEFINITION */
static void mux_control_update_gpios(mux_input_channel_E input_channel)
{
    switch (input_channel)
    {
        case MUX_INPUT_CHANNEL_ONE:
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_ONE_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ONE, PORT_ONE_CHANNEL_ONE_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_ONE_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ONE, PORT_ONE_CHANNEL_ONE_PIN_STATE);
            break;

        case MUX_INPUT_CHANNEL_TWO:
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_TWO_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ONE, PORT_ONE_CHANNEL_TWO_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_TWO_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ONE, PORT_ONE_CHANNEL_TWO_PIN_STATE);
            break;

        case MUX_INPUT_CHANNEL_THREE:
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_THREE_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ONE, PORT_ONE_CHANNEL_THREE_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_THREE_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ONE, PORT_ONE_CHANNEL_THREE_PIN_STATE);
            break;

        case MUX_INPUT_CHANNEL_FOUR:
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_FOUR_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ONE, PORT_ONE_CHANNEL_FOUR_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ZERO, PORT_ZERO_CHANNEL_FOUR_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ONE, PORT_ONE_CHANNEL_FOUR_PIN_STATE);
            break;

        case MUX_DISABLED:
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ZERO, PORT_ZERO_DISABLED_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_ONE], GPIO_PORT_ONE, PORT_ONE_DISABLED_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ZERO, PORT_ZERO_DISABLED_PIN_STATE);
            gpio_expander_write_port(&gpio_expander_vars[MUX_CONTROL_TWO], GPIO_PORT_ONE, PORT_ONE_DISABLED_PIN_STATE);
            break;

        default:
            break;
    }
}

void mux_control_init(I2C_HandleTypeDef* hi2c)
{
    gpio_expander_vars[MUX_CONTROL_ONE].i2c_handler = hi2c;
    gpio_expander_vars[MUX_CONTROL_TWO].i2c_handler = hi2c;

    for (int i = 0; i < NUM_OF_MUX_CONTROLS; i++)
    {
        gpio_expander_config(&gpio_expander_vars[i]);
    }

    // Initially disable all muxes
    mux_control_update_gpios(MUX_DISABLED);
}

mux_input_channel_E mux_control_get_curr_input_channel(void)
{
    return mux_control_vars.curr_input_channel;
}

void mux_control_enable_sequencer(void)
{
    mux_control_vars.enabled = true;
}

void mux_control_sequencer(void)
{
    if (mux_control_vars.mux_timer > MUX_SEQUENCER_FREQ_TICKS)
    {
        mux_input_channel_E next_channel = mux_control_vars.curr_input_channel;

        switch (next_channel)
        {
            case MUX_INPUT_CHANNEL_ONE:
                next_channel = MUX_INPUT_CHANNEL_TWO;
                break;

            case MUX_INPUT_CHANNEL_TWO:
                next_channel = MUX_INPUT_CHANNEL_THREE;
                break;

            case MUX_INPUT_CHANNEL_THREE:
                next_channel = MUX_INPUT_CHANNEL_ONE;
                break;

            case MUX_INPUT_CHANNEL_FOUR:
                // Note: channel four doesn't have direct input in hardware
                next_channel = MUX_INPUT_CHANNEL_ONE;
                break;

            case MUX_DISABLED:
                if (mux_control_vars.enabled)
                {
                    next_channel = MUX_INPUT_CHANNEL_FOUR;
                }
                break;

            default:
                break;
        }

    #if DISABLE_MUXING
        next_channel = MUX_INPUT_CHANNEL_ONE;
    #endif

        if (mux_control_vars.mux_control_ovr)
        {
            next_channel = mux_control_vars.input_channel_ovr;
        }

    #if !DISABLE_MUXING
        __disable_irq();
    #endif
        mux_control_update_gpios(next_channel);
        mux_control_vars.curr_input_channel = next_channel;
    #if !DISABLE_MUXING
        __enable_irq();
    #endif
        mux_control_vars.mux_timer = 0U;
    }
    else
    {
        mux_control_vars.mux_timer++;
    }
}

void mux_control_enable_sequencer_override(void)
{
    mux_control_vars.mux_control_ovr = true;
}

void mux_control_disable_sequencer_override(void)
{
    mux_control_vars.mux_control_ovr = false;
}

void mux_control_set_input_channel_ovr(mux_input_channel_E channel)
{
    mux_control_vars.input_channel_ovr = channel;
}

#if DEBUG_GPIO_EXPANDER
uint8_t test_mux_control_read_addr(uint8_t reg_addr, mux_controller_E mux)
{
    return gpio_expander_debug_read_address(&gpio_expander_vars[mux], reg_addr);
}
#endif // DEBUG_GPIO_EXPANDER
