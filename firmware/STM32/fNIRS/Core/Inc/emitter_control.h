
#ifndef INC_EMITTER_CONTROL_H_
#define INC_EMITTER_CONTROL_H_

/* INCLUDES */
#include "main.h"
#include "pwm_driver.h"

/* DEFINES */

/* DATA STRUCTURES */

typedef enum
{
    IDLE = 0U, 
    USER_CONTROL, 
    SEQUENCER_CONTROL,
    FULLY_ENABLED, 
    FULLY_DISABLED,

    NUM_OF_EMIITER_CONTROL_STATES,
} emitter_control_state_E;

typedef struct
{
    bool emitter_control_enabled;
    uint8_t timer;
    emitter_control_state_E curr_state;
    emitter_control_state_E requested_state;

    float pwm_frequency;
    float duty_cycle[NUM_OF_PWM_CHANNELS];
    float phase_shift[NUM_OF_PWM_CHANNELS];

} emitter_control_vars_S;

/* FUNCTION DECLARATIONS */
void emitter_control_init(I2C_HandleTypeDef* hi2c);
void emitter_control_enable(void);
void emitter_control_disable(void);
void emitter_control_request_operating_mode(emitter_control_state_E state);
void emitter_control_update_frequency(float frequency);
void emitter_control_update_duty_and_phase(pwm_channel_E channel, float duty_cycle, float phase_shift);
void emitter_control_state_machine(void);

#endif /* INC_EMITTER_CONTROL_H_ */
