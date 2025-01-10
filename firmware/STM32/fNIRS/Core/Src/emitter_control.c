
/* INCLUDES */
#include "emitter_control.h"
#include "pwm_driver.h"

/* DEFINES */
// Note: lsb is read/write bit: R = 0, W = 1
#define PWM_DRIVER_SLAVE_ADDR_READ (0b1001011)

/* DATA STRUCTURES */

static pwm_driver_handler_S pwm_config = {
    .device_address         = PWM_DRIVER_SLAVE_ADDR_READ,
    .enable_line_gpio_pin   = PWM_CTRL_EN1_Pin,
    .gpio_port              = PWM_CTRL_EN1_GPIO_Port,
    .i2c_handler            = NULL,
    .device_config_vars     = { 0 },
    .pwm_frequency          = 1000,
    .duty_cycle             = { 0 },
    .phase_shift            = { 0 },
};

static emitter_control_vars_S emitter_control_vars = { 0 };

/* FUNCTION DEFINITIONS */

static void emitter_control_update_pwm_channels(emitter_control_state_E state)
{
    switch (state)
    {
        case IDLE:
            break; 

        case USER_CONTROL: 
            break;

        case SEQUENCER_CONTROL: 
            break;

        case FULLY_ENABLED:
            break;

        case FULLY_DISABLED:
            break;

        default: 
            break;
    }

    if (emitter_control_vars.pwm_frequency != pwm_config.pwm_frequency)
    {
        pwm_driver_update_frequency(&pwm_config, emitter_control_vars.pwm_frequency);
    }

    for (pwm_channel_E i = (pwm_channel_E)0U; i < NUM_OF_PWM_CHANNELS; i++)
    {
        if (emitter_control_vars.duty_cycle[i] != pwm_config.duty_cycle[i] || emitter_control_vars.phase_shift[i] != pwm_config.phase_shift[i])
        {
            pwm_driver_update_individual_patterns(&pwm_config, i, emitter_control_vars.duty_cycle[i], emitter_control_vars.phase_shift[i]);
        }
    }
}

void emitter_control_init(I2C_HandleTypeDef* hi2c)
{
    pwm_config.i2c_handler = hi2c;
    pwm_driver_deassert_enable_line(&pwm_config);
    pwm_driver_config(&pwm_config);
}

void emitter_control_enable(void)
{
    emitter_control_vars.emitter_control_enabled = true;
    pwm_driver_assert_enable_line(&pwm_config); 
}

void emitter_control_disable(void)
{
    pwm_driver_deassert_enable_line(&pwm_config);
    emitter_control_vars.emitter_control_enabled = false;
}

void emitter_control_request_operating_mode(emitter_control_state_E state)
{
    emitter_control_vars.requested_state = state;
}

void emitter_control_update_frequency(float frequency)
{
    emitter_control_vars.pwm_frequency = frequency;
}

void emitter_control_update_duty_and_phase(pwm_channel_E channel, float duty_cycle, float phase_shift)
{
    emitter_control_vars.duty_cycle[channel] = duty_cycle;
    emitter_control_vars.phase_shift[channel] = phase_shift;
}

void emitter_control_state_machine(void)
{
    emitter_control_state_E curr_state = emitter_control_vars.curr_state;
    emitter_control_state_E next_state = curr_state;

    // update timer threshold value to determine the frequency of the state machine
    if (emitter_control_vars.timer > 50U)
    {
        switch (curr_state)
        {
            case IDLE:
                if (emitter_control_vars.requested_state != IDLE)
                {
                    next_state = emitter_control_vars.requested_state;
                }
                break;

            case USER_CONTROL: 
                if (emitter_control_vars.emitter_control_enabled == false)
                {
                    next_state = FULLY_DISABLED;
                }
                break;

            case SEQUENCER_CONTROL: 
                if (emitter_control_vars.emitter_control_enabled == false)
                {
                    next_state = FULLY_DISABLED;
                }
                break;

            case FULLY_ENABLED:
                if (emitter_control_vars.emitter_control_enabled == false)
                {
                    next_state = FULLY_DISABLED;
                }
                break;

            case FULLY_DISABLED:
                if (emitter_control_vars.emitter_control_enabled)
                {
                    next_state = IDLE;
                }
                break;

            default:
                break;
        }

        emitter_control_vars.timer = 0U;
        emitter_control_update_pwm_channels(curr_state);
        emitter_control_vars.curr_state = next_state;
    }
    else
    {
        emitter_control_vars.timer++;
    }
}
