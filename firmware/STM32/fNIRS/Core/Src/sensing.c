/* INCLUDES */
#include "sensing.h"
#include "mux_control.h"
#include "emitter_control.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"

/* DEFINES */

/* DATA STRUCTURES */

// Hardware mapping
// sensor group 1: adc1 or adc2, channel 15
// sensor group 2: adc1 or adc2, channel 14
// sensor group 3: adc1 or adc2, channel 13
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
	.adc_conversion_completed_counter = 0U,
};

/* FUNCTION DEFINITIONS */

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

uint8_t sensing_get_adc_conversion_complete(void)
{
    return sense_vars.adc_conversion_completed_counter;
}

void sensing_reset_adc_conversion_complete(void)
{
    sense_vars.adc_conversion_completed_counter = 0U;
}

void sensing_update_all_sensor_channels(void)
{
	const mux_input_channel_E curr_channel = mux_control_get_curr_input_channel();
	for (sensor_module_E i = (sensor_module_E)0U; i < NUM_OF_SENSOR_MODULES; i+=2)
	{
		uint8_t dma_index = i >> 1;
		uint16_t raw_adc_value_even = (uint16_t)(sense_vars.sensor_raw_value_dma[dma_index] & 0xffff);
		uint16_t raw_adc_value_odd = (uint16_t)(sense_vars.sensor_raw_value_dma[dma_index] >> 16);
		sense_vars.sensor_calibrated_value[i][curr_channel] = sense_vars.sensor_scale[i] * raw_adc_value_even + sense_vars.sensor_offset[i];
		sense_vars.sensor_calibrated_value[i+1][curr_channel] = sense_vars.sensor_scale[i+1] * raw_adc_value_odd + sense_vars.sensor_offset[i+1];
	}
}

void sensing_update_single_channel(void)
{
	static uint16_t data_buffer[1000] = { 0 };
	static uint16_t i = 0;

	data_buffer[i++] = (uint16_t)((sense_vars.sensor_raw_value_dma[1] >> 16) & 0xffff);

	if (i > 999 && i < 1200)
	{
		uint8_t buffer_to_send[2000] = { 0 };
		for (int j = 0; j < 1000; j++)
		{
			buffer_to_send[j*2] = data_buffer[j] & 0xff;
			buffer_to_send[j*2+1] = (data_buffer[j] >> 8) & 0xff;
		}
		CDC_Transmit_FS(buffer_to_send, sizeof(buffer_to_send));
		i = 1500;
	}
	else if (i > 999)
	{
		i = 1500;
	}
}

// ISR function - called every 5kHz
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc)
{
    sense_vars.adc_conversion_completed_counter++;
//    sensing_update_all_sensor_channels();
    sensing_update_single_channel();
}


