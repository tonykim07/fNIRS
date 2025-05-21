
/* INCLUDES */
#include "emitter_control.h"
#include "pwm_driver.h"
#include "serial_interface.h"
#include "isr.h"

/* DEFINES */
// Note: lsb is read/write bit: R = 1, W = 0
#define PWM_DRIVER_SLAVE_ADDR_READ (0b10001011)
#define DEFAULT_DUTY_CYCLE (1.00)
#define DEFAULT_PHASE_SHIFT (0.00)
#define DEFAULT_PWM_FREQUENCY (1500)
#define ZERO_DUTY_CYCLE (0.00)

/* DATA STRUCTURES */

static pwm_driver_handler_S pwm_config = {
    .device_address         = PWM_DRIVER_SLAVE_ADDR_READ,
    .enable_line_gpio_pin   = PWM_CTRL_EN1_Pin,
    .gpio_port              = PWM_CTRL_EN1_GPIO_Port,
    .i2c_handler            = NULL,
    .device_config_vars     = { 0 },
    .pwm_frequency          = DEFAULT_PWM_FREQUENCY,
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

        case DISABLED:
            for (pwm_channel_E i = (pwm_channel_E)0; i < NUM_OF_PWM_CHANNELS; i++)
            {
                emitter_control_vars.duty_cycle[i] = ZERO_DUTY_CYCLE;
                emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
            }
            break; 

        case DEFAULT_MODE:
            // Odd numbered modules enable 940NM emitters
            // Even numbered modules enable 660NM emitters

            // Module 1
            emitter_control_vars.duty_cycle[PWM_CHANNEL0] = ZERO_DUTY_CYCLE; 
            emitter_control_vars.phase_shift[PWM_CHANNEL0] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL1] = DEFAULT_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL1] = DEFAULT_PHASE_SHIFT;

            // Module 2
            emitter_control_vars.duty_cycle[PWM_CHANNEL2] = DEFAULT_DUTY_CYCLE; 
            emitter_control_vars.phase_shift[PWM_CHANNEL2] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL3] = ZERO_DUTY_CYCLE;    
            emitter_control_vars.phase_shift[PWM_CHANNEL3] = DEFAULT_PHASE_SHIFT;

            // Module 3
            emitter_control_vars.duty_cycle[PWM_CHANNEL4] = ZERO_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL4] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL5] = DEFAULT_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL5] = DEFAULT_PHASE_SHIFT;

            // Module 4
            emitter_control_vars.duty_cycle[PWM_CHANNEL6] = DEFAULT_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL6] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL7] = ZERO_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL7] = DEFAULT_PHASE_SHIFT;
            // Module 5
            emitter_control_vars.duty_cycle[PWM_CHANNEL8] = ZERO_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL8] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL9] = DEFAULT_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL9] = DEFAULT_PHASE_SHIFT;

            // Module 6
            emitter_control_vars.duty_cycle[PWM_CHANNEL10] = DEFAULT_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL10] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL11] = ZERO_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL11] = DEFAULT_PHASE_SHIFT;

            // Module 7
            emitter_control_vars.duty_cycle[PWM_CHANNEL12] = ZERO_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL12] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL13] = DEFAULT_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL13] = DEFAULT_PHASE_SHIFT;

            // Module 8
            emitter_control_vars.duty_cycle[PWM_CHANNEL14] = DEFAULT_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL14] = DEFAULT_PHASE_SHIFT;
            emitter_control_vars.duty_cycle[PWM_CHANNEL15] = ZERO_DUTY_CYCLE;
            emitter_control_vars.phase_shift[PWM_CHANNEL15] = DEFAULT_PHASE_SHIFT;

            emitter_control_vars.pwm_frequency = DEFAULT_PWM_FREQUENCY;
            break; 

        case USER_CONTROL:
            uint16_t override_data = emitter_control_vars.user_control_settings;
            for (pwm_channel_E i = (pwm_channel_E)0U; i < NUM_OF_PWM_CHANNELS; i++)
            {
                emitter_control_vars.duty_cycle[i] = (float)((override_data >> i) & 0x1);
            }
            emitter_control_vars.pwm_frequency = DEFAULT_PWM_FREQUENCY;
            break;

        case CYCLING: 
            for (pwm_channel_E i = (pwm_channel_E)0; i < NUM_OF_PWM_CHANNELS; i++)
            {
                emitter_control_vars.duty_cycle[i] = ZERO_DUTY_CYCLE; 
                emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
            }

            if (emitter_control_vars.timer % 2U == 0U)
            {
                for (pwm_channel_E i = (pwm_channel_E)0; i < NUM_OF_PWM_CHANNELS; i+=2)
                {
                    emitter_control_vars.duty_cycle[i] = DEFAULT_DUTY_CYCLE;
                    emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
                }
            }
            else
            {
                for (pwm_channel_E i = (pwm_channel_E)1; i < NUM_OF_PWM_CHANNELS; i+=2)
                {
                    emitter_control_vars.duty_cycle[i] = DEFAULT_DUTY_CYCLE;
                    emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
                }
            }
            break;

        case FULLY_ENABLED_940NM:
            // Even channels correspond to 940NM emitter
            for (pwm_channel_E i = (pwm_channel_E)0; i < NUM_OF_PWM_CHANNELS; i+=2)
            {
                emitter_control_vars.duty_cycle[i] = DEFAULT_DUTY_CYCLE;
                emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
            }

            // Make sure 660NM emitters are off
            for (pwm_channel_E i = (pwm_channel_E)1; i < NUM_OF_PWM_CHANNELS; i+=2)
            {
                emitter_control_vars.duty_cycle[i] = ZERO_DUTY_CYCLE; 
                emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
            }
            break;

        case FULLY_ENABLED_660NM:
            // Odd channels correspond to 660NM emitter
            for (pwm_channel_E i = (pwm_channel_E)1; i < NUM_OF_PWM_CHANNELS; i+=2)
            {
                emitter_control_vars.duty_cycle[i] = DEFAULT_DUTY_CYCLE; 
                emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
            }

            // Make sure 660NM emitters are off
            for (pwm_channel_E i = (pwm_channel_E)0; i < NUM_OF_PWM_CHANNELS; i+=2)
            {
                emitter_control_vars.duty_cycle[i] = ZERO_DUTY_CYCLE;
                emitter_control_vars.phase_shift[i] = DEFAULT_PHASE_SHIFT;
            }
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
        pwm_driver_update_individual_patterns(&pwm_config, i, emitter_control_vars.duty_cycle[i], emitter_control_vars.phase_shift[i]);
    }
}

