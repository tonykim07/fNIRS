
/* INCLUDES */
#include "gpio_expander.h"

/* DEFINES */
#define INPUT_PORT_ZERO_ADDR                (0x00)
#define INPUT_PORT_ONE_ADDR                 (0x01)
#define OUTPUT_PORT_ZERO_ADDR               (0x02)
#define OUTPUT_PORT_ONE_ADDR                (0x03)
#define POLARITY_INVERSION_PORT_ZERO_ADDR   (0x04)
#define POLARITY_INVERSION_PORT_ONE_ADDR    (0x05)
#define CONFIG_PORT_ZERO_ADDR               (0x06)
#define CONFIG_PORT_ONE_ADDR                (0x07)

/* FUNCTION DEFINITIONS */

void gpio_expander_config(gpio_expander_handler_S* handler)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr = handler->device_address & ~(0x1);

    // Write pin io config to device (can run burst transfer, but doing one at a time for now) 
    HAL_I2C_Mem_Write(i2c_handler, device_addr, CONFIG_PORT_ZERO_ADDR, I2C_MEMADD_SIZE_8BIT, &handler->gpio_pin_config[GPIO_PORT_ZERO],
                      sizeof(handler->gpio_pin_config[GPIO_PORT_ZERO]), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr, CONFIG_PORT_ONE_ADDR, I2C_MEMADD_SIZE_8BIT, &handler->gpio_pin_config[GPIO_PORT_ONE],
                      sizeof(handler->gpio_pin_config[GPIO_PORT_ONE]), HAL_MAX_DELAY);
    
    // Write pin polarity config to device (can run burst transfer, but doing one at a time for now) 
    HAL_I2C_Mem_Write(i2c_handler, device_addr, POLARITY_INVERSION_PORT_ZERO_ADDR, I2C_MEMADD_SIZE_8BIT, &handler->gpio_pin_config[GPIO_PORT_ZERO],
                      sizeof(handler->gpio_pin_config[GPIO_PORT_ZERO]), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr, POLARITY_INVERSION_PORT_ONE_ADDR, I2C_MEMADD_SIZE_8BIT, &handler->gpio_pin_config[GPIO_PORT_ONE],
                      sizeof(handler->gpio_pin_config[GPIO_PORT_ONE]), HAL_MAX_DELAY);
}

void gpio_expander_write_pin(gpio_expander_handler_S* handler, gpio_expander_port_E port, uint8_t pin, gpio_expander_pin_state_E pin_state)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr_read = handler->device_address;
    const uint8_t device_addr_write = handler->device_address & ~(0x1);

    uint8_t output_port_addr = (port == GPIO_PORT_ZERO) ? OUTPUT_PORT_ZERO_ADDR : OUTPUT_PORT_ONE_ADDR;
    uint8_t pin_states = 0;

    HAL_I2C_Mem_Read(i2c_handler, device_addr_read, output_port_addr, I2C_MEMADD_SIZE_8BIT, &pin_states, sizeof(uint8_t), HAL_MAX_DELAY);
    
    if (pin_state == PIN_HIGH)
    {
        pin_states |= (1U << pin);
    } 
    else 
    {
        pin_states &= ~(1U << pin);
    }   

    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, output_port_addr, I2C_MEMADD_SIZE_8BIT, &pin_states, sizeof(uint8_t), HAL_MAX_DELAY);
}

void gpio_expander_write_port(gpio_expander_handler_S* handler, gpio_expander_port_E port, uint8_t pin_states)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr = handler->device_address & ~(0x1);

    uint8_t output_port_addr = (port == GPIO_PORT_ZERO) ? OUTPUT_PORT_ZERO_ADDR : OUTPUT_PORT_ONE_ADDR;
    
    HAL_I2C_Mem_Write(i2c_handler, device_addr, output_port_addr, I2C_MEMADD_SIZE_8BIT, &pin_states, sizeof(uint8_t), HAL_MAX_DELAY);
}

#if DEBUG_GPIO_EXPANDER
void gpio_expander_debug_write_address(gpio_expander_handler_S* handler, uint8_t reg_addr, uint8_t data_to_write)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr = handler->device_address & ~(0x1);

    HAL_I2C_Mem_Write(i2c_handler, device_addr, reg_addr, I2C_MEMADD_SIZE_8BIT, &data_to_write, sizeof(uint8_t), HAL_MAX_DELAY);
}

uint8_t gpio_expander_debug_read_address(gpio_expander_handler_S* handler, uint8_t reg_addr)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr = handler->device_address;

    uint8_t data = 0;
    HAL_I2C_Mem_Read(i2c_handler, device_addr, reg_addr, I2C_MEMADD_SIZE_8BIT, &data, sizeof(uint8_t), HAL_MAX_DELAY);

    return data;
}
#endif // DEBUG_GPIO_EXPANDER