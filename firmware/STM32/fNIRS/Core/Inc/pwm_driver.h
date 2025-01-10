
#ifndef INC_PWM_DRIVER_H_
#define INC_PWM_DRIVER_H_

/* INCLUDES */
#include "main.h"

/* DEFINES */

/* DATA STRUCTURES */
typedef enum
{
    PWM_CHANNEL0 = 0U, 
    PWM_CHANNEL1,
    PWM_CHANNEL2,
    PWM_CHANNEL3,
    PWM_CHANNEL4,
    PWM_CHANNEL5,
    PWM_CHANNEL6,
    PWM_CHANNEL7,
    PWM_CHANNEL8,
    PWM_CHANNEL9,
    PWM_CHANNEL10,
    PWM_CHANNEL11,
    PWM_CHANNEL12,
    PWM_CHANNEL13,
    PWM_CHANNEL14,
    PWM_CHANNEL15,

    NUM_OF_PWM_CHANNELS,
} pwm_channel_E;

typedef struct
{
    const uint8_t device_address;
    I2C_HandleTypeDef *i2c_handler;
} pwm_driver_handler_S;


/* FUNCTION DECLARATIONS */
void pwm_driver_config(pwm_driver_handler_S* handler);
void pwm_driver_update_frequency(pwm_driver_handler_S* handler);
// TODO: add phase control to these functions
void pwm_driver_update_individual_duty_cycle(pwm_driver_handler_S* handler, pwm_channel_E channel, float32_t duty_cycle);
void pwm_driver_update_all_duty_cycles(pwm_driver_handler_S* handler, float32_t duty_cycle);


#endif /* INC_PWM_DRIVER_H_ */
