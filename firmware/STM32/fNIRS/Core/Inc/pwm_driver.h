
#ifndef INC_PWM_DRIVER_H_
#define INC_PWM_DRIVER_H_

/* INCLUDES */
#include "main.h"
#include "stdbool.h"

/* DEFINES */
#define DEBUG_PWM_DRIVER (0U)

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
    bool restart_enable;
    bool auto_increment_enable;
    bool sleep_mode_enable;
    bool sub_addr_one_enable; 
    bool sub_addr_two_enable;
    bool sub_addr_three_enable;

    bool inverted_output_enable;
    bool totem_pole_enable;
    bool output_default_on_enable;
} device_config_S;

typedef struct
{
    const uint8_t device_address;
    const uint16_t enable_line_gpio_pin;
    GPIO_TypeDef* gpio_port;
    I2C_HandleTypeDef *i2c_handler;

    device_config_S device_config_vars;

    float pwm_frequency;
    float duty_cycle[NUM_OF_PWM_CHANNELS];
    float phase_shift[NUM_OF_PWM_CHANNELS];

} pwm_driver_handler_S;


/* FUNCTION DECLARATIONS */
void pwm_driver_config(pwm_driver_handler_S* handler);
void pwm_driver_assert_enable_line(pwm_driver_handler_S* handler);
void pwm_driver_deassert_enable_line(pwm_driver_handler_S* handler);
void pwm_driver_enable_sleep_mode(pwm_driver_handler_S* handler);
void pwm_driver_disable_sleep_mode(pwm_driver_handler_S* handler);
void pwm_driver_update_frequency(pwm_driver_handler_S* handler, float frequency_hz);
void pwm_driver_update_individual_patterns(pwm_driver_handler_S* handler, pwm_channel_E channel, float duty_cycle, float phase_shift);
void pwm_driver_update_all_patterns(pwm_driver_handler_S* handler, float duty_cycle, float phase_shift);

#if DEBUG_PWM_DRIVER
void pwm_driver_debug_write_address(pwm_driver_handler_S* handler, uint8_t reg_addr, uint8_t data_to_write);
uint8_t pwm_driver_debug_read_address(pwm_driver_handler_S* handler, uint8_t reg_addr);
#endif // DEBUG_PWM_DRIVER

#endif /* INC_PWM_DRIVER_H_ */
