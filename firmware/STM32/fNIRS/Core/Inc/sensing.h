
#ifndef INC_SENSING_H_
#define INC_SENSING_H_

/* INCLUDES */
#include "main.h"
#include "mux_control.h"

/* DEFINES */


/* DATA STRUCTURES */
typedef enum
{
    ADC_1,
    // ADC_2, 
    // ADC_3,

    NUM_OF_ADC_MODULES,
} adc_E;

typedef enum 
{
    SENSOR_MODULE_1 = 0U, 
    SENSOR_MODULE_2, 
    SENSOR_MODULE_3, 
    SENSOR_MODULE_4,
    SENSOR_MODULE_5,
    SENSOR_MODULE_6,
    SENSOR_MODULE_7,
    SENSOR_MODULE_8, 

    NUM_OF_SENSOR_MODULES,
} sensor_module_E;

typedef enum
{
    // TODO: rename temperature sensor names to be more readable (i.e. location on board)
    TEMPSENSE_ONE, 
    TEMPSENSE_TWO, 
    TEMPSENSE_THREE, 

    NUM_OF_TEMPSENSORS,
} temp_sensor_E;

typedef struct
{
    ADC_HandleTypeDef *adc_handler[NUM_OF_ADC_MODULES];
    
    // DMA flag and buffer
    uint32_t sensor_raw_value_dma[NUM_OF_SENSOR_MODULES];
    
    uint16_t sensor_raw_value[NUM_OF_SENSOR_MODULES][NUM_OF_INPUT_CHANNELS];
    uint16_t sensor_calibrated_value[NUM_OF_SENSOR_MODULES][NUM_OF_INPUT_CHANNELS];
    uint16_t sensor_scale[NUM_OF_SENSOR_MODULES];
    uint16_t sensor_offset[NUM_OF_SENSOR_MODULES];

    uint16_t temp_sensor_raw_adc_value[NUM_OF_TEMPSENSORS];
    float temperature[NUM_OF_TEMPSENSORS];

} fnirs_sense_vars_S;

/* FUNCTION DECLARATIONS */
void sensing_init(ADC_HandleTypeDef *hadc);
uint16_t sensing_get_sensor_calibrated_value(sensor_module_E sensor_module, mux_input_channel_E detector);
float sensing_get_temperature_reading(temp_sensor_E sensor);
void sensing_update_all_temperature_readings(void);
void sensing_update_all_sensor_channels(void);

#endif /* INC_SENSING_H_ */
