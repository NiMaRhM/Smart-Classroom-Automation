#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <DHT.h>
#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include "driver/i2s.h"

using namespace websockets;

#ifndef FP_PIN
#define FP_PIN 33
#endif
volatile bool fpFlag = false;

#define DHTPIN 27
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

#define TFT_CS   5
#define TFT_DC   21
#define TFT_RST  4
#define TFT_SCLK 18
#define TFT_MOSI 23

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST);

enum ScreenMode { SHOW_DHT, SHOW_FP };
ScreenMode screenMode = SHOW_DHT;

unsigned long fpUntilMs = 0;
const unsigned long FP_SHOW_TIME = 3000;

unsigned long lastDhtMs = 0;
const unsigned long DHT_PERIOD = 2000;

void printDHT(int x, int y, const char* label, float value, const char* unit) {
  tft.setCursor(x, y);
  tft.setTextSize(2);
  tft.setTextColor(ST77XX_WHITE);
  tft.print(label);

  tft.setTextSize(3);
  tft.setCursor(x, y + 25);
  tft.setTextColor(ST77XX_YELLOW);

  tft.fillRect(x, y + 25, 90, 28, ST77XX_BLACK);
  tft.fillRect(x + 90, y + 25, 30, 28, ST77XX_BLACK);

  if (isnan(value)) tft.print("--");
  else tft.print(value, 1);

  tft.setTextSize(2);
  tft.setTextColor(ST77XX_WHITE);
  tft.print(unit);
}

void IRAM_ATTR fpISR() {
  fpFlag = true;
}

void showDhtScreenBase() {
  tft.fillScreen(ST77XX_BLACK);
}

void setup_dht() {
  Serial.begin(115200);
  delay(200);

  dht.begin();

  tft.initR(INITR_BLACKTAB);
  tft.setRotation(1);
  tft.fillScreen(ST77XX_BLACK);

  pinMode(FP_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(FP_PIN), fpISR, FALLING);

  showDhtScreenBase();
}

void loop_dht() {
  unsigned long now = millis();

  if (screenMode == SHOW_FP) {
    if ((long)(now - fpUntilMs) >= 0) {
      screenMode = SHOW_DHT;
      showDhtScreenBase();
      lastDhtMs = 0;
    }
    return;
  }

  if (now - lastDhtMs >= DHT_PERIOD) {
    lastDhtMs = now;

    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (isnan(h) || isnan(t)) {
      Serial.println("Failed to read from DHT11!");
    } else {
      Serial.print("Temp: "); Serial.print(t); Serial.print(" C  ");
      Serial.print("Hum: "); Serial.print(h); Serial.println(" %");
    }

    printDHT(10, 0,  "Temp:", t, " C");
    printDHT(10, 65, "Hum:",  h, " %");
  }
}

const char* WIFI_SSID = "NiMaRhM Honor";
const char* WIFI_PASS = "nimarhm123";

const char* SERVER_IP = "10.91.52.239";

String WS_AUDIO_URL;
String WS_DEVICE_URL;

#define I2S_WS   25
#define I2S_SD   32
#define I2S_SCK  26

static const int SAMPLE_RATE = 16000;
static const int CHUNK_MS = 40;
static const int SAMPLES_PER_CHUNK = (SAMPLE_RATE * CHUNK_MS) / 1000;

static const int CHUNK_BYTES_IN  = SAMPLES_PER_CHUNK * 4;
static const int CHUNK_BYTES_OUT = SAMPLES_PER_CHUNK * 2;

static int32_t i2s_in[SAMPLES_PER_CHUNK];
static int16_t pcm16[SAMPLES_PER_CHUNK];

WebsocketsClient wsAudio;
WebsocketsClient wsDevice;

volatile bool audioConnected  = false;
volatile bool deviceConnected = false;

volatile bool recording = false;

void i2s_init_inmp441() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 16,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = -1,
    .data_in_num = I2S_SD
  };

  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
  i2s_zero_dma_buffer(I2S_NUM_0);

  Serial.println("[I2S] initialized");
}

void ws_audio_init() {
  wsAudio.onEvent([](WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
      audioConnected = true;
      Serial.println("[WS AUDIO] connected");

      if (recording) {
        wsAudio.send("START");
      }

    } else if (event == WebsocketsEvent::ConnectionClosed) {
      audioConnected = false;
      Serial.println("[WS AUDIO] disconnected");
    }
  });

  wsAudio.connect(WS_AUDIO_URL);
}

void ws_device_init() {
  wsDevice.onEvent([](WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
      deviceConnected = true;
      Serial.println("[WS DEVICE] connected");
      wsDevice.send("HELLO ESP32");

    } else if (event == WebsocketsEvent::ConnectionClosed) {
      deviceConnected = false;
      Serial.println("[WS DEVICE] disconnected");
    }
  });

  wsDevice.onMessage([](WebsocketsMessage msg) {
    if (!msg.isText()) return;

    String cmd = msg.data();
    cmd.trim();
    cmd.toUpperCase();

    if (cmd == "START") {
      recording = true;
      Serial.println("[CMD] START -> recording ON");

      if (audioConnected) wsAudio.send("START");

      if (deviceConnected) wsDevice.send("REC:ON");

    } else if (cmd == "STOP") {
      recording = false;
      Serial.println("[CMD] STOP -> recording OFF");

      if (audioConnected) wsAudio.send("STOP");

      if (deviceConnected) wsDevice.send("REC:OFF");
    }
  });

  wsDevice.connect(WS_DEVICE_URL);
}

void mic_send_chunk_ws() {
  if (!recording || !audioConnected) return;

  size_t bytesRead = 0;
  esp_err_t err = i2s_read(I2S_NUM_0, (void*)i2s_in, CHUNK_BYTES_IN, &bytesRead, portMAX_DELAY);
  if (err != ESP_OK || bytesRead != CHUNK_BYTES_IN) return;

  for (int i = 0; i < SAMPLES_PER_CHUNK; i++) {
    pcm16[i] = (int16_t)(i2s_in[i] >> 14);
  }

  wsAudio.sendBinary((const char*)pcm16, CHUNK_BYTES_OUT);
}

void ws_reconnect_if_needed() {
  static unsigned long lastTryAudio  = 0;
  static unsigned long lastTryDevice = 0;

  if (!audioConnected && millis() - lastTryAudio > 2000) {
    lastTryAudio = millis();
    Serial.println("[WS AUDIO] reconnect...");
    wsAudio.connect(WS_AUDIO_URL);
  }

  if (!deviceConnected && millis() - lastTryDevice > 2000) {
    lastTryDevice = millis();
    Serial.println("[WS DEVICE] reconnect...");
    wsDevice.connect(WS_DEVICE_URL);
  }
}

void setup_audio() {
  Serial.begin(115200);
  delay(200);

  WS_AUDIO_URL  = String("ws://") + SERVER_IP + ":8765/audio";
  WS_DEVICE_URL = String("ws://") + SERVER_IP + ":8765/device";

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("[WiFi] connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] connected");
  Serial.print("[WiFi] IP: ");
  Serial.println(WiFi.localIP());

  i2s_init_inmp441();

  ws_audio_init();
  ws_device_init();

  Serial.println("Ready. Use Teacher Panel buttons (Start/Stop).");
}

void loop_audio() {
  wsAudio.poll();
  wsDevice.poll();

  mic_send_chunk_ws();

  ws_reconnect_if_needed();
}

void setup() {
  setup_dht();
  setup_audio();
}

void loop() {
  loop_audio();
  loop_dht();
}
