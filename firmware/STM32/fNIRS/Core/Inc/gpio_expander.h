
#ifndef INC_GPIO_EXPANDER_H_
#define INC_GPIO_EXPANDER_H_

/* INCLUDES */
//#include "stm32l4xx_hal_conf.h"
#include "main.h"
/* DEFINES */

/* DATA STRUCTURES */

typedef enum
{
    PIN_LOW = 0U, 
    PIN_HIGH,
} gpio_expander_pin_state_E;

typedef enum
{
    GPIO_PORT_ZERO = 0U,
    GPIO_PORT_ONE,
    NUM_OF_GPIO_PORTS,
} gpio_expander_port_E;

typedef struct
{
    // GPIO control
    uint8_t gpio_pin_config[NUM_OF_GPIO_PORTS];
    uint8_t gpio_polarity_config[NUM_OF_GPIO_PORTS];

    // Device Interface
    const uint8_t device_address;  
    I2C_HandleTypeDef *i2c_handler; 
} gpio_expander_handler_S;


/* FUNCTIONS DECLARATIONS */
void gpio_expander_config(gpio_expander_handler_S* handler);
void gpio_expander_write_pin(gpio_expander_handler_S* handler, gpio_expander_port_E port, uint8_t pin, gpio_expander_pin_state_E pin_state);
void gpio_expander_write_port(gpio_expander_handler_S* handler, gpio_expander_port_E port, uint8_t pin_states);

#endif /* INC_GPIO_EXPANDER_H_ */
