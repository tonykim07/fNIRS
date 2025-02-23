
/* INCLUDES */
#include "pwm_driver.h"

/* DEFINES */

// Configuration registers
#define MODE1_ADDR      (0x00)
#define MODE2_ADDR      (0x01)

// Individual PWM control registers
#define LED_ON_L_BASEADDR (0x06)
#define LED_ON_H_BASEADDR (0x07)
#define LED_OFF_L_BASEADDR (0x08)
#define LED_OFF_H_BASEADDR (0x09)
#define LED_ADDR(addr, offset) (uint8_t)((addr) + (4U)*(offset))

// PWM control registers for controlling all channels at once
#define ALL_LED_ON_L_ADDR (0xFA)
#define ALL_LED_ON_H_ADDR (0xFB)
#define ALL_LED_OFF_L_ADDR (0xFC)
#define ALL_LED_OFF_H_ADDR (0xFD)

// PWM frequency control register
#define PRE_SCALE_ADDR  (0xFE)

#define INTERNAL_OSC_CLOCK_FREQ (25e6F)
#define PWM_DRIVER_MAX_PRESCALE (0xFF)
#define PWM_DRIVER_MIN_PRESCALE (0x03)

/* FUNCTION DEFINITIONS */

void pwm_driver_config(pwm_driver_handler_S* handler)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr_write = handler->device_address & ~(0x1); 

    uint8_t mode1_reg_config = 0U; 
    uint8_t mode2_reg_config = 0;

    if (handler->device_config_vars.restart_enable)
    {
        mode1_reg_config |= (1U << 7U);
    }
    if (handler->device_config_vars.auto_increment_enable)
    {
        mode1_reg_config |= (1U << 5U);
    }
    if (handler->device_config_vars.sleep_mode_enable)
    {
        mode1_reg_config |= (1U << 4U);
    }
    if (handler->device_config_vars.sub_addr_one_enable)
    {
        mode1_reg_config |= (1U << 3U);
    }
    if (handler->device_config_vars.sub_addr_two_enable)
    {
        mode1_reg_config |= (1U << 2U);
    }
    if (handler->device_config_vars.sub_addr_three_enable)
    {
        mode1_reg_config |= (1U << 1U);
    }

    if (handler->device_config_vars.inverted_output_enable)
    {
        mode2_reg_config |= (1U << 4U);
    }
    if (handler->device_config_vars.totem_pole_enable)
    {
        mode2_reg_config |= (1U << 2U);
    }
    if (handler->device_config_vars.output_default_on_enable)
    {
        mode2_reg_config |= (1U);
    }

    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, MODE1_ADDR, I2C_MEMADD_SIZE_8BIT, &mode1_reg_config,
                      sizeof(mode1_reg_config), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, MODE2_ADDR, I2C_MEMADD_SIZE_8BIT, &mode2_reg_config,
                      sizeof(mode2_reg_config), HAL_MAX_DELAY);
}

void pwm_driver_assert_enable_line(pwm_driver_handler_S* handler)
{
    HAL_GPIO_WritePin(handler->gpio_port, handler->enable_line_gpio_pin, GPIO_PIN_SET);
}

void pwm_driver_deassert_enable_line(pwm_driver_handler_S* handler)
{
    HAL_GPIO_WritePin(handler->gpio_port, handler->enable_line_gpio_pin, GPIO_PIN_RESET);
}

void pwm_driver_enable_sleep_mode(pwm_driver_handler_S* handler)
{
    uint8_t mode1_reg_config;
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr_read = handler->device_address;
    const uint8_t device_addr_write = handler->device_address & ~(0x1);

    HAL_I2C_Mem_Read(i2c_handler, device_addr_read, MODE1_ADDR, I2C_MEMADD_SIZE_8BIT, &mode1_reg_config,
                     sizeof(mode1_reg_config), HAL_MAX_DELAY);
    
    mode1_reg_config |= (1U << 4U);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, MODE1_ADDR, I2C_MEMADD_SIZE_8BIT, &mode1_reg_config,
                      sizeof(mode1_reg_config), HAL_MAX_DELAY);
}

