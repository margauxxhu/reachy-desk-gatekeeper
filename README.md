# Desk Gatekeeper

A human-robot interaction project for the [Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) robot that acts as an intelligent desk guardian. Someone outside your room asks Reachy whether it's okay to come in — Reachy finds you, reads your physical response, and reports back. No words, no phone taps, no interruption.

## Use Case

You're at your desk working. Someone in your home wants to know if they can enter without interrupting you.

They send a trigger — via Discord or iMessage — and Reachy Mini:

1. **Searches for your face** — sweeps left, centre, and right using its onboard camera
2. **Locks onto you** — looks directly at your face, antennas perk up to signal "I see you — respond now"
3. **Waits 8 seconds for your signal** — watches for a fist gesture
4. **Reports back** on the same channel that triggered it:
   - 🟢 **Come On In** — fist raised toward the camera: you're free, they can enter
   - 🔴 **Not yet** — no gesture after 8 seconds: default is busy, give them a moment

**The signal rule is simple:**
- ✊ **Raise a fist** = available, come in
- **Do nothing** = busy / not now (passive default — no action needed when you're in a call)

No need to touch your phone or break your focus. The interaction is entirely physical.

## Two Trigger Rails

| Rail | How it works |
|---|---|
| **Discord** | Housemate types `/knock` in a shared server → Reachy runs the sequence → Discord embed reply |
| **iMessage** | Housemate texts you → Apple Shortcut fires a `POST /knock` to Reachy's HTTP server → Reachy runs the same sequence → iMessage reply sent back automatically |

Both rails share the same core logic and the same robot behaviour.

## Project Structure

```
desk-gatekeeper/
├── main.py                  # Entry point — connects Reachy, starts Discord bot + HTTP server
├── requirements.txt
├── .env.example
├── core/
│   └── gatekeeper.py        # Shared knock sequence used by both rails
├── api/
│   └── server.py            # FastAPI HTTP server (port 8080) — iMessage rail
├── bot/
│   └── commands.py          # /knock Discord slash command
├── vision/
│   ├── face_detection.py    # MediaPipe BlazeFace + Haar fallback face detection
│   └── gesture.py           # Fist gesture detection via MediaPipe Hands
└── robot/
    └── movements.py         # Reachy movement routines (search, gaze hold, reactions)
```

## Requirements

- [Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) with its daemon running
- Python 3.12+ (use the robot's `/venvs/apps_venv`)
- A Discord bot with the `applications.commands` scope (for the Discord rail)
- An iPhone with Shortcuts (for the iMessage rail)

## Setup

### 1. Clone onto Reachy Mini

```bash
ssh pollen@reachy-mini.local
git clone https://github.com/margauxxhu/reachy-desk-gatekeeper.git
cd reachy-desk-gatekeeper
```

### 2. Install dependencies

```bash
/venvs/apps_venv/bin/pip install "discord.py>=2.3.2" python-dotenv "fastapi>=0.111.0" "uvicorn>=0.29.0"
```

The Reachy SDK and OpenCV are already available in `/venvs/apps_venv`.

### 3. Configure environment

```bash
cp .env.example .env
nano .env
```

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Your Discord bot token |
| `DISCORD_GUILD_ID` | Your server ID (for instant command sync) |
| `REACHY_HOST` | `localhost` when running on the robot |
| `REACHY_PORT` | `8000` (Reachy Mini daemon default) |

### 4. Discord bot setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → New Application → Bot
2. Copy the token into `.env`
3. Under OAuth2 → URL Generator, select scopes `bot` + `applications.commands`
4. Bot permissions: **Read Messages**, **Send Messages**, **Embed Links**
5. Invite the bot to your server

### 5. iMessage rail — Apple Shortcuts setup

Create a Shortcut on the triggering person's iPhone:

1. **Automation** → New → **Message received** from [specific contact] → Run Immediately
2. Action: **Get Contents of URL** — `POST http://reachy-mini.local:8080/knock`
3. Action: **Get Dictionary Value** — key `message`, from Contents of URL
4. Action: **Send Message** — message: Dictionary Value, to: [original contact]

The HTTP server returns:
```json
{ "found": true, "busy": false, "message": "🟢 Come On In — they're free, go ahead!" }
```

### 6. Run

```bash
cd ~/reachy-desk-gatekeeper
nohup /venvs/apps_venv/bin/python main.py > gatekeeper.log 2>&1 &
```

Both the Discord bot and HTTP server start together in the same process.

## How Gesture Detection Works

**Face detection** uses MediaPipe BlazeFace (with Haar cascade as fallback). BlazeFace handles angled and bowed faces reliably — it will find you even when you're looking at your screen, not at Reachy.

**Fist detection** uses MediaPipe Hands sampled at ~10 fps for 8 seconds. A fist is confirmed when 3 or more of the 4 fingers have their tip curled below their middle knuckle for 2 consecutive frames. This works at any position in frame — just raise your fist toward the camera.

Tune in `vision/gesture.py`:

```python
CONFIRM_FRAMES = 2   # consecutive frames required to confirm the fist
```

Scan sweep positions in `robot/movements.py` can be adjusted if Reachy's field of view doesn't cover your usual seating position.

## Extending

- **Sound** — `robot.media.play_sound("file.wav")` is available for audio feedback
- **Auto-trigger** — replace the Discord command with a continuous polling loop
- **Face recognition** — add a recognition layer on top of BlazeFace to identify specific people
- **Other gestures** — swap `vision/gesture.py` for thumbs up, open palm, or any MediaPipe Hands landmark pattern
