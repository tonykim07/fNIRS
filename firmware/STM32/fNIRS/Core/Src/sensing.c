/* INCLUDES */
#include "sensing.h"
#include "mux_control.h"
#include "emitter_control.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"

/* DEFINES */

#define LPF_ALPHA (0.6)

/* DATA STRUCTURES */

// Hardware mapping
// sensor group 1: adc1 or adc2, channel 15
// sensor group 2: adc1 or adc2, channel 14
// sensor group 3: adc1 or adc2, channel 13s
// sensor group 4: adc1 or adc2, channel 12
// sensor group 5: adc1, adc2, or adc3, channel 4
// sensor group 6: adc1, adc2, or adc3, channel 3
// sensor group 7: adc1, adc2, or adc3, channel 1
// sensor group 8: adc1, adc2, or adc3, channel 2

static fnirs_sense_vars_S sense_vars = { 
    .adc_handler = { NULL },
    .sensor_scale = { 
        [SENSOR_MODULE_1] = 1U,
        [SENSOR_MODULE_2] = 1U,
        [SENSOR_MODULE_3] = 1U,
        [SENSOR_MODULE_4] = 1U,
        [SENSOR_MODULE_5] = 1U,
        [SENSOR_MODULE_6] = 1U,
        [SENSOR_MODULE_7] = 1U,
        [SENSOR_MODULE_8] = 1U
    },
    .sensor_offset = { 0 },
    .sensor_raw_value = { { 0 } },
    .sensor_calibrated_value = { { 0 } },
    .temp_sensor_raw_adc_value = { 0 },
    .temperature = { 0 },
};

/* FUNCTION DEFINITIONS */

static inline uint16_t sensing_low_pass_filter(uint16_t input, uint16_t previous_output) 
{
    return (uint16_t)(LPF_ALPHA * input + (1.0 - LPF_ALPHA) * previous_output);
}

void sensing_init(ADC_HandleTypeDef *hadc)
{
    sense_vars.adc_handler[ADC_1] = hadc;
    HAL_ADCEx_Calibration_Start(hadc, ADC_SINGLE_ENDED);
    HAL_Delay(10);
    HAL_ADC_Start_DMA(hadc, sense_vars.sensor_raw_value_dma, NUM_OF_SENSOR_MODULES);
}

uint16_t sensing_get_sensor_calibrated_value(sensor_module_E sensor_module, mux_input_channel_E detector)
{
    return sense_vars.sensor_calibrated_value[sensor_module][detector];
}

float sensing_get_temperature_reading(temp_sensor_E sensor)
{
    return sense_vars.temperature[sensor];
}

void sensing_update_all_temperature_readings(void)
{
    
}

void sensing_update_all_sensor_channels(void)
{
	const mux_input_channel_E curr_channel = mux_control_get_curr_input_channel();
	for (sensor_module_E i = (sensor_module_E)0U; i < NUM_OF_SENSOR_MODULES; i+=2)
	{
		uint8_t dma_index = i >> 1;
		uint16_t raw_adc_value_even = (uint16_t)(sense_vars.sensor_raw_value_dma[dma_index] & 0xffff);
		uint16_t raw_adc_value_odd = (uint16_t)(sense_vars.sensor_raw_value_dma[dma_index] >> 16);
		sense_vars.sensor_calibrated_value[i][curr_channel] = sensing_low_pass_filter(raw_adc_value_even, sense_vars.sensor_calibrated_value[i][curr_channel]);
		sense_vars.sensor_calibrated_value[i+1][curr_channel] = sensing_low_pass_filter(raw_adc_value_odd, sense_vars.sensor_calibrated_value[i+1][curr_channel]);
	}
}

