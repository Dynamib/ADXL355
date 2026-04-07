#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <PL_ADXL355.h>
#include <PubSubClient.h>
#include <HTTPUpdate.h>

// ================= 配置区 =================
const char *ssid = "Zhouai1001";
const char *password = "12345678";
const char *mqtt_server = "8.148.71.98";
const int mqtt_port = 1883;

const char *topic_data = "lab/vibration"; // 数据Topic
const char *topic_cmd  = "lab/vibration/cmd";

#define CHIP_SELECT_PIN 5
#define DRDY_PIN        4

PL::ADXL355 adxl;
WiFiClient espClient;
PubSubClient client(espClient);

// === 核心数据结构 (二进制包) ===
// 一个点 16 字节
struct __attribute__((packed)) VibrationData {
  float x; float y; float z; float v;
};

// 队列句柄
QueueHandle_t sensorQueue;
volatile bool isSampling = true; 

// === 一次发 250 个点 (4KB) ===
// 4000Hz 下，250个点 = 62.5ms 的数据量，每秒发 16 次包
const int BATCH_COUNT = 250; 
VibrationData batchBuffer[BATCH_COUNT]; // 直接用结构体数组
int bufferIndex = 0; 

// ================= 函数声明 =================
void setup_wifi();
void reconnect();
void mqtt_callback(char* topic, byte* payload, unsigned int length);
void TaskReadSensor(void *pvParameters); 

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== ESP32 Ultimate Binary Mode (4000Hz) ===");

  SPI.begin(18, 19, 23, CHIP_SELECT_PIN);
  pinMode(DRDY_PIN, INPUT);
  adxl.beginSPI(CHIP_SELECT_PIN);
  adxl.setRange(PL::ADXL355_Range::range2g);
  
  // *** 满血全开：4000Hz ***
  adxl.setOutputDataRate(PL::ADXL355_OutputDataRate::odr4000);
  adxl.enableMeasurement();

  // 队列稍微大一点
  sensorQueue = xQueueCreate(4000, sizeof(VibrationData));

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqtt_callback);
  
  // 发送缓存设为 5KB (250个点 * 16字节 = 4000字节)
  client.setBufferSize(5120); 

  xTaskCreatePinnedToCore(TaskReadSensor, "SensorRead", 4096, NULL, 10, NULL, 0);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  VibrationData data;
  static unsigned long lastTime = 0;
  static int packetCount = 0;
  static int totalPoints = 0;

  int processLimit = 0;
  // 每次最多处理 20 个包 (20 * 250 = 5000点)，防止看门狗咬人
  while (processLimit < 20 && xQueueReceive(sensorQueue, &data, 0) == pdTRUE) {
    
    // 直接存入结构体数组
    batchBuffer[bufferIndex++] = data;

    // 攒够了 250 个点 (4000字节)
    if (bufferIndex >= BATCH_COUNT) {
      // *** 核心：直接发送内存二进制数据 ***
      // (uint8_t*)batchBuffer 强制转换为字节流
      // sizeof(batchBuffer) = 4000
      client.publish(topic_data, (uint8_t*)batchBuffer, sizeof(batchBuffer));
      
      packetCount++;
      totalPoints += BATCH_COUNT;
      bufferIndex = 0;
      processLimit++;
    }
  }

  // 监控 FPS
  if (millis() - lastTime > 1000) {
    long elapsed = millis() - lastTime;
    lastTime = millis();
    int waiting = uxQueueMessagesWaiting(sensorQueue);
    float realFps = (float)totalPoints * 1000.0 / elapsed;
    
    Serial.printf("[BINARY MODE] FPS: %.2f Hz | Queue: %d/4000\n", realFps, waiting);
    totalPoints = 0; 
  }
}

// === 读取任务 (最简) ===
void TaskReadSensor(void *pvParameters) {
  int loopCounter = 0;
  for (;;) {
    if (isSampling && digitalRead(DRDY_PIN) == HIGH) {
      auto acc = adxl.getAccelerations();
      VibrationData d;
      d.x = acc.x; d.y = acc.y; d.z = acc.z;
      d.v = sqrt(acc.x*acc.x + acc.y*acc.y + acc.z*acc.z);
      xQueueSend(sensorQueue, &d, 0);

      loopCounter++;
      if (loopCounter >= 200) { // 稍微休息一下
        loopCounter = 0;
        vTaskDelay(1); 
      }
    } else {
      taskYIELD(); 
    }
  }
}

// 辅助函数 (保持精简)
void mqtt_callback(char* topic, byte* payload, unsigned int length) {}
void setup_wifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
}
void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32-Binary")) client.subscribe(topic_cmd);
    else delay(2000);
  }
}