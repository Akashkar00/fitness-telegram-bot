# FitBot - AI Fitness Telegram Bot

FitBot is a Telegram bot that acts as your personal AI fitness coach. It provides workout plans, fitness calculators, nutrition tips, cardio routines, stretching guides, sleep advice, and an AI-powered chat powered by OpenAI GPT.

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
- **AI Chat** — Ask any fitness question and get a GPT-powered response

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| Telegram Library | aiogram |
| AI | OpenAI GPT-3.5 Turbo |
| Config | python-dotenv |
| Deployment | Heroku |

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Akashkar00/fitness-telegram-bot.git
cd fitness-telegram-bot
```

### 2. Create a virtual environment

```bash
conda create -n fitbot python=3.11 -y
conda activate fitbot
```

Or with venv:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
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

### AI Chat
Just send any fitness-related message and FitBot will respond using GPT.

---

## Deployment on Heroku

### 1. Install Heroku CLI and login

```bash
heroku login
```

### 2. Create a Heroku app

```bash
heroku create your-app-name
```

### 3. Set environment variables

```bash
heroku config:set OPENAI_API_KEY=your_openai_api_key
heroku config:set TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### 4. Deploy

```bash
git push heroku main
```

---

## Project Structure

```
fitness-telegram-bot/
├── main.py              # Bot logic and command handlers
├── requirements.txt     # Python dependencies
├── Procfile             # Heroku process config
├── runtime.txt          # Python version for Heroku
└── .env                 # Environment variables (not committed)
```

---

## Security Note

Never commit your `.env` file or paste real API keys anywhere in the code or README. The `.gitignore` already excludes `.env`.

---

## Author

Built by **Akash** — [GitHub](https://github.com/Akashkar00)