void pwm_driver_disable_sleep_mode(pwm_driver_handler_S* handler)
{
    uint8_t mode1_reg_config;
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr_read = handler->device_address;
    const uint8_t device_addr_write = handler->device_address & ~(0x1);

    HAL_I2C_Mem_Read(i2c_handler, device_addr_read, MODE1_ADDR, I2C_MEMADD_SIZE_8BIT, &mode1_reg_config,
                     sizeof(mode1_reg_config), HAL_MAX_DELAY);
    
    mode1_reg_config &= ~(1U << 4U);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, MODE1_ADDR, I2C_MEMADD_SIZE_8BIT, &mode1_reg_config,
                      sizeof(mode1_reg_config), HAL_MAX_DELAY);
}

void pwm_driver_update_frequency(pwm_driver_handler_S* handler, float frequency_hz)
{
    handler->pwm_frequency = frequency_hz;

    // The frequency can not be changed if the device is not sleeping
    pwm_driver_enable_sleep_mode(handler);

    // Frequency is limited from 24Hz to 1526 Hz
    uint8_t pre_scale = (uint8_t)((INTERNAL_OSC_CLOCK_FREQ / (4096U * frequency_hz)) - 1U);

    // Maximum prescale value results in frequency of 24 Hz
    if (pre_scale > PWM_DRIVER_MAX_PRESCALE)
    {
        pre_scale = PWM_DRIVER_MAX_PRESCALE;
    }
    // Minimum prescale value results in frequency of 1526 Hz
    if (pre_scale < PWM_DRIVER_MIN_PRESCALE)
    {
        pre_scale = PWM_DRIVER_MIN_PRESCALE;
    }

    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr_write = handler->device_address & ~(0x1);

    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, PRE_SCALE_ADDR, I2C_MEMADD_SIZE_8BIT, &pre_scale,
                      sizeof(pre_scale), HAL_MAX_DELAY);

    // Enable the PWMs
    pwm_driver_disable_sleep_mode(handler);
}

void pwm_driver_update_individual_patterns(pwm_driver_handler_S* handler, pwm_channel_E channel, float duty_cycle, float phase_shift)
{
    if (duty_cycle < 0)
    {
        duty_cycle = 0;
    }
    if (phase_shift < 0)
    {
        phase_shift = 0;
    }

    if (duty_cycle > 1)
    {
        duty_cycle = 1;
    }
    if (phase_shift > 1)
    {
        phase_shift = 0;
    }

    handler->duty_cycle[channel] = duty_cycle; 
    handler->phase_shift[channel] = phase_shift;

    // PWM count registers are 12bits, period is 4096 counts
    const uint16_t phase_counts = (uint16_t)(((1U << 12U) * phase_shift) - 1U);
    const uint16_t duty_counts = (uint16_t)(((1U << 12U) * duty_cycle) - 1U);
    
    uint16_t rising_edge = phase_counts;
    uint16_t falling_edge = phase_counts + duty_counts;

    if (falling_edge > (1U << 12U))
    {
        falling_edge -= (1U << 12U);
    }

    uint8_t led_on_l = (uint8_t)(rising_edge & 0xFF);
    uint8_t led_on_h = (uint8_t)((rising_edge >> 8U) & 0xF);
    uint8_t led_off_l = (uint8_t)(falling_edge & 0xFF);
    uint8_t led_off_h = (uint8_t)((falling_edge >> 8U) & 0xF);

    if (duty_cycle == 1)
    {
        led_on_h = 0x1F;
        led_off_h = 0x0;
    }

    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr_write = handler->device_address & ~(0x1);

    const uint8_t led_on_l_addr = LED_ADDR(LED_ON_L_BASEADDR, (uint8_t)channel);
    const uint8_t led_on_h_addr = LED_ADDR(LED_ON_H_BASEADDR, (uint8_t)channel);
    const uint8_t led_off_l_addr = LED_ADDR(LED_OFF_L_BASEADDR, (uint8_t)channel);
    const uint8_t led_off_h_addr = LED_ADDR(LED_OFF_H_BASEADDR, (uint8_t)channel);

    // TODO: change to burst transfer to avoid writing multiple times
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, led_on_l_addr, I2C_MEMADD_SIZE_8BIT, &led_on_l,
                      sizeof(led_on_l), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, led_on_h_addr, I2C_MEMADD_SIZE_8BIT, &led_on_h,
                      sizeof(led_on_h), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, led_off_l_addr, I2C_MEMADD_SIZE_8BIT, &led_off_l,
                      sizeof(led_off_l), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, led_off_h_addr, I2C_MEMADD_SIZE_8BIT, &led_off_h,
                      sizeof(led_off_h), HAL_MAX_DELAY);

}

