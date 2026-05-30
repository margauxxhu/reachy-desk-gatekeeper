# Desk Gatekeeper

A human-robot interaction project for the [Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) robot that acts as an intelligent desk guardian. Someone outside your room asks Reachy whether it's okay to come in — Reachy finds you, reads your physical response, and reports back. No words, no phone taps, no interruption.

## Use Case

You're at your desk working. Someone in your home wants to know if they can enter without interrupting you.

They send a trigger — via Discord or iMessage — and Reachy Mini:

1. **Searches for your face** — sweeps left, centre, and right using its onboard camera
2. **Locks onto you** — looks directly at your face and waits up to 8 seconds
3. **Reads your signal** — detects whether you nod twice (the "busy" signal)
4. **Reports back** on the same channel that triggered it:
   - 🔴 **Do Not Disturb** — two nods detected, you're in a call or focused
   - 🟢 **Come On In** — no signal, you're available

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
│   ├── face_detection.py    # OpenCV Haar-cascade face detection via Reachy's camera
│   └── gesture.py           # Nod detection via face Y-position tracking
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
{ "found": true, "busy": false, "message": "🟢 Come On In — they're available!" }
```

### 6. Run

```bash
cd ~/reachy-desk-gatekeeper
nohup /venvs/apps_venv/bin/python main.py > gatekeeper.log 2>&1 &
```

Both the Discord bot and HTTP server start together in the same process.

## How Nod Detection Works

Frames are sampled at ~5 fps for 8 seconds. The normalised Y-position of the largest detected face is tracked over time. A nod is counted when the Y-centre drops below baseline by more than `NOD_THRESHOLD` (6% of frame height) and then recovers — matching the natural down-then-up motion of a head nod.

Tune in `vision/gesture.py`:

```python
NOD_THRESHOLD = 0.06   # fraction of frame height per nod
EMA_ALPHA     = 0.4    # smoothing (higher = more responsive, noisier)
```

Scan sweep positions in `robot/movements.py` can be adjusted if Reachy's field of view doesn't cover your usual seating position.

## Extending

- **Sound** — `robot.media.play_sound("file.wav")` is available for audio feedback
- **Auto-trigger** — replace the Discord command with a continuous polling loop
- **Face recognition** — swap the Haar cascade for a model that identifies specific people
- **Other gestures** — thumbs up/down, hand raise — extend `vision/gesture.py`
