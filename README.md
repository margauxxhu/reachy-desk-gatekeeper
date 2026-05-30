# Desk Gatekeeper

A human-robot interaction project for the [Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) robot that acts as an intelligent desk guardian. Someone outside your room can ask Reachy whether it's okay to come in — Reachy finds you, reads your response, and reports back over Discord.

## Use Case

You're at your desk working. Someone in your home wants to know if they can enter the room without interrupting you.

They type `/knock` in a shared Discord server. Reachy Mini:

1. **Searches for your face** — sweeps left, centre, and right using its onboard camera
2. **Locks onto you** — looks directly at your face and waits up to 8 seconds
3. **Reads your signal** — detects whether you nod twice (the "busy" signal)
4. **Reports back** to the person on Discord:
   - 🔴 **Do Not Disturb** — two nods detected, you're in a call or focused
   - 🟢 **Come On In** — no signal, you're available

No need to touch your phone or break your focus.

## Project Structure

```
desk-gatekeeper/
├── main.py                  # Entry point — connects Reachy + launches Discord bot
├── requirements.txt
├── .env.example             # Environment variable template
├── bot/
│   └── commands.py          # /knock slash command and Discord interaction flow
├── vision/
│   ├── face_detection.py    # OpenCV Haar-cascade face detection via Reachy's camera
│   └── gesture.py           # Nod detection via face Y-position tracking
└── robot/
    └── movements.py         # Reachy movement routines (search, gaze hold, reactions)
```

## Requirements

- [Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) with its daemon running
- Python 3.12+ (use the robot's `/venvs/apps_venv`)
- A Discord bot with the `applications.commands` scope and a server to invite it to

## Setup

### 1. Clone onto Reachy Mini

```bash
ssh pollen@reachy-mini.local
git clone https://github.com/margauxxhu/desk-gatekeeper.git
cd desk-gatekeeper
```

### 2. Install dependencies

```bash
/venvs/apps_venv/bin/pip install "discord.py>=2.3.2" python-dotenv
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

### 4. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → New Application → Bot
2. Copy the token into `.env`
3. Under OAuth2 → URL Generator, select scopes `bot` + `applications.commands`
4. Bot permissions: **Read Messages**, **Send Messages**, **Embed Links**
5. Invite the bot to your server

### 5. Run

```bash
cd ~/desk-gatekeeper
nohup /venvs/apps_venv/bin/python main.py > gatekeeper.log 2>&1 &
```

## How Nod Detection Works

Frames are sampled at ~5 fps for 8 seconds. The normalised Y-position of the largest detected face is tracked over time. A nod is counted when the Y-centre drops below the baseline by more than `NOD_THRESHOLD` (6% of frame height) and then recovers — matching the natural down-then-up motion of a head nod.

Tune these constants in `vision/gesture.py` if detection is too sensitive or not sensitive enough:

```python
NOD_THRESHOLD = 0.06   # fraction of frame height per nod
EMA_ALPHA     = 0.4    # smoothing (higher = more responsive, noisier)
```

The scan sweep positions in `robot/movements.py` can also be adjusted if Reachy's field of view doesn't cover your usual seating position.

## Extending

- **Sound** — `robot.media.play_sound("file.wav")` is available for audio feedback
- **Auto-trigger** — replace the Discord command with a continuous polling loop
- **Face recognition** — swap the Haar cascade for a model that identifies specific people
