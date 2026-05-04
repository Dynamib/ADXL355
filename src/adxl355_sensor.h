#ifndef ADXL355_SENSOR_H
#define ADXL355_SENSOR_H

#include <Arduino.h>
#include <SPI.h>
#include <PL_ADXL355.h>

struct VibrationData {
  float x;
  float y;
  float z;
  float v;
};

extern QueueHandle_t sensorQueue;
extern volatile bool isSampling;

bool initSensor(SPIClass &spi, int csPin, int drdyPin,
                PL::ADXL355_OutputDataRate odr, PL::ADXL355_Range range);
void taskSensorRead(void *pvParameters);

#endif
