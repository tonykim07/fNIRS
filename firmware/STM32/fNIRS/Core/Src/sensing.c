
/* INCLUDES */
#include "sensing.h"
#include "mux_control.h"

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
    .adc_handler_mapping = { 
        [SENSOR_MODULE_1] = ADC_1,
        [SENSOR_MODULE_2] = ADC_1,
        [SENSOR_MODULE_3] = ADC_1,
        [SENSOR_MODULE_4] = ADC_2,
        [SENSOR_MODULE_5] = ADC_2,
        [SENSOR_MODULE_6] = ADC_2,
        [SENSOR_MODULE_7] = ADC_3,
        [SENSOR_MODULE_8] = ADC_3,
    },
    .adc_channel_config = { 
        [SENSOR_MODULE_1] = { 
            .Channel = ADC_CHANNEL_15, 
            .Rank = ADC_REGULAR_RANK_1, 
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5, 
            .SingleDiff = ADC_SINGLE_ENDED, 
            .OffsetNumber = ADC_OFFSET_NONE, 
            .Offset = 0
        },
        [SENSOR_MODULE_2] = {
            .Channel = ADC_CHANNEL_14,
            .Rank = ADC_REGULAR_RANK_1,
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5,
            .SingleDiff = ADC_SINGLE_ENDED,
            .OffsetNumber = ADC_OFFSET_NONE,
            .Offset = 0
        },
        [SENSOR_MODULE_3] = {
            .Channel = ADC_CHANNEL_13,
            .Rank = ADC_REGULAR_RANK_1,
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5,
            .SingleDiff = ADC_SINGLE_ENDED,
            .OffsetNumber = ADC_OFFSET_NONE,
            .Offset = 0
        },
        [SENSOR_MODULE_4] = {
            .Channel = ADC_CHANNEL_12,
            .Rank = ADC_REGULAR_RANK_1,
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5,
            .SingleDiff = ADC_SINGLE_ENDED,
            .OffsetNumber = ADC_OFFSET_NONE,
            .Offset = 0
        },
        [SENSOR_MODULE_5] = {
            .Channel = ADC_CHANNEL_4,
            .Rank = ADC_REGULAR_RANK_1,
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5,
            .SingleDiff = ADC_SINGLE_ENDED,
            .OffsetNumber = ADC_OFFSET_NONE,
            .Offset = 0
        },
        [SENSOR_MODULE_6] = {
            .Channel = ADC_CHANNEL_3,
            .Rank = ADC_REGULAR_RANK_1,
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5,
            .SingleDiff = ADC_SINGLE_ENDED,
            .OffsetNumber = ADC_OFFSET_NONE,
            .Offset = 0
        },
        [SENSOR_MODULE_7] = 
        {
            .Channel = ADC_CHANNEL_1,
            .Rank = ADC_REGULAR_RANK_1,
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5,
            .SingleDiff = ADC_SINGLE_ENDED,
            .OffsetNumber = ADC_OFFSET_NONE,
            .Offset = 0
        },
        [SENSOR_MODULE_8] = {
            .Channel = ADC_CHANNEL_2,
            .Rank = ADC_REGULAR_RANK_1,
            .SamplingTime = ADC_SAMPLETIME_2CYCLES_5,
            .SingleDiff = ADC_SINGLE_ENDED,
            .OffsetNumber = ADC_OFFSET_NONE,
            .Offset = 0
        }
    },
    .sensor_scale = { 
        [SENSOR_MODULE_1] = 1.0,
        [SENSOR_MODULE_2] = 1.0,
        [SENSOR_MODULE_3] = 1.0,
        [SENSOR_MODULE_4] = 1.0,
        [SENSOR_MODULE_5] = 1.0,
        [SENSOR_MODULE_6] = 1.0,
        [SENSOR_MODULE_7] = 1.0,
        [SENSOR_MODULE_8] = 1.0
    },
    .sensor_offset = { 0 },
    .sensor_raw_value = { { 0 } },
    .sensor_calibrated_value = { { 0 } },
    .temp_sensor_raw_adc_value = { 0 },
    .temperature = { 0 },
};

/* FUNCTION DEFINITIONS */

void sensing_init(ADC_HandleTypeDef *hadc1, ADC_HandleTypeDef *hadc2, ADC_HandleTypeDef *hadc3)
{
    sense_vars.adc_handler[ADC_1] = hadc1;
    sense_vars.adc_handler[ADC_2] = hadc2;
    sense_vars.adc_handler[ADC_3] = hadc3;
}

float sensing_get_sensor_calibrated_value(sensor_module_E sensor_module, mux_input_channel_E detector)
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
    // TODO: optimize this function
    mux_input_channel_E curr_channel = mux_control_get_curr_input_channel();

    for (sensor_module_E i = (sensor_module_E)0; i < NUM_OF_SENSOR_MODULES; i++)
    {
        float raw_adc_value = 0.0;
        ADC_HandleTypeDef *adc_handler = sense_vars.adc_handler[sense_vars.adc_handler_mapping[i]];

        HAL_ADC_ConfigChannel(adc_handler, &sense_vars.adc_channel_config[i]);
        HAL_ADC_Start(adc_handler);
        HAL_ADC_PollForConversion(adc_handler, HAL_MAX_DELAY);
        raw_adc_value = HAL_ADC_GetValue(adc_handler);
        sense_vars.sensor_raw_value[i][curr_channel] = raw_adc_value;
        sense_vars.sensor_calibrated_value[i][curr_channel] = sense_vars.sensor_scale[i] * raw_adc_value + sense_vars.sensor_offset[i];
    }
}

