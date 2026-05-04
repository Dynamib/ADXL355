#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include "wifi_config.h"
#include "adxl355_sensor.h"
#include "microros_node.h"

static void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    digitalWrite(LED_PIN, (millis() / 300) % 2 ? HIGH : LOW);
    if (millis() - start > 30000) {
      Serial.println("\nWiFi timeout, restarting...");
      ESP.restart();
    }
    delay(500);
  }
  Serial.println();
  Serial.print("WiFi connected. IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== ESP32 + ADXL355 micro-ROS Node ===");
  Serial.printf("Publish rate: %d Hz | Agent: %s:%d\n",
                PUBLISH_RATE_HZ, MICRO_ROS_AGENT_IP, MICRO_ROS_AGENT_PORT);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  setupWiFi();

  if (!initSensor(SPI, CS_PIN, DRDY_PIN, SENSOR_ODR, SENSOR_RANGE)) {
    Serial.println("ADXL355 init failed!");
    while (1) {
      digitalWrite(LED_PIN, HIGH);
      delay(200);
      digitalWrite(LED_PIN, LOW);
      delay(200);
    }
  }
  Serial.println("ADXL355 sensor initialized (500 Hz ODR, ±2g)");

  microros_connected = initMicroROS();
  if (microros_connected) {
    Serial.println("micro-ROS node initialized");
  } else {
    Serial.println("micro-ROS init failed — will retry in spin task");
  }

  xTaskCreatePinnedToCore(taskSensorRead, "SensorRead",
                          4096, NULL, 10, NULL, 0);
  xTaskCreatePinnedToCore(taskMicroROSSpin, "MicrorosSpin",
                          8192, NULL, 8, NULL, 1);

  Serial.println("FreeRTOS tasks created. System running.");
}

void loop() {
  // Everything is handled by FreeRTOS tasks.
  // Periodic status output on serial.
  static unsigned long lastStatus = 0;
  if (millis() - lastStatus > 10000) {
    lastStatus = millis();
    UBaseType_t waiting = uxQueueMessagesWaiting(sensorQueue);
    Serial.printf("[STATUS] WiFi: %s | Agent: %s | Queue: %u/%d\n",
                  WiFi.status() == WL_CONNECTED ? "OK" : "DOWN",
                  microros_connected ? "OK" : "DOWN",
                  (unsigned)waiting, QUEUE_SIZE);
  }
  vTaskDelay(pdMS_TO_TICKS(1000));
}