void emitter_control_init(I2C_HandleTypeDef* hi2c)
{
    pwm_config.i2c_handler = hi2c;
    pwm_config.device_config_vars.totem_pole_enable = true;
    pwm_driver_assert_enable_line(&pwm_config);
    pwm_driver_config(&pwm_config);
}

void emitter_control_enable(void)
{
    emitter_control_vars.emitter_control_enabled = true;
    // Deasserting enables the controller
    pwm_driver_deassert_enable_line(&pwm_config); 
}

void emitter_control_disable(void)
{
    pwm_driver_assert_enable_line(&pwm_config);
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
    uint16_t user_control_settings = serial_interface_rx_get_user_emitter_controls();
    bool run_state_machine = isr_get_emitter_control_timer_flag();
    bool user_override_enabled = serial_interface_rx_get_user_emitter_control_override_enable();
    bool user_control_updated = (user_control_settings != emitter_control_vars.user_control_settings);
    
    if (run_state_machine || 
        (user_override_enabled && curr_state != USER_CONTROL && curr_state != CYCLING) || 
        (user_override_enabled && curr_state == USER_CONTROL && user_control_updated))
    {
        switch (curr_state)
        {
            case DISABLED: 
                if (emitter_control_vars.emitter_control_enabled || emitter_control_vars.requested_state != curr_state)
                {
                    next_state = IDLE;
                }
                break;

            case IDLE:
                if (emitter_control_vars.emitter_control_enabled == false)
                {
                    next_state = DISABLED;
                }
                else if (emitter_control_vars.requested_state != curr_state)
                {
                    next_state = emitter_control_vars.requested_state;
                }
                break;
            
            case DEFAULT_MODE: 
            case USER_CONTROL: 
            case CYCLING:
            case FULLY_ENABLED_940NM:
            case FULLY_ENABLED_660NM:
                if (emitter_control_vars.emitter_control_enabled == false)
                {
                    next_state = DISABLED;
                }
                else if (emitter_control_vars.requested_state != curr_state)
                {
                    next_state = IDLE;
                }
                break;

            default:
                break;
        }

        emitter_control_vars.timer++;
        emitter_control_vars.user_control_settings = user_control_settings;
        emitter_control_update_pwm_channels(curr_state);
        emitter_control_vars.curr_state = next_state;
        isr_reset_emitter_control_timer_flag();
    }
}

bool emitter_control_is_emitter_active(pwm_channel_E channel)
{
    return (emitter_control_vars.duty_cycle[channel] > 0);
}

#if DEBUG_PWM_DRIVER
uint8_t test_pwm_driver_read_addr(uint8_t reg_addr)
{
    return pwm_driver_debug_read_address(&pwm_config, reg_addr);
}
#endif // DEBUG_PWM_DRIVER
