/* INCLUDES */
#include "sensing.h"
#include "mux_control.h"
#include "emitter_control.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"

/* DEFINES */
// #define USB_BUFFER_SIZE 10
#define NUM_OF_EMITTERS 16

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
    .sampling_timer = 0,
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

void sendUSB_sensor_emitter_data(SensorEmitterData *sensor_data)
{

    // char uart_buffer[25];  // Buffer for formatted UART transmission
    // int offset = 0;
    // Debug print before USB transmission
    // for (int i = 0; i < NUM_OF_SENSOR_MODULES; i++)
    // {
    //     printf("Sensor %d: Value = %.2f, Emitter = %d\n",
    //         i + 1, sensor_data[i].sensor_value, sensor_data[i].emitter_status);
    // }

    // Transmit data via USB CDC
    // uint8_t usb_data[] = "Hello World from USB CDC\n";
    // CDC_Transmit_FS(usb_data, sizeof(usb_data) - 1);

    CDC_Transmit_FS((uint8_t*)sensor_data, sizeof(SensorEmitterData) * NUM_OF_SENSOR_MODULES);
    HAL_Delay(10);
}

void sensing_update_all_sensor_channels(void)
{
    // TODO: optimize this function
    if (sense_vars.sampling_timer > 10)
    {
        mux_input_channel_E curr_channel = mux_control_get_curr_input_channel();

        for (sensor_module_E i = (sensor_module_E)0; i < NUM_OF_SENSOR_MODULES; i++)
        {
        	uint16_t raw_adc_value;
        	ADC_HandleTypeDef *adc_handler = sense_vars.adc_handler[sense_vars.adc_handler_mapping[i]];

            HAL_ADC_ConfigChannel(adc_handler, &sense_vars.adc_channel_config[i]);
            HAL_ADC_Start(adc_handler);
            HAL_ADC_PollForConversion(adc_handler, HAL_MAX_DELAY);
            raw_adc_value = HAL_ADC_GetValue(adc_handler);
            sense_vars.sensor_raw_value[i][curr_channel] = raw_adc_value;
            sense_vars.sensor_calibrated_value[i][curr_channel] = sense_vars.sensor_scale[i] * raw_adc_value + sense_vars.sensor_offset[i];
        }
        sense_vars.sampling_timer = 0U;
    }
    else
    {
        sense_vars.sampling_timer++;
    }
}

void send_single_raw_sensor_valueUSB(void)
{
    sensor_module_E sensor_module = SENSOR_MODULE_1;  // Default to first sensor (change if needed)

    // Zero-initialize the buffer
    uint8_t usb_buffer[2];

    uint16_t raw_adc_value;
    raw_adc_value = sensing_get_sensor_calibrated_value(sensor_module, MUX_INPUT_CHANNEL_ONE);

    // Extract the lower and upper bytes from the uint16_t value
    uint8_t lower_byte = (uint8_t)(raw_adc_value & 0xFF);        // Extract LSB (Lower byte)
    uint8_t upper_byte = (uint8_t)((raw_adc_value >> 8) & 0xFF); // Extract MSB (Higher byte)


    // Store the lower and upper bytes in the buffer
    usb_buffer[1] = lower_byte;  // LSB in the first byte
    usb_buffer[0] = upper_byte;  // MSB in the second byte

    // Transmit both bytes at once
    CDC_Transmit_FS(usb_buffer, sizeof(usb_buffer));  // Send 2 bytes (LSB and MSB)

    HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly

    // Send additional message, e.g., "S1" for "Sensor 1"
    uint8_t data1[] = "S1";
    CDC_Transmit_FS(data1, sizeof(data1) - 1);  // Send the string "S1" (excluding null terminator)
    HAL_Delay(20);
}

void send_uint16_over_usb(uint16_t value)
{
    // Initialize a buffer of 2 bytes to hold the LSB and MSB
    uint8_t usb_buffer[2] = {0};

    // Extract the lower and upper bytes from the uint16_t value
    uint8_t lower_byte = (uint8_t)(value & 0xFF);        // Extract LSB (Lower byte)
    uint8_t upper_byte = (uint8_t)((value >> 8) & 0xFF); // Extract MSB (Higher byte)

    // Store the bytes into the buffer
    usb_buffer[0] = lower_byte;  // LSB in the first byte
    usb_buffer[1] = upper_byte;  // MSB in the second byte

    // Transmit both bytes together
    CDC_Transmit_FS(usb_buffer, sizeof(usb_buffer));

    // Small delay to allow transmission to complete
    HAL_Delay(10);  // Adjust as needed
}