void pwm_driver_update_all_patterns(pwm_driver_handler_S* handler, float duty_cycle, float phase_shift)
{
    if (duty_cycle < 0)
    {
        duty_cycle = 0;
    }
    if (phase_shift < 0)
    {
        phase_shift = 0;
    }

    if (duty_cycle > 1)
    {
        duty_cycle = 1;
    }
    if (phase_shift > 1)
    {
        phase_shift = 0;
    }

    for (pwm_channel_E i = (pwm_channel_E)0U; i < NUM_OF_PWM_CHANNELS; i++)
    {
        handler->duty_cycle[i] = duty_cycle; 
        handler->phase_shift[i] = phase_shift;
    }

    // PWM count registers are 12bits, period is 4096 counts
    const uint16_t phase_counts = (uint16_t)((1U << 12U) * phase_shift);
    const uint16_t duty_counts = (uint16_t)((1U << 12U) * duty_cycle);
    
    uint16_t rising_edge = phase_counts;
    uint16_t falling_edge = phase_counts + duty_counts;

    if (falling_edge > (1U << 12U))
    {
        falling_edge -= (1U << 12U);
    }

    uint8_t led_on_l = (uint8_t)(rising_edge & 0xFF);
    uint8_t led_on_h = (uint8_t)((rising_edge >> 8U) & 0xF);
    uint8_t led_off_l = (uint8_t)(falling_edge & 0xFF);
    uint8_t led_off_h = (uint8_t)((falling_edge >> 8U) & 0xF);

    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr_write = handler->device_address & ~(0x1);

    // TODO: change to burst transfer to avoid writing multiple times
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, ALL_LED_ON_L_ADDR, I2C_MEMADD_SIZE_8BIT, &led_on_l,
                      sizeof(led_on_l), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, ALL_LED_ON_H_ADDR, I2C_MEMADD_SIZE_8BIT, &led_on_h,
                      sizeof(led_on_h), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, ALL_LED_OFF_L_ADDR, I2C_MEMADD_SIZE_8BIT, &led_off_l,
                      sizeof(led_off_l), HAL_MAX_DELAY);
    HAL_I2C_Mem_Write(i2c_handler, device_addr_write, ALL_LED_OFF_H_ADDR, I2C_MEMADD_SIZE_8BIT, &led_off_h,
                      sizeof(led_off_h), HAL_MAX_DELAY);
}

#if DEBUG_PWM_DRIVER
void pwm_driver_debug_write_address(pwm_driver_handler_S* handler, uint8_t reg_addr, uint8_t data_to_write)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr = handler->device_address & ~(0x1);

    HAL_I2C_Mem_Write(i2c_handler, device_addr, reg_addr, I2C_MEMADD_SIZE_8BIT, &data_to_write, sizeof(uint8_t), HAL_MAX_DELAY);
}

uint8_t pwm_driver_debug_read_address(pwm_driver_handler_S* handler, uint8_t reg_addr)
{
    I2C_HandleTypeDef *i2c_handler = handler->i2c_handler;
    const uint8_t device_addr = handler->device_address;

    uint8_t data = 0;
    HAL_I2C_Mem_Read(i2c_handler, device_addr, reg_addr, I2C_MEMADD_SIZE_8BIT, &data, sizeof(uint8_t), HAL_MAX_DELAY);

    return data;
}
#endif // DEBUG_PWM_DRIVER