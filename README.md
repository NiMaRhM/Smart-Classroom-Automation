# Classroom Recording System
<img width="1917" height="931" alt="Screenshot 2026-07-11 142124" src="https://github.com/user-attachments/assets/3668e2e4-d338-4b6c-9fa5-a8a588dc9d3c" />
An integrated hardware-software system for recording classroom lectures, transcribing Persian speech, and generating concise AI-powered summaries.

The system uses an **ESP32-based recording device** with an I2S microphone, DHT11 environmental sensor, and ST7735 TFT display. A Python server receives audio streams, stores recordings, transcribes Persian speech with Whisper, and provides a web interface for teachers and students.

---

## Features

- Real-time audio streaming over WebSockets
- Remote recording control for teachers
- Automatic recording storage
- Persian speech-to-text using OpenAI Whisper (`large-v3`)
- Noise reduction before transcription
- AI-generated lecture summaries using an OpenAI-compatible LLM API
- Student portal for audio playback, downloads, transcripts, and summaries
- Teacher dashboard for starting and stopping recordings
- Temperature and humidity monitoring with DHT11
- Local device status display using an ST7735 TFT screen
- Automatic ESP32 Wi-Fi and WebSocket reconnection

---

## Architecture

```text
┌──────────────────┐      WebSocket Audio        ┌─────────────────────┐
│   ESP32 Device   │ ─────────────────────────▶ │   Python Server      │
│                  │                             │                      │
│  -  I2S Microphone│                            │  -  Flask Web UI      │
│  -  DHT11 Sensor  │ ◀─────────────────────────│  -  WebSocket Server  │
│  -  TFT Display   │     WebSocket Commands    │  -  File Storage      │
└──────────────────┘                            └──────────┬────────────┘
                                                            │
                                                            ▼
                                                  ┌────────────────────┐
                                                  │    speech.py       │
                                                  │                    │
                                                  │  -  Noise Reduction│
                                                  │  -  Whisper STT    │
                                                  │  -  LLM Summary    │
                                                  └────────────────────┘
```

---

## Hardware Requirements

| Component | Purpose |
|---|---|
| ESP32 Development Board | Main controller and Wi-Fi connection |
| INMP441 Digital Microphone | I2S audio capture |
| DHT11 Sensor | Temperature and humidity measurement |
| ST7735 TFT Display | Device status and sensor display |
| Breadboard and jumper wires | Hardware connections |
| Optional push button | Local recording control |

> See [`manual.pdf`](manual.pdf) for detailed wiring diagrams and hardware assembly instructions.

---

## Pin Connections

| Module | ESP32 Pin |
|---|---|
| DHT11 Data | GPIO 27 |
| TFT CS | GPIO 5 |
| TFT DC | GPIO 21 |
| TFT RST | GPIO 4 |
| TFT SCLK | GPIO 18 |
| TFT MOSI | GPIO 23 |
| INMP441 SD | GPIO 32 |
| INMP441 WS | GPIO 25 |
| INMP441 SCK | GPIO 26 |
| INMP441 L/R | GND |
| Optional Button | GPIO 33 with pull-up |

---

## Software Requirements

### Server

- Python `3.11` recommended
- FFmpeg for audio conversion and processing
- Optional NVIDIA CUDA-compatible GPU for faster Whisper transcription

### ESP32

- Arduino IDE
- ESP32 Board Package
- Required Arduino libraries

---

## Arduino Setup

### Install ESP32 Board Package

1. Open **Arduino IDE**.
2. Go to **File → Preferences**.
3. Add this URL under **Additional Board Manager URLs**:

```text
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

4. Go to **Tools → Board → Boards Manager**.
5. Search for `esp32`.
6. Install the ESP32 package by **Espressif Systems**.

### Required Arduino Libraries

Install the following libraries through **Arduino Library Manager**:

- `Adafruit GFX Library`
- `Adafruit ST7735 and ST7789 Library`
- `DHT sensor library` by Adafruit
- `ArduinoWebsockets` by Gil Maimon

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/classroom-recording-system.git
cd classroom-recording-system
```

### 2. Create a Virtual Environment

#### Windows

```bash
py -m venv .venv
.\.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

FFmpeg is required for audio processing.

#### Windows

```bash
choco install ffmpeg
```

#### Ubuntu / Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

#### macOS

```bash
brew install ffmpeg
```

Verify the installation:

```bash
ffmpeg -version
```

### 5. Optional: Install CUDA PyTorch

For GPU-accelerated Whisper transcription:

```bash
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Verify CUDA support:

```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

---

## ESP32 Firmware Setup

Open the ESP32 sketch from the `STM32/` directory, or open the provided `.ino` file in Arduino IDE.

Update your Wi-Fi credentials and server IP address:

```cpp
const char* WIFI_SSID = "YourWiFiSSID";
const char* WIFI_PASS = "YourWiFiPassword";

const char* SERVER_IP = "192.168.x.x";
```

Replace `192.168.x.x` with the local IP address of the computer running the Python server.

Then:

1. Connect the ESP32 to your computer using USB.
2. Select the correct board and serial port in Arduino IDE.
3. Compile and upload the firmware.
4. Open the Serial Monitor to check Wi-Fi and WebSocket status.

---

## Server Configuration

### Configure the LLM API

Open `speech.py` and configure your API credentials:

```python
OPENAI_API_KEY = "your-api-key"
AVALAI_BASE_URL = "https://api.cerebras.ai/v1"
MODEL_NAME = "llama-3.3-70b"
```

> **Warning:** Do not commit real API keys to GitHub. Use environment variables or a `.env` file.

Example:

```python
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AVALAI_BASE_URL = os.getenv(
    "AVALAI_BASE_URL",
    "https://api.cerebras.ai/v1"
)
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b")
```

### Configure Teacher Password

Open `server.py` and change the default password:

```python
TEACHER_PASSWORD = "change-this-password"
```

---

## Run the Server

Start the Python server:

```bash
python server.py
```

The server provides the following services:

| Service | Address |
|---|---|
| Web Interface | `http://0.0.0.0:8080` |
| Audio WebSocket | `ws://0.0.0.0:8765/audio` |
| Device Control WebSocket | `ws://0.0.0.0:8765/device` |

Open the web application:

```text
http://<server-ip>:8080
```

Example:

```text
http://192.168.1.100:8080
```

---

## Usage

### Teacher Panel

1. Open `http://<server-ip>:8080`.
2. Log in to the teacher panel.
3. Press **Start Recording**.
4. The server sends a command to the ESP32.
5. The ESP32 starts streaming classroom audio.
6. Press **Stop Recording** when the lecture ends.

### Student Panel

Students can:

- Browse recorded classroom sessions
- Play recordings in the browser
- Download audio files
- View Persian transcripts
- Read AI-generated summaries

### Process Recordings

Click the **Speech** button on the student page to process new recordings.

The processing pipeline performs:

1. Noise reduction
2. Audio cleanup and conversion
3. Persian transcription using Whisper
4. Transcript correction
5. AI summary generation

---

## Output Directories

| Directory | Description |
|---|---|
| `recordings/` | Original lecture audio recordings |
| `recordings/clean/` | Noise-reduced WAV files |
| `recordings/texts/speech/` | Persian speech transcripts |
| `recordings/texts/summary/` | AI-generated lecture summaries |
| `tmp_pcm/` | Temporary PCM chunks while recording |

---

## Project Structure

```text
.
├── server.py                  # Flask server and WebSocket handlers
├── speech.py                  # Audio processing, Whisper, and summaries
├── requirements.txt           # Python dependencies
├── templates/                 # HTML templates
├── static/                    # CSS, JavaScript, and assets
├── recordings/                # Audio recordings and generated results
│   ├── clean/                 # Cleaned audio files
│   └── texts/
│       ├── speech/            # Speech-to-text transcripts
│       └── summary/           # Generated summaries
├── tmp_pcm/                   # Temporary PCM chunks
├── STM32/                     # ESP32 Arduino firmware
├── manual.pdf                 # Hardware assembly documentation
├── report.pdf                 # Project report
└── need more.txt              # Additional setup notes
```

---

## Configuration

### Server Settings

Edit `server.py` to change:

- HTTP server port
- WebSocket server port
- Flask secret key
- Teacher password
- Recording storage paths

### Audio Settings

Audio settings must match between the ESP32 firmware and the Python server.

You may configure:

- Sample rate
- Number of audio channels
- PCM bit depth
- Audio chunk size
- Recording buffer size

### Whisper Model

The default transcription model is:

```python
model = whisper.load_model("large-v3")
```

For systems with limited RAM or GPU memory, use a smaller model:

```python
model = whisper.load_model("medium")
```

Available models:

```text
tiny
base
small
medium
large-v3
```

### Summary Prompt

Customize the prompt in `speech.py` to control the generated summaries.

For example, summaries can include:

- Key lecture topics
- Important definitions
- Main conclusions
- Homework assignments
- Exam-related points
- Questions raised during class

---

## Troubleshooting

### ESP32 Cannot Connect to Wi-Fi

- Check the Wi-Fi SSID and password.
- Confirm that the ESP32 and server use the same local network.
- Check the Serial Monitor for errors.
- Ensure the router supports 2.4 GHz Wi-Fi if required by your ESP32 board.

### WebSocket Connection Fails

- Ensure that `server.py` is running.
- Verify the `SERVER_IP` value in the ESP32 firmware.
- Allow ports `8080` and `8765` through the firewall.
- Do not use `localhost` as the ESP32 server address.

### No Audio Is Recorded

- Verify INMP441 wiring.
- Check I2S pin assignments.
- Confirm that the microphone receives power.
- Ensure ESP32 and server audio settings match.
- Check serial logs for I2S or WebSocket errors.

### Whisper Runs Out of Memory

- Use a smaller Whisper model such as `medium`, `small`, or `base`.
- Run Whisper on CPU.
- Close other GPU-intensive applications.
- Process shorter recordings.

### Summarization Fails

- Verify the API key.
- Check the API base URL.
- Confirm internet connectivity.
- Check API usage limits, credits, and rate limits.
- Review Python server logs for details.

---

## Security and Privacy

Before deploying the system in a real classroom:

- Change the default teacher password.
- Store API keys in environment variables.
- Do not commit `.env` files or credentials to GitHub.
- Use HTTPS and secure WebSockets for public deployment.
- Restrict access to recordings and student data.
- Follow local privacy, consent, and education-data regulations.
- Obtain consent from lecturers and students before recording classes.

---

## Documentation

- [`manual.pdf`](manual.pdf) — Hardware assembly instructions and wiring diagrams
- [`report.pdf`](report.pdf) — Project design, implementation, and evaluation
- [`need more.txt`](need%20more.txt) — Additional installation commands and notes

---


## Acknowledgements

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Cerebras](https://cerebras.ai/) for LLM inference APIs
- [LangChain](https://www.langchain.com/) for LLM workflow support
- [ArduinoWebsockets](https://github.com/gilmaimon/ArduinoWebsockets) for ESP32 WebSocket communication
- [Adafruit](https://www.adafruit.com/) libraries for display and DHT11 sensor support