void send_all_sensor_valuesUSB(void)
{

	sensor_module_E sensor_module1 = SENSOR_MODULE_1;  // Default to first sensor (change if needed)

	//group 1

	uint8_t g1[] = "G1";
	CDC_Transmit_FS(g1, sizeof(g1) - 1);  // Send the string "Group1"
	HAL_Delay(10);

	uint8_t usb_buffer11[2], usb_buffer12[2], usb_buffer13[2];
	uint16_t raw_adc_value_sensor11 = sensing_get_sensor_calibrated_value(sensor_module1, MUX_INPUT_CHANNEL_ONE);
	HAL_Delay(10);

	// Process sensor 1
	usb_buffer11[1] = (uint8_t)(raw_adc_value_sensor11 & 0xFF);  // Store LSB in the first byte
	usb_buffer11[0] = (uint8_t)(raw_adc_value_sensor11 >> 8);   // Store MSB in the second byte
	CDC_Transmit_FS(usb_buffer11, sizeof(usb_buffer11));  // Send both bytes at once
	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly

	uint8_t data11[] = "S1";
	CDC_Transmit_FS(data11, sizeof(data11) - 1);  // Send the string "Sensor 1 sent\n"
	HAL_Delay(10);

	// Process sensor 2
	uint16_t raw_adc_value_sensor12 = sensing_get_sensor_calibrated_value(sensor_module1, MUX_INPUT_CHANNEL_TWO);
	usb_buffer12[1] = (uint8_t)(raw_adc_value_sensor12 & 0xFF);  // Store LSB in the first byte
	usb_buffer12[0] = (uint8_t)(raw_adc_value_sensor12 >> 8);   // Store MSB in the second byte
	CDC_Transmit_FS(usb_buffer12, sizeof(usb_buffer12));  // Send both bytes at once
	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly

	uint8_t data12[] = "S2";
	CDC_Transmit_FS(data12, sizeof(data12) - 1);  // Send the string "Sensor 2 sent\n"
	HAL_Delay(10);

	// Process sensor 3
	uint16_t raw_adc_value_sensor13 = sensing_get_sensor_calibrated_value(sensor_module1, MUX_INPUT_CHANNEL_THREE);
	usb_buffer13[1] = (uint8_t)(raw_adc_value_sensor13 & 0xFF);  // Store LSB in the first byte
	usb_buffer13[0] = (uint8_t)(raw_adc_value_sensor13 >> 8);   // Store MSB in the second byte
	CDC_Transmit_FS(usb_buffer13, sizeof(usb_buffer13));  // Send both bytes at once
	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly

	uint8_t data13[] = "S3";
	CDC_Transmit_FS(data13, sizeof(data13) - 1);  // Send the string "Sensor 3 sent\n"
	HAL_Delay(10);

//	// group 2
//	sensor_module_E sensor_module2 = SENSOR_MODULE_2;  // Default to first sensor (change if needed)
//
//	uint8_t g2[] = "G2";
//	CDC_Transmit_FS(g2, sizeof(g2) - 1);  // Send the string "Group1"
//	HAL_Delay(10);
//	uint8_t usb_buffer21[2], usb_buffer22[2], usb_buffer23[2];
//	uint16_t raw_adc_value_sensor21 = sensing_get_sensor_calibrated_value(sensor_module2, MUX_INPUT_CHANNEL_ONE);
//	HAL_Delay(10);
//
//	// Process sensor 1
//	usb_buffer21[1] = (uint8_t)(raw_adc_value_sensor21 & 0xFF);  // Store LSB in the first byte
//	usb_buffer21[0] = (uint8_t)(raw_adc_value_sensor21 >> 8);   // Store MSB in the second byte
//	CDC_Transmit_FS(usb_buffer21, sizeof(usb_buffer21));  // Send both bytes at once
//	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly
//
//	uint8_t data21[] = "S1";
//	CDC_Transmit_FS(data21, sizeof(data21) - 1);  // Send the string "Sensor 1 sent\n"
//	HAL_Delay(10);
//
//	// Process sensor 2
//	uint16_t raw_adc_value_sensor22 = sensing_get_sensor_calibrated_value(sensor_module2, MUX_INPUT_CHANNEL_TWO);
//	usb_buffer22[1] = (uint8_t)(raw_adc_value_sensor22 & 0xFF);  // Store LSB in the first byte
//	usb_buffer22[0] = (uint8_t)(raw_adc_value_sensor22 >> 8);   // Store MSB in the second byte
//	CDC_Transmit_FS(usb_buffer22, sizeof(usb_buffer22));  // Send both bytes at once
//	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly
//
//	uint8_t data22[] = "S2";
//	CDC_Transmit_FS(data22, sizeof(data22) - 1);  // Send the string "Sensor 2 sent\n"
//	HAL_Delay(10);
//
//	// Process sensor 3
//	uint16_t raw_adc_value_sensor23 = sensing_get_sensor_calibrated_value(sensor_module2, MUX_INPUT_CHANNEL_THREE);
//	usb_buffer23[1] = (uint8_t)(raw_adc_value_sensor23 & 0xFF);  // Store LSB in the first byte
//	usb_buffer23[0] = (uint8_t)(raw_adc_value_sensor23 >> 8);   // Store MSB in the second byte
//	CDC_Transmit_FS(usb_buffer23, sizeof(usb_buffer23));  // Send both bytes at once
//	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly
//
//	uint8_t data23[] = "S3";
//	CDC_Transmit_FS(data23, sizeof(data23) - 1);  // Send the string "Sensor 3 sent\n"
//	HAL_Delay(10);
//
//	// group 3
//	sensor_module_E sensor_module3 = SENSOR_MODULE_3;  // Default to first sensor (change if needed)
//
//	uint8_t g3[] = "G3";
//	CDC_Transmit_FS(g3, sizeof(g3) - 1);  // Send the string "Group1"
//	HAL_Delay(10);
//	uint8_t usb_buffer31[2], usb_buffer32[2], usb_buffer33[2];
//	uint16_t raw_adc_value_sensor31 = sensing_get_sensor_calibrated_value(sensor_module3, MUX_INPUT_CHANNEL_ONE);
//	HAL_Delay(10);
//
//	// Process sensor 1
//	usb_buffer31[1] = (uint8_t)(raw_adc_value_sensor31 & 0xFF);  // Store LSB in the first byte
//	usb_buffer31[0] = (uint8_t)(raw_adc_value_sensor31 >> 8);   // Store MSB in the second byte
//	CDC_Transmit_FS(usb_buffer31, sizeof(usb_buffer31));  // Send both bytes at once
//	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly
//
//	uint8_t data31[] = "S1";
//	CDC_Transmit_FS(data31, sizeof(data31) - 1);  // Send the string "Sensor 1 sent\n"
//	HAL_Delay(10);
//
//	// Process sensor 2
//	uint16_t raw_adc_value_sensor32 = sensing_get_sensor_calibrated_value(sensor_module3, MUX_INPUT_CHANNEL_TWO);
//	usb_buffer32[1] = (uint8_t)(raw_adc_value_sensor32 & 0xFF);  // Store LSB in the first byte
//	usb_buffer32[0] = (uint8_t)(raw_adc_value_sensor32 >> 8);   // Store MSB in the second byte
//	CDC_Transmit_FS(usb_buffer32, sizeof(usb_buffer32));  // Send both bytes at once
//	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly
//
//	uint8_t data32[] = "S2";
//	CDC_Transmit_FS(data32, sizeof(data32) - 1);  // Send the string "Sensor 2 sent\n"
//	HAL_Delay(10);
//
//	// Process sensor 3
//	uint16_t raw_adc_value_sensor33 = sensing_get_sensor_calibrated_value(sensor_module3, MUX_INPUT_CHANNEL_THREE);
//	usb_buffer33[1] = (uint8_t)(raw_adc_value_sensor33 & 0xFF);  // Store LSB in the first byte
//	usb_buffer33[0] = (uint8_t)(raw_adc_value_sensor33 >> 8);   // Store MSB in the second byte
//	CDC_Transmit_FS(usb_buffer33, sizeof(usb_buffer33));  // Send both bytes at once
//	HAL_Delay(10);  // Small delay to ensure USB buffer processes correctly
//
//	uint8_t data33[] = "S3";
//	CDC_Transmit_FS(data33, sizeof(data33) - 1);  // Send the string "Sensor 3 sent\n"
//	HAL_Delay(10);

//	}
}


// example packet sent through usb would be: 
// group 1: [Sensor1_Value] [Sensor2_Value] [Sensor3_Value] [Group1_Emitter] [940/660nm/off]
// group 2: [Sensor1_Value] [Sensor2_Value] [Sensor3_Value] [Group2_Emitter] [940/660nm/off]
// ...
// group 8: [Sensor1_Value] [Sensor2_Value] [Sensor3_Value] [Group8_Emitter] [940/660nm/off]
