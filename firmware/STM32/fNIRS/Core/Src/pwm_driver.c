
/* INCLUDES */
#include "pwm_driver.h"

/* DEFINES */

// Configuration registers
#define MODE1_ADDR      (0x00)
#define MODE2_ADDR      (0x01)
#define SUBADR1_ADDR    (0x02)
#define SUBADR2_ADDR    (0x03)
#define SUBADR3_ADDR    (0x04)
#define ALLCALLADR_ADDR (0x05)

// PWM control registers
#define LED_ON_L_BASEADDR (0x06)
#define LED_ON_H_BASEADDR (0x07)
#define LED_OFF_L_BASEADDR (0x08)
#define LED_OFF_H_BASEADDR (0x09)
#define LED_ADDR(addr, offset) (uint8_t)((addr) + (4U)*(offset))

#define ALL_LED_ON_L_ADDR (0xFA)
#define ALL_LED_ON_H_ADDR (0xFB)
#define ALL_LED_OFF_L_ADDR (0xFC)
#define ALL_LED_OFF_H_ADDR (0xFD)

// PWM frequency control register
#define PRE_SCALE_ADDR  (0xFE)

/* FUNCTION DEFINITIONS */

void pwm_driver_config(pwm_driver_handler_S* handler)
{

}

void pwm_driver_update_frequency(pwm_driver_handler_S* handler)
{

}

void pwm_driver_update_individual_duty_cycle(pwm_driver_handler_S* handler, pwm_channel_E channel, float32_t duty_cycle)
{

}

void pwm_driver_update_all_duty_cycles(pwm_driver_handler_S* handler, float32_t duty_cycle)
{
    
}
