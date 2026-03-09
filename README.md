# FitBot - AI Fitness Telegram Bot

FitBot is a Telegram bot that acts as your personal AI fitness coach. It provides workout plans, fitness calculators, nutrition tips, cardio routines, stretching guides, sleep advice, a personal workout & running tracker with weekly charts, and an AI-powered chat powered by OpenAI GPT.

---

## Features

- **Workout Plans** — Chest, back, legs, arms, shoulders, abs, full body
- **Cardio Plans** — Beginner, intermediate, advanced HIIT
- **Fitness Calculators** — BMI, daily calories, protein intake, water intake, body fat %
- **Stretching Routines** — Morning, post-workout, office/desk
- **Warm-Up Routine** — Pre-workout warm-up guide
- **Daily Challenges** — A new fitness challenge every day
- **Nutrition Tips** — Randomized diet and macro guidance
- **Sleep & Recovery Tips** — Evidence-based rest advice
- **Motivation Quotes** — Daily fitness inspiration
- **🏋️ Workout Tracker** — Log gym sets, view today's log, weekly summary with chart
- **🏃 Running Tracker** — Log runs with auto-calculated pace, weekly km summary
- **📊 Weekly Chart** — 3-panel chart: daily gym volume, volume by exercise, daily running distance
- **AI Chat** — Ask any fitness question and get a GPT-powered response

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Telegram Library | aiogram v3 |
| AI | OpenAI GPT-3.5 Turbo |
| Database | SQLite (via `sqlite3`) |
| Charts | Matplotlib |
| Config | python-dotenv |

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Akashkar00/fitness-telegram-bot.git
cd fitness-telegram-bot
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

Or with conda:

```bash
conda create -n fitbot python=3.11 -y
conda activate fitbot
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the bot token you receive

### 5. Get an OpenAI API Key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new secret key and copy it

### 6. Configure environment variables

Create a `.env` file in the root directory:

```ini
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### 7. Run the bot

```bash
python main.py
```

---

## Bot Commands

### Basics
| Command | Description |
|---|---|
| `/start` | Start the bot |
| `/help` | Show all commands |
| `/clear` | Clear AI conversation context |

### Workouts
| Command | Description |
|---|---|
| `/workout <muscle>` | Get a workout plan |
| `/cardio <level>` | Get a cardio plan |
| `/warmup` | Pre-workout warm-up routine |
| `/stretch <type>` | Get a stretching routine |

**Workout muscles:** `chest`, `back`, `legs`, `arms`, `shoulders`, `abs`, `full body`

**Cardio levels:** `beginner`, `intermediate`, `advanced`

**Stretch types:** `morning`, `post-workout`, `office`

### Calculators
| Command | Example | Description |
|---|---|---|
| `/bmi <weight_kg> <height_cm>` | `/bmi 70 175` | Calculate BMI |
| `/calories <weight> <height> <age> <gender>` | `/calories 70 175 25 male` | Daily calorie needs |
| `/protein <weight_kg>` | `/protein 70` | Daily protein intake |
| `/water <weight_kg>` | `/water 70` | Daily water intake |
| `/bodyfat <gender> <waist> <neck> <height>` | `/bodyfat male 85 38 175` | Body fat % (US Navy method) |

### Daily
| Command | Description |
|---|---|
| `/nutrition` | Random nutrition tips |
| `/motivation` | Daily motivation quote |
| `/sleep` | Sleep & recovery tips |
| `/challenge` | Today's fitness challenge |

### 🏋️ Workout Tracker
| Command | Example | Description |
|---|---|---|
| `/log <exercise> <weight>kg <sets>x<reps>` | `/log bench 80kg 3x10` | Log a gym set |
| `/today` | `/today` | View today's gym + running activity |
| `/summary` | `/summary` | 7-day report + chart |
| `/delete` | `/delete` | Clear all your tracker data |

### 🏃 Running Tracker
| Command | Example | Description |
|---|---|---|
| `/run <distance>km <duration>min` | `/run 5km 28min` | Log a run (pace auto-calculated) |
| `/runs` | `/runs` | View today's runs with pace |
| `/today` | `/today` | View today's gym + running combined |
| `/summary` | `/summary` | 7-day running stats + chart |

### 📊 Weekly Summary Chart (`/summary`)
The chart has **3 panels**:
1. **Daily Gym Volume (kg)** — bar chart of total volume per day
2. **Volume by Exercise (kg)** — horizontal bars per exercise
3. **Daily Running Distance (km)** — bar chart of km per day _(only shown if you have runs logged)_

### AI Chat
Just send any fitness-related message and FitBot will respond using GPT.

---

## Project Structure

```
fitness-telegram-bot/
├── main.py              # Bot logic, command handlers, tracker
├── fitness.db           # SQLite database (auto-created, not committed)
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables (not committed)
```

---

## Security Note

Never commit your `.env` file or paste real API keys anywhere in the code or README. The `.gitignore` already excludes `.env` and `fitness.db`.

---

## Author

Built by **Akash Kar** — NIT Rourkela | [GitHub](https://github.com/Akashkar00)
