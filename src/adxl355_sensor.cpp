#include "adxl355_sensor.h"
#include "wifi_config.h"

static PL::ADXL355 adxl;

QueueHandle_t sensorQueue = nullptr;
volatile bool isSampling = true;

bool initSensor(SPIClass &spi, int csPin, int drdyPin,
                PL::ADXL355_OutputDataRate odr, PL::ADXL355_Range range) {
  pinMode(drdyPin, INPUT);

  adxl.beginSPI(csPin);
  adxl.setRange(range);
  adxl.setOutputDataRate(odr);
  adxl.enableMeasurement();

  // Route DATA_RDY to INT1 pin (INT_MAP register defaults to 0x00)
  adxl.enableDataReady();
  adxl.setInterrupts(PL::ADXL355_Interrupts::dataReadyInt1);

  // Verify SPI communication by reading device ID
  auto info = adxl.getDeviceInfo();
  if (info.vendorId != 0xAD || info.deviceId != 0xED) {
    Serial.printf("ADXL355 ID mismatch: vendor=0x%02X device=0x%02X\n",
                  info.vendorId, info.deviceId);
    return false;
  }
  Serial.printf("ADXL355 device verified (vendor=0x%02X device=0x%02X)\n",
                info.vendorId, info.deviceId);

  sensorQueue = xQueueCreate(QUEUE_SIZE, sizeof(VibrationData));
  if (sensorQueue == nullptr) {
    return false;
  }
  return true;
}

void taskSensorRead(void *pvParameters) {
  int loopCounter = 0;

  for (;;) {
    if (isSampling && digitalRead(DRDY_PIN) == HIGH) {
      auto acc = adxl.getAccelerations();
      VibrationData d;
      d.x = acc.x;
      d.y = acc.y;
      d.z = acc.z;
      d.v = sqrtf(acc.x * acc.x + acc.y * acc.y + acc.z * acc.z);
      xQueueSend(sensorQueue, &d, 0);

      loopCounter++;
      if (loopCounter >= 100) {
        loopCounter = 0;
        vTaskDelay(1);
      }
    } else {
      taskYIELD();
    }
  }
}
