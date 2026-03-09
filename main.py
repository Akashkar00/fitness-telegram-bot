import logging
import random
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO

import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
import asyncio
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Config ────────────────────────────────────────────────────────────────────
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()


# ─── Workout & Run DB ─────────────────────────────────────────────────────────

DB_PATH = "fitness.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                date      TEXT    NOT NULL,
                exercise  TEXT    NOT NULL,
                sets      INTEGER NOT NULL,
                reps      INTEGER NOT NULL,
                weight_kg REAL    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                date         TEXT    NOT NULL,
                distance_km  REAL    NOT NULL,
                duration_min REAL    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weight_log (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date    TEXT    NOT NULL,
                weight  REAL    NOT NULL,
                UNIQUE(user_id, date)
            )
        """)
        conn.commit()

init_db()


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _pace_str(dist: float, dur: float) -> str:
    if dist <= 0:
        return "N/A"
    p = dur / dist
    return f"{int(p)}:{int((p - int(p)) * 60):02d} min/km"

def _week_since() -> str:
    return (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")

def _get_week_workouts(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT date, exercise, sets, reps, weight_kg FROM workouts
            WHERE user_id=? AND date>=? ORDER BY date, exercise
        """, (user_id, _week_since())).fetchall()

def _get_week_runs(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT date, distance_km, duration_min FROM runs
            WHERE user_id=? AND date>=? ORDER BY date
        """, (user_id, _week_since())).fetchall()

def _build_chart(by_date: dict, by_exercise: dict, run_by_date: dict, weight_by_date: dict = None) -> BytesIO:
    has_runs    = bool(run_by_date)
    has_weights = bool(weight_by_date)
    num_panels  = 2 + int(has_runs) + int(has_weights)

    fig, axes = plt.subplots(num_panels, 1, figsize=(9, num_panels * 4 + 1))
    if num_panels == 1:
        axes = [axes]
    ax1, ax2 = axes[0], axes[1]
    ax3 = axes[2] if num_panels >= 3 else None
    ax4 = axes[3] if num_panels == 4 else None
    # If only 3 panels with no runs but has weights
    if has_runs and not has_weights:
        ax3_run, ax4 = axes[2], None
    elif not has_runs and has_weights:
        ax3_run, ax3_wt = None, axes[2]
    elif has_runs and has_weights:
        ax3_run, ax3_wt = axes[2], axes[3]
    else:
        ax3_run, ax3_wt = None, None

    fig.patch.set_facecolor("#1a1a2e")
    for ax in axes:
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="white")
        ax.spines[:].set_color("#0f3460")
        ax.yaxis.label.set_color("white")
        ax.xaxis.label.set_color("white")
        ax.title.set_color("white")

    # Panel 1 — Daily gym volume
    dates = sorted(by_date)
    day_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%a\n%d %b") for d in dates]
    day_vols = [sum(s * r * w for _, s, r, w in by_date[d]) for d in dates]
    bars1 = ax1.bar(day_labels, day_vols, color="#e94560", edgecolor="#0f3460", linewidth=1.2)
    ax1.set_title("Daily Gym Volume (kg)", fontsize=13, fontweight="bold", pad=8)
    ax1.set_ylabel("Volume (kg)")
    if day_vols:
        ax1.set_ylim(0, max(day_vols) * 1.25)
        for bar, v in zip(bars1, day_vols):
            ax1.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + max(day_vols) * 0.02,
                     f"{v:.0f}", ha="center", va="bottom",
                     color="white", fontsize=9, fontweight="bold")

    # Panel 2 — Volume by exercise
    exs = sorted(by_exercise, key=lambda x: by_exercise[x])
    vols = [by_exercise[e] for e in exs]
    colors = plt.cm.plasma([i / max(len(exs), 1) for i in range(len(exs))])
    hbars = ax2.barh(exs, vols, color=colors, edgecolor="#0f3460")
    ax2.set_title("Volume by Exercise (kg)", fontsize=13, fontweight="bold", pad=8)
    ax2.set_xlabel("Volume (kg)")
    if vols:
        for bar, v in zip(hbars, vols):
            ax2.text(v + max(vols) * 0.01, bar.get_y() + bar.get_height() / 2,
                     f"{v:.0f}", va="center", color="white", fontsize=9, fontweight="bold")

    # Panel 3 — Daily running distance
    if ax3_run is not None:
        run_dates  = sorted(run_by_date)
        run_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%a\n%d %b") for d in run_dates]
        run_dists  = [run_by_date[d] for d in run_dates]
        bars3 = ax3_run.bar(run_labels, run_dists, color="#00b4d8", edgecolor="#0f3460", linewidth=1.2)
        ax3_run.set_title("Daily Running Distance (km)", fontsize=13, fontweight="bold", pad=8)
        ax3_run.set_ylabel("Distance (km)")
        if run_dists:
            ax3_run.set_ylim(0, max(run_dists) * 1.25)
            for bar, v in zip(bars3, run_dists):
                ax3_run.text(bar.get_x() + bar.get_width() / 2,
                             bar.get_height() + max(run_dists) * 0.02,
                             f"{v:.1f}", ha="center", va="bottom",
                             color="white", fontsize=9, fontweight="bold")

    # Panel 4 — Body weight trend
    if ax3_wt is not None and weight_by_date:
        wt_dates  = sorted(weight_by_date)
        wt_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%a\n%d %b") for d in wt_dates]
        wt_vals   = [weight_by_date[d] for d in wt_dates]
        ax3_wt.plot(wt_labels, wt_vals, color="#a8dadc", linewidth=2.5,
                    marker="o", markersize=7,
                    markerfacecolor="#e94560", markeredgecolor="white", markeredgewidth=1)
        ax3_wt.fill_between(range(len(wt_vals)), wt_vals,
                            min(wt_vals) - 0.3, alpha=0.15, color="#a8dadc")
        ax3_wt.set_title("Body Weight (kg)", fontsize=13, fontweight="bold", pad=8)
        ax3_wt.set_ylabel("Weight (kg)")
        ax3_wt.set_ylim(min(wt_vals) - 1, max(wt_vals) + 1)
        ax3_wt.set_xticks(range(len(wt_labels)))
        ax3_wt.set_xticklabels(wt_labels, fontsize=8)
        for i, (lbl, v) in enumerate(zip(wt_labels, wt_vals)):
            ax3_wt.annotate(f"{v}kg", (i, v),
                            textcoords="offset points", xytext=(0, 8),
                            ha="center", color="white", fontsize=8)

    plt.tight_layout(pad=3)
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf


# ─── Conversation Memory ──────────────────────────────────────────────────────
class Reference:
    """Stores conversation context for OpenAI."""
    def __init__(self):
        self.response = ""

reference = Reference()
model_name = "gpt-3.5-turbo"

FITNESS_SYSTEM_PROMPT = """You are FitBot 💪, a professional fitness coach and nutritionist AI assistant. 
You ONLY answer questions related to fitness, workouts, nutrition, health, and wellness.
If someone asks something unrelated to fitness, politely redirect them to fitness topics.
Keep responses concise, motivational, and actionable.
Use emojis to make responses engaging. Always encourage the user."""


# ─── Workout Database ─────────────────────────────────────────────────────────
WORKOUTS = {
    "chest": {
        "title": "🏋️ Chest Day Workout",
        "exercises": [
            "1. Barbell Bench Press — 4×8-10",
            "2. Incline Dumbbell Press — 3×10-12",
            "3. Cable Flyes — 3×12-15",
            "4. Push-Ups (to failure) — 3 sets",
            "5. Dumbbell Pullover — 3×12",
        ]
    },
    "back": {
        "title": "🔙 Back Day Workout",
        "exercises": [
            "1. Deadlifts — 4×6-8",
            "2. Pull-Ups — 4×8-12",
            "3. Barbell Rows — 3×10-12",
            "4. Lat Pulldown — 3×12",
            "5. Seated Cable Row — 3×12-15",
        ]
    },
    "legs": {
        "title": "🦵 Leg Day Workout",
        "exercises": [
            "1. Barbell Squats — 4×8-10",
            "2. Leg Press — 3×10-12",
            "3. Romanian Deadlifts — 3×10-12",
            "4. Leg Curls — 3×12-15",
            "5. Calf Raises — 4×15-20",
        ]
    },
    "arms": {
        "title": "💪 Arms Day Workout",
        "exercises": [
            "1. Barbell Curls — 4×10-12",
            "2. Tricep Dips — 3×10-12",
            "3. Hammer Curls — 3×12",
            "4. Overhead Tricep Extension — 3×12",
            "5. Concentration Curls — 3×12-15",
        ]
    },
    "shoulders": {
        "title": "🔝 Shoulder Day Workout",
        "exercises": [
            "1. Overhead Press — 4×8-10",
            "2. Lateral Raises — 4×12-15",
            "3. Front Raises — 3×12",
            "4. Face Pulls — 3×15",
            "5. Shrugs — 4×12-15",
        ]
    },
    "abs": {
        "title": "🎯 Abs Workout",
        "exercises": [
            "1. Hanging Leg Raises — 4×12-15",
            "2. Cable Crunches — 3×15-20",
            "3. Plank — 3×60 seconds",
            "4. Russian Twists — 3×20",
            "5. Ab Wheel Rollouts — 3×10-12",
        ]
    },
    "full body": {
        "title": "🔥 Full Body Workout",
        "exercises": [
            "1. Squats — 4×8-10",
            "2. Bench Press — 4×8-10",
            "3. Barbell Rows — 3×10-12",
            "4. Overhead Press — 3×10-12",
            "5. Deadlifts — 3×6-8",
            "6. Pull-Ups — 3×max reps",
        ]
    },
}


# ─── Motivation Quotes ─────────────────────────────────────────────────────────
MOTIVATION_QUOTES = [
    "💪 \"The only bad workout is the one that didn't happen.\"",
    "🔥 \"Push yourself, because no one else is going to do it for you.\"",
    "🏆 \"Success isn't always about greatness. It's about consistency.\"",
    "⚡ \"Your body can stand almost anything. It's your mind you have to convince.\"",
    "🎯 \"The pain you feel today will be the strength you feel tomorrow.\"",
    "🚀 \"Don't stop when you're tired. Stop when you're done.\"",
    "💥 \"Sweat is just fat crying.\"",
    "🏋️ \"The only way to define your limits is by going beyond them.\"",
    "✨ \"Fitness is not about being better than someone else. It's about being better than you used to be.\"",
    "🌟 \"Wake up. Work out. Look hot. Kick ass. Repeat.\"",
    "💎 \"It never gets easier, you just get stronger.\"",
    "🔥 \"Train insane or remain the same.\"",
    "⭐ \"A one-hour workout is 4% of your day. No excuses.\"",
    "🦾 \"Sore today, strong tomorrow.\"",
    "🎖️ \"Fall in love with taking care of your body.\"",
]


# ─── Nutrition Tips ────────────────────────────────────────────────────────────
NUTRITION_TIPS = [
    "🥗 **Protein Intake**: Aim for 1.6-2.2g of protein per kg of body weight for muscle growth.",
    "💧 **Hydration**: Drink at least 3-4 liters of water daily, more during intense workouts.",
    "🍌 **Pre-Workout Meal**: Eat complex carbs + protein 1-2 hours before training.",
    "🥛 **Post-Workout**: Consume protein within 30-60 minutes after your workout.",
    "🥑 **Healthy Fats**: Include sources like avocado, nuts, olive oil — they support hormone production.",
    "🍗 **Lean Protein Sources**: Chicken breast, fish, eggs, tofu, lentils, Greek yogurt.",
    "⏰ **Meal Timing**: Eat every 3-4 hours to maintain energy and metabolism.",
    "🚫 **Avoid**: Processed foods, excessive sugar, and trans fats.",
    "🥦 **Micronutrients**: Eat a variety of colorful vegetables for vitamins and minerals.",
    "📊 **Track Macros**: Use a calorie-tracking app to hit your daily protein, carb, and fat targets.",
]


# ─── Stretching Routines ──────────────────────────────────────────────────────
STRETCHING_ROUTINES = {
    "morning": {
        "title": "🌅 Morning Stretch Routine (10 min)",
        "exercises": [
            "1. Neck Rolls — 30 sec each direction",
            "2. Shoulder Circles — 30 sec",
            "3. Cat-Cow Stretch — 1 min",
            "4. Standing Hamstring Stretch — 30 sec each leg",
            "5. Hip Circles — 30 sec each side",
            "6. Quad Stretch — 30 sec each leg",
            "7. Seated Spinal Twist — 30 sec each side",
            "8. Child's Pose — 1 min",
        ]
    },
    "post-workout": {
        "title": "🧘 Post-Workout Stretch Routine (10 min)",
        "exercises": [
            "1. Standing Quad Stretch — 30 sec each leg",
            "2. Pigeon Pose — 45 sec each side",
            "3. Hamstring Stretch — 30 sec each leg",
            "4. Chest Doorway Stretch — 30 sec",
            "5. Tricep Overhead Stretch — 30 sec each arm",
            "6. Seated Forward Fold — 1 min",
            "7. Lying Spinal Twist — 30 sec each side",
            "8. Corpse Pose (Savasana) — 2 min",
        ]
    },
    "office": {
        "title": "🖥️ Office/Desk Stretch Routine (5 min)",
        "exercises": [
            "1. Neck Side Stretch — 20 sec each side",
            "2. Shoulder Shrugs — 30 sec",
            "3. Wrist Circles — 20 sec each",
            "4. Seated Spinal Twist — 20 sec each side",
            "5. Seated Hip Stretch — 20 sec each side",
            "6. Standing Calf Raises — 30 sec",
            "7. Deep Breathing — 1 min",
        ]
    },
}


# ─── Warm-Up Routines ─────────────────────────────────────────────────────────
WARMUP_ROUTINES = [
    "1. Jumping Jacks — 1 min",
    "2. High Knees — 1 min",
    "3. Butt Kicks — 1 min",
    "4. Arm Circles (forward + backward) — 30 sec each",
    "5. Leg Swings — 30 sec each leg",
    "6. Hip Rotations — 30 sec each direction",
    "7. Bodyweight Squats — 15 reps",
    "8. Lunges — 10 each leg",
    "9. Inchworms — 5 reps",
    "10. Light Jog in Place — 1 min",
]


# ─── Cardio Plans ──────────────────────────────────────────────────────────────
CARDIO_PLANS = {
    "beginner": {
        "title": "🟢 Beginner Cardio Plan",
        "exercises": [
            "1. Brisk Walking — 20 min",
            "2. Jumping Jacks — 3×30 sec",
            "3. Step-Ups — 3×1 min",
            "4. Light Cycling — 15 min",
            "5. Cool Down Walk — 5 min",
        ],
        "note": "3-4 days/week. Increase duration gradually."
    },
    "intermediate": {
        "title": "🟡 Intermediate Cardio Plan",
        "exercises": [
            "1. Jogging — 20 min",
            "2. Burpees — 4×10 reps",
            "3. Mountain Climbers — 3×30 sec",
            "4. Jump Rope — 3×2 min",
            "5. High Knees — 3×1 min",
            "6. Cycling — 20 min",
        ],
        "note": "4-5 days/week. Mix steady-state and intervals."
    },
    "advanced": {
        "title": "🔴 Advanced HIIT Cardio Plan",
        "exercises": [
            "1. Sprint Intervals — 10×30 sec sprint / 30 sec rest",
            "2. Box Jumps — 4×12 reps",
            "3. Battle Ropes — 4×30 sec",
            "4. Burpee Tuck Jumps — 3×10 reps",
            "5. Rowing Machine — 10 min intervals",
            "6. Stair Sprints — 5×1 min",
        ],
        "note": "5-6 days/week. Ensure proper recovery."
    },
}


# ─── Daily Challenges ─────────────────────────────────────────────────────────
DAILY_CHALLENGES = [
    "🔥 **100 Push-Up Challenge**: Do 100 push-ups throughout the day in any set size!",
    "🦵 **200 Squat Challenge**: Complete 200 bodyweight squats today!",
    "🏃 **10K Steps Challenge**: Walk at least 10,000 steps today!",
    "💧 **Hydration Challenge**: Drink 4 liters of water today!",
    "🧘 **Flexibility Challenge**: Do 20 minutes of stretching today!",
    "⏱️ **Plank Challenge**: Hold plank for a total of 5 minutes today!",
    "🦾 **50 Burpees Challenge**: Complete 50 burpees throughout the day!",
    "🏋️ **No Equipment Workout**: Do a full 30-min bodyweight workout today!",
    "🥗 **Clean Eating Challenge**: No processed food or sugar for the entire day!",
    "🌅 **Morning Workout Challenge**: Complete your workout before 8 AM!",
    "💤 **Recovery Challenge**: Get 8 hours of sleep tonight and stretch for 15 min!",
    "🏃‍♂️ **HIIT Challenge**: Do 20 minutes of high-intensity interval training!",
    "🧗 **Core Challenge**: 100 crunches + 3 min plank + 50 leg raises today!",
    "💪 **Arm Challenge**: 100 bicep curls + 100 tricep dips throughout the day!",
    "🚶 **Active Recovery**: Walk 5K + 20 min yoga/stretching today!",
]


# ─── Sleep Tips ────────────────────────────────────────────────────────────────
SLEEP_TIPS = [
    "😴 **7-9 Hours**: Adults need 7-9 hours of quality sleep for muscle recovery.",
    "🌙 **Consistent Schedule**: Go to bed and wake up at the same time every day.",
    "📱 **Screen Off**: Avoid screens 1 hour before bed — blue light disrupts melatonin.",
    "🌡️ **Cool Room**: Keep bedroom temperature between 18-20°C (65-68°F).",
    "☕ **No Late Caffeine**: Avoid caffeine at least 6 hours before bedtime.",
    "🍽️ **Light Dinner**: Don't eat heavy meals 2-3 hours before sleeping.",
    "🧘 **Wind Down**: Try meditation, deep breathing, or reading before bed.",
    "💪 **Recovery Matters**: Growth hormone is released during deep sleep — muscles grow while you rest!",
    "🚫 **No Alcohol**: Alcohol disrupts REM sleep and reduces recovery quality.",
    "☀️ **Morning Sunlight**: Get 10-15 min of sunlight after waking to set your circadian rhythm.",
]


# ─── Command Handlers ─────────────────────────────────────────────────────────

@dp.message(Command('start'))
async def welcome(message: types.Message):
    welcome_text = (
        "🏋️‍♂️ *Welcome to FitBot!* 🏋️‍♀️\n\n"
        "I'm your personal AI fitness coach, created by *Akash* 💪\n\n"
        "I can help you with:\n"
        "🔹 Workout plans for any muscle group\n"
        "🔹 BMI, calorie & body fat calculations\n"
        "🔹 Daily water & protein intake\n"
        "🔹 Stretching, warm-up & cardio routines\n"
        "🔹 Sleep & recovery tips\n"
        "🔹 Daily fitness challenges\n"
        "🔹 Nutrition tips & motivation\n"
        "🔹 Any fitness-related questions\n\n"
        "Type /help to see all commands! 🚀"
    )
    await message.answer(welcome_text)


@dp.message(Command('help'))
async def helper(message: types.Message):
    help_text = (
        "📋 *FitBot Commands:*\n\n"
        "*── Basics ──*\n"
        "🏠 /start — Start the bot\n"
        "❓ /help — Show this help menu\n\n"
        "*── Workouts ──*\n"
        "🏋️ /workout `<muscle>` — Get a workout plan\n"
        "    _(chest, back, legs, arms, shoulders, abs, full body)_\n"
        "🏃 /cardio `<level>` — Cardio plan (beginner, intermediate, advanced)\n"
        "� /warmup — Pre-workout warm-up routine\n"
        "🧘 /stretch `<type>` — Stretching routine (morning, post-workout, office)\n\n"
        "*── Calculators ──*\n"
        "�📏 /bmi `<weight_kg>` `<height_cm>` — Calculate BMI\n"
        "🔥 /calories `<weight>` `<height>` `<age>` `<gender>` — Daily calorie needs\n"
        "🍗 /protein `<weight_kg>` — Daily protein intake\n"
        "💧 /water `<weight_kg>` — Daily water intake\n"
        "📊 /bodyfat `<gender>` `<waist_cm>` `<neck_cm>` `<height_cm>` — Body fat %\n\n"
        "*── Daily ──*\n"
        "🥗 /nutrition — Nutrition tips\n"
        "💪 /motivation — Motivation quote\n"
        "💤 /sleep — Sleep & recovery tips\n"
        "🎯 /challenge — Daily fitness challenge\n"
        "🗑️ /clear — Clear conversation context\n\n"
        "*── Tracker ──*\n"
        "🏋️ /log `<exercise> <weight>kg <sets>x<reps>` — Log a gym set\n"
        "    e.g. `/log bench 80kg 3x10`\n"
        "🏃 /run `<dist>km <time>min` — Log a run\n"
        "    e.g. `/run 5km 28min`\n"
        "⚖️ /weight `<kg>` — Log today's body weight\n"
        "    e.g. `/weight 74.5`\n"
        "📋 /today — Today's gym + running log\n"
        "🏃 /runs — Today's runs only\n"
        "📊 /summary — Weekly report + chart\n"
        "📉 /weightlog — 30-day body weight trend\n"
        "🗑 /delete — Clear all your tracker data\n\n"
        "💬 Or just send me any fitness question!"
    )
    await message.answer(help_text)


@dp.message(Command('workout'))
async def workout(message: types.Message, command: CommandObject):
    args = (command.args or "").lower().strip()
    if not args:
        available = ", ".join(WORKOUTS.keys())
        await message.answer(
            f"⚠️ Please specify a muscle group!\n\n"
            f"Usage: `/workout <muscle>`\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return

    plan = WORKOUTS.get(args)
    if not plan:
        available = ", ".join(WORKOUTS.keys())
        await message.answer(
            f"❌ Unknown muscle group: *{args}*\n\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return

    exercises = "\n".join(plan["exercises"])
    response_text = (
        f"{plan['title']}\n"
        f"{'─' * 30}\n"
        f"{exercises}\n"
        f"{'─' * 30}\n"
        f"💡 _Rest 60-90 sec between sets. Stay hydrated!_ 💧"
    )
    await message.answer(response_text)


@dp.message(Command('bmi'))
async def bmi_calculator(message: types.Message, command: CommandObject):
    args = (command.args or "").strip().split()
    if len(args) != 2:
        await message.answer(
            "⚠️ Usage: `/bmi <weight_kg> <height_cm>`\n"
            "Example: `/bmi 70 175`",
            parse_mode="Markdown"
        )
        return

    try:
        weight = float(args[0])
        height_cm = float(args[1])
        height_m = height_cm / 100
        bmi = weight / (height_m ** 2)

        if bmi < 18.5:
            category = "Underweight 🔵"
            tip = "Consider increasing your calorie intake with nutrient-dense foods."
        elif bmi < 25:
            category = "Normal Weight 🟢"
            tip = "Great shape! Maintain your current lifestyle with regular exercise."
        elif bmi < 30:
            category = "Overweight 🟡"
            tip = "Try a calorie deficit diet combined with regular cardio and strength training."
        else:
            category = "Obese 🔴"
            tip = "Consult a healthcare professional and start with low-impact exercises."

        response_text = (
            f"📏 *Your BMI Results:*\n"
            f"{'─' * 30}\n"
            f"⚖️ Weight: {weight} kg\n"
            f"📐 Height: {height_cm} cm\n"
            f"📊 BMI: *{bmi:.1f}*\n"
            f"📋 Category: *{category}*\n"
            f"{'─' * 30}\n"
            f"💡 _{tip}_"
        )
        await message.answer(response_text)

    except ValueError:
        await message.answer("❌ Please enter valid numbers.\nExample: `/bmi 70 175`")


@dp.message(Command('calories'))
async def calorie_calculator(message: types.Message, command: CommandObject):
    args = (command.args or "").strip().split()
    if len(args) != 4:
        await message.answer(
            "⚠️ Usage: `/calories <weight_kg> <height_cm> <age> <gender>`\n"
            "Example: `/calories 70 175 25 male`",
            parse_mode="Markdown"
        )
        return

    try:
        weight = float(args[0])
        height = float(args[1])
        age = int(args[2])
        gender = args[3].lower()

        # Mifflin-St Jeor Equation
        if gender in ("male", "m"):
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        elif gender in ("female", "f"):
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        else:
            await message.answer("❌ Gender should be *male* or *female*.")
            return

        response_text = (
            f"🔥 *Your Daily Calorie Needs:*\n"
            f"{'─' * 30}\n"
            f"⚖️ Weight: {weight} kg | 📐 Height: {height} cm\n"
            f"🎂 Age: {age} | 👤 Gender: {gender.title()}\n"
            f"{'─' * 30}\n"
            f"🛋️ Sedentary: *{bmr * 1.2:.0f}* kcal\n"
            f"🚶 Light Activity: *{bmr * 1.375:.0f}* kcal\n"
            f"🏃 Moderate Activity: *{bmr * 1.55:.0f}* kcal\n"
            f"🏋️ Very Active: *{bmr * 1.725:.0f}* kcal\n"
            f"⚡ Athlete: *{bmr * 1.9:.0f}* kcal\n"
            f"{'─' * 30}\n"
            f"💡 _To lose weight: eat 300-500 kcal below your level._\n"
            f"💡 _To gain muscle: eat 300-500 kcal above your level._"
        )
        await message.answer(response_text)

    except ValueError:
        await message.answer(
            "❌ Please enter valid numbers.\nExample: `/calories 70 175 25 male`",
            parse_mode="Markdown"
        )


@dp.message(Command('nutrition'))
async def nutrition(message: types.Message):
    tips = random.sample(NUTRITION_TIPS, min(5, len(NUTRITION_TIPS)))
    tips_text = "\n\n".join(tips)
    response_text = (
        f"🥗 *Nutrition Tips:*\n"
        f"{'─' * 30}\n\n"
        f"{tips_text}\n\n"
        f"{'─' * 30}\n"
        f"💬 _Ask me any nutrition question for personalized advice!_"
    )
    await message.answer(response_text)


@dp.message(Command('motivation'))
async def motivation(message: types.Message):
    quote = random.choice(MOTIVATION_QUOTES)
    await message.answer(f"🔥 *Daily Motivation:*\n\n{quote}\n\n_Keep pushing! You got this!_ 🚀")


@dp.message(Command('clear'))
async def clear(message: types.Message):
    reference.response = ""
    await message.answer("🗑️ Conversation cleared! Start fresh 💪")


@dp.message(Command('water'))
async def water_intake(message: types.Message, command: CommandObject):
    args = (command.args or "").strip().split()
    if len(args) != 1:
        await message.answer(
            "⚠️ Usage: `/water <weight_kg>`\n"
            "Example: `/water 70`",
            parse_mode="Markdown"
        )
        return
    try:
        weight = float(args[0])
        water_liters = weight * 0.033
        glasses = int(water_liters / 0.25)
        workout_extra = water_liters + 0.5
        response_text = (
            f"💧 *Your Daily Water Intake:*\n"
            f"{'─' * 30}\n"
            f"⚖️ Weight: {weight} kg\n\n"
            f"🥤 Daily Minimum: *{water_liters:.1f} liters* (~{glasses} glasses)\n"
            f"🏋️ On Workout Days: *{workout_extra:.1f} liters*\n"
            f"☀️ Hot Weather: *{water_liters + 0.7:.1f} liters*\n"
            f"{'─' * 30}\n"
            f"💡 _Tips:_\n"
            f"• Drink a glass right after waking up\n"
            f"• Carry a water bottle everywhere\n"
            f"• Drink before you feel thirsty\n"
            f"• Urine should be light yellow"
        )
        await message.answer(response_text)
    except ValueError:
        await message.answer("❌ Please enter a valid number.\nExample: `/water 70`")


@dp.message(Command('protein'))
async def protein_intake(message: types.Message, command: CommandObject):
    args = (command.args or "").strip().split()
    if len(args) != 1:
        await message.answer(
            "⚠️ Usage: `/protein <weight_kg>`\n"
            "Example: `/protein 70`",
            parse_mode="Markdown"
        )
        return
    try:
        weight = float(args[0])
        response_text = (
            f"🍗 *Your Daily Protein Needs:*\n"
            f"{'─' * 30}\n"
            f"⚖️ Weight: {weight} kg\n\n"
            f"🛋️ Sedentary: *{weight * 0.8:.0f}g* (0.8g/kg)\n"
            f"🚶 Light Activity: *{weight * 1.0:.0f}g* (1.0g/kg)\n"
            f"🏋️ Muscle Building: *{weight * 1.6:.0f}-{weight * 2.2:.0f}g* (1.6-2.2g/kg)\n"
            f"🏃 Endurance Athlete: *{weight * 1.2:.0f}-{weight * 1.4:.0f}g* (1.2-1.4g/kg)\n"
            f"🔥 Fat Loss: *{weight * 1.8:.0f}-{weight * 2.4:.0f}g* (1.8-2.4g/kg)\n"
            f"{'─' * 30}\n"
            f"💡 _Protein Sources (per 100g):_\n"
            f"• Chicken breast: 31g\n"
            f"• Eggs (2 large): 12g\n"
            f"• Greek yogurt: 10g\n"
            f"• Lentils: 9g\n"
            f"• Paneer: 18g\n"
            f"• Whey protein scoop: ~25g"
        )
        await message.answer(response_text)
    except ValueError:
        await message.answer("❌ Please enter a valid number.\nExample: `/protein 70`")


@dp.message(Command('bodyfat'))
async def bodyfat_calculator(message: types.Message, command: CommandObject):
    args = (command.args or "").strip().split()
    if len(args) != 4:
        await message.answer(
            "⚠️ Usage: `/bodyfat <gender> <waist_cm> <neck_cm> <height_cm>`\n"
            "Example: `/bodyfat male 85 38 175`",
            parse_mode="Markdown"
        )
        return
    try:
        gender = args[0].lower()
        waist = float(args[1])
        neck = float(args[2])
        height = float(args[3])

        # US Navy Body Fat Formula
        if gender in ("male", "m"):
            bf = 495 / (1.0324 - 0.19077 * math.log10(waist - neck) + 0.15456 * math.log10(height)) - 450
        elif gender in ("female", "f"):
            bf = 495 / (1.29579 - 0.35004 * math.log10(waist + 0 - neck) + 0.22100 * math.log10(height)) - 450
        else:
            await message.answer("❌ Gender should be *male* or *female*.")
            return

        if gender in ("male", "m"):
            if bf < 6: cat = "Essential Fat 🔵"
            elif bf < 14: cat = "Athletic 🟢"
            elif bf < 18: cat = "Fitness 🟢"
            elif bf < 25: cat = "Average 🟡"
            else: cat = "Above Average 🔴"
        else:
            if bf < 14: cat = "Essential Fat 🔵"
            elif bf < 21: cat = "Athletic 🟢"
            elif bf < 25: cat = "Fitness 🟢"
            elif bf < 32: cat = "Average 🟡"
            else: cat = "Above Average 🔴"

        response_text = (
            f"📊 *Body Fat Estimation:*\n"
            f"{'─' * 30}\n"
            f"👤 Gender: {gender.title()}\n"
            f"📏 Waist: {waist} cm | Neck: {neck} cm | Height: {height} cm\n\n"
            f"🎯 Body Fat: *{bf:.1f}%*\n"
            f"📋 Category: *{cat}*\n"
            f"{'─' * 30}\n"
            f"💡 _US Navy method — for best accuracy, measure in the morning._"
        )
        await message.answer(response_text)
    except ValueError:
        await message.answer("❌ Please enter valid numbers.\nExample: `/bodyfat male 85 38 175`")


@dp.message(Command('stretch'))
async def stretch(message: types.Message, command: CommandObject):
    args = (command.args or "").lower().strip()
    if not args:
        available = ", ".join(STRETCHING_ROUTINES.keys())
        await message.answer(
            f"⚠️ Please specify a stretch type!\n\n"
            f"Usage: `/stretch <type>`\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return
    routine = STRETCHING_ROUTINES.get(args)
    if not routine:
        available = ", ".join(STRETCHING_ROUTINES.keys())
        await message.answer(
            f"❌ Unknown stretch type: *{args}*\n\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return
    exercises = "\n".join(routine["exercises"])
    response_text = (
        f"{routine['title']}\n"
        f"{'─' * 30}\n"
        f"{exercises}\n"
        f"{'─' * 30}\n"
        f"💡 _Hold each stretch gently. Never bounce!_ 🧘"
    )
    await message.answer(response_text)


@dp.message(Command('warmup'))
async def warmup(message: types.Message):
    exercises = "\n".join(WARMUP_ROUTINES)
    response_text = (
        f"🔥 *Pre-Workout Warm-Up Routine (10 min)*\n"
        f"{'─' * 30}\n"
        f"{exercises}\n"
        f"{'─' * 30}\n"
        f"💡 _Always warm up before lifting to prevent injuries!_ 🛡️"
    )
    await message.answer(response_text)


@dp.message(Command('cardio'))
async def cardio(message: types.Message, command: CommandObject):
    args = (command.args or "").lower().strip()
    if not args:
        available = ", ".join(CARDIO_PLANS.keys())
        await message.answer(
            f"⚠️ Please specify a level!\n\n"
            f"Usage: `/cardio <level>`\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return
    plan = CARDIO_PLANS.get(args)
    if not plan:
        available = ", ".join(CARDIO_PLANS.keys())
        await message.answer(
            f"❌ Unknown level: *{args}*\n\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return
    exercises = "\n".join(plan["exercises"])
    response_text = (
        f"{plan['title']}\n"
        f"{'─' * 30}\n"
        f"{exercises}\n"
        f"{'─' * 30}\n"
        f"📌 _{plan['note']}_"
    )
    await message.answer(response_text)


@dp.message(Command('sleep'))
async def sleep_tips(message: types.Message):
    tips = random.sample(SLEEP_TIPS, min(5, len(SLEEP_TIPS)))
    tips_text = "\n\n".join(tips)
    response_text = (
        f"😴 *Sleep & Recovery Tips:*\n"
        f"{'─' * 30}\n\n"
        f"{tips_text}\n\n"
        f"{'─' * 30}\n"
        f"💤 _Good sleep = better gains!_"
    )
    await message.answer(response_text)


@dp.message(Command('challenge'))
async def daily_challenge(message: types.Message):
    # Use day of year to give a consistent daily challenge
    day_index = datetime.now().timetuple().tm_yday % len(DAILY_CHALLENGES)
    today_challenge = DAILY_CHALLENGES[day_index]
    random_bonus = random.choice(DAILY_CHALLENGES)
    response_text = (
        f"🎯 *Today's Fitness Challenge:*\n"
        f"{'─' * 30}\n\n"
        f"{today_challenge}\n\n"
        f"{'─' * 30}\n"
        f"🎲 *Bonus Challenge:*\n{random_bonus}\n\n"
        f"_Complete both and you're a legend!_ 🏆"
    )
    await message.answer(response_text)


# ─── Tracker Handlers ────────────────────────────────────────────────────────

@dp.message(Command('log'))
async def log_workout(message: types.Message, command: CommandObject):
    args = (command.args or "").strip().split()
    try:
        weight_token = next(t for t in reversed(args) if "kg" in t.lower())
        sets_reps_token = args[-1]
        w_idx = args.index(weight_token)
        exercise = " ".join(args[:w_idx]).strip()
        weight_kg = float(weight_token.lower().replace("kg", ""))
        sets, reps = map(int, sets_reps_token.lower().split("x"))
        if not exercise:
            raise ValueError
    except Exception:
        await message.answer(
            "❌ Format: `/log <exercise> <weight>kg <sets>x<reps>`\n"
            "Example: `/log bench 80kg 3x10`"
        )
        return
    vol = sets * reps * weight_kg
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO workouts (user_id,date,exercise,sets,reps,weight_kg) VALUES (?,?,?,?,?,?)",
            (message.from_user.id, _today(), exercise, sets, reps, weight_kg)
        )
        conn.commit()
    await message.answer(
        f"✅ Logged *{exercise}*\n"
        f"  {sets}×{reps} @ {weight_kg}kg\n"
        f"  Volume: *{vol:.0f} kg*"
    )


@dp.message(Command('run'))
async def log_run(message: types.Message, command: CommandObject):
    args = (command.args or "").strip().split()
    try:
        dist_token = next(t for t in args if "km" in t.lower())
        dur_token  = next(t for t in args if "min" in t.lower())
        dist = float(dist_token.lower().replace("km", ""))
        dur  = float(dur_token.lower().replace("min", ""))
        if dist <= 0 or dur <= 0:
            raise ValueError
    except Exception:
        await message.answer(
            "❌ Format: `/run <distance>km <duration>min`\n"
            "Example: `/run 5km 28min`"
        )
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO runs (user_id,date,distance_km,duration_min) VALUES (?,?,?,?)",
            (message.from_user.id, _today(), dist, dur)
        )
        conn.commit()
    await message.answer(
        f"🏃 Logged run: *{dist}km* in *{dur}min*\n"
        f"  Pace: _{_pace_str(dist, dur)}_"
    )


@dp.message(Command('today'))
async def today_log(message: types.Message):
    uid = message.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        gym_rows = conn.execute(
            "SELECT exercise,sets,reps,weight_kg FROM workouts WHERE user_id=? AND date=? ORDER BY id",
            (uid, _today())
        ).fetchall()
        run_rows = conn.execute(
            "SELECT distance_km,duration_min FROM runs WHERE user_id=? AND date=? ORDER BY id",
            (uid, _today())
        ).fetchall()

    if not gym_rows and not run_rows:
        await message.answer(
            "No activity today.\nUse `/log` for gym or `/run` for running."
        )
        return

    lines = [f"📋 *Today's Activity ({_today()})*\n"]
    if gym_rows:
        lines.append("🏋️ *Gym:*")
        total_vol = 0
        for ex, s, r, w in gym_rows:
            vol = s * r * w
            total_vol += vol
            lines.append(f"• *{ex}* — {s}×{r} @ {w}kg _(vol: {vol:.0f}kg)_")
        lines.append(f"Total Volume: *{total_vol:.0f} kg*\n")
    if run_rows:
        lines.append("🏃 *Running:*")
        td, tmin = 0.0, 0.0
        for dist, dur in run_rows:
            td += dist; tmin += dur
            lines.append(f"• {dist}km in {dur}min _(pace: {_pace_str(dist, dur)})_")
        lines.append(f"Total: *{td:.1f}km* in *{tmin:.0f}min*  avg pace: _{_pace_str(td, tmin)}_")
    await message.answer("\n".join(lines))


@dp.message(Command('runs'))
async def today_runs(message: types.Message):
    uid = message.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT distance_km,duration_min FROM runs WHERE user_id=? AND date=? ORDER BY id",
            (uid, _today())
        ).fetchall()
    if not rows:
        await message.answer("No runs today. Use `/run 5km 30min` to log one.")
        return
    lines = [f"🏃 *Today's Runs ({_today()})*\n"]
    td, tmin = 0.0, 0.0
    for i, (dist, dur) in enumerate(rows, 1):
        td += dist; tmin += dur
        lines.append(f"• Run {i}: {dist}km in {dur}min _(pace: {_pace_str(dist, dur)})_")
    lines.append(f"\n📊 Total: *{td:.1f}km* in *{tmin:.0f}min*")
    lines.append(f"Avg Pace: _{_pace_str(td, tmin)}_")
    await message.answer("\n".join(lines))


@dp.message(Command('summary'))
async def weekly_summary(message: types.Message):
    uid = message.from_user.id
    gym_rows = _get_week_workouts(uid)
    run_rows  = _get_week_runs(uid)

    # Weekly weight data
    weight_by_date = {}
    with sqlite3.connect(DB_PATH) as conn:
        wt_rows = conn.execute("""
            SELECT date, weight FROM weight_log
            WHERE user_id=? AND date>=?
            ORDER BY date
        """, (uid, _week_since())).fetchall()
    for date, w in wt_rows:
        weight_by_date[date] = w

    if not gym_rows and not run_rows and not wt_rows:
        await message.answer("No activity in the past 7 days. Start with `/log`, `/run`, or `/weight`!")
        return

    by_date     = defaultdict(list)
    by_exercise = defaultdict(float)
    for date, ex, s, r, w in gym_rows:
        vol = s * r * w
        by_date[date].append((ex, s, r, w))
        by_exercise[ex] += vol

    run_by_date = defaultdict(float)
    for date, dist, _ in run_rows:
        run_by_date[date] += dist

    lines = ["📊 *Weekly Summary (last 7 days)*\n"]
    if gym_rows:
        grand_vol = sum(by_exercise.values())
        lines.append(f"🏋️ Gym sessions: *{len(by_date)}*")
        lines.append(f"Total volume: *{grand_vol:.0f} kg*")
        lines.append("\n*Volume by exercise:*")
        for ex, vol in sorted(by_exercise.items(), key=lambda x: -x[1]):
            lines.append(f"  • {ex}: {vol:.0f} kg")
        lines.append("\n*Daily gym breakdown:*")
        for d in sorted(by_date):
            day_vol = sum(s * r * w for _, s, r, w in by_date[d])
            lines.append(f"  📅 {datetime.strptime(d, '%Y-%m-%d').strftime('%a %d %b')} — {day_vol:.0f} kg")

    if run_rows:
        total_dist = sum(r[1] for r in run_rows)
        total_dur  = sum(r[2] for r in run_rows)
        lines.append("\n🏃 *Running:*")
        lines.append(f"  🗺 Distance: *{total_dist:.1f} km*")
        lines.append(f"  ⏱ Time: *{total_dur:.0f} min*")
        lines.append(f"  🚀 Avg Pace: _{_pace_str(total_dist, total_dur)}_")
        for d in sorted(run_by_date):
            lines.append(f"  📅 {datetime.strptime(d, '%Y-%m-%d').strftime('%a %d %b')} — {run_by_date[d]:.1f}km")

    if wt_rows:
        first_w, last_w = wt_rows[0][1], wt_rows[-1][1]
        change = last_w - first_w
        arrow = "📉" if change < 0 else ("📈" if change > 0 else "➡️")
        lines.append("\n⚖️ *Body Weight (this week):*")
        for date, w in wt_rows:
            lines.append(f"  📅 {datetime.strptime(date, '%Y-%m-%d').strftime('%a %d %b')} — *{w} kg*")
        if len(wt_rows) >= 2:
            lines.append(f"\n{arrow} *Weight Change:* {change:+.1f} kg")
            lines.append(f"  Start: {first_w}kg → Now: {last_w}kg")
            if first_w > 0:
                pct = abs(change) / first_w * 100
                direction = "lost" if change < 0 else ("gained" if change > 0 else "maintained")
                lines.append(f"  You {direction} *{pct:.1f}%* of your body weight")

    await message.answer("\n".join(lines))
    if gym_rows:  # Only build chart if there's gym data
        chart = _build_chart(by_date, by_exercise, run_by_date, weight_by_date)
        await message.answer_photo(chart, caption="📈 Your 7-day fitness chart")


@dp.message(Command('delete'))
async def delete_tracker(message: types.Message):
    uid = message.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM workouts WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM runs WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM weight_log WHERE user_id=?", (uid,))
        conn.commit()
    await message.answer("🗑 All your workout, running, and weight data has been deleted.")


@dp.message(Command('weight'))
async def log_weight(message: types.Message, command: CommandObject):
    args = (command.args or "").strip()
    try:
        kg = float(args)
        if kg <= 0 or kg > 500:
            raise ValueError
    except Exception:
        await message.answer(
            "❌ Format: `/weight <kg>`\n"
            "Example: `/weight 74.5`"
        )
        return

    with sqlite3.connect(DB_PATH) as conn:
        # UPSERT — one entry per day
        conn.execute("""
            INSERT INTO weight_log (user_id, date, weight)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET weight=excluded.weight
        """, (message.from_user.id, _today(), kg))
        conn.commit()
    await message.answer(
        f"⚖️ Weight logged: *{kg} kg* on {_today()}\n"
        f"_Use /weightlog to see your trend._"
    )


@dp.message(Command('weightlog'))
async def weight_log_handler(message: types.Message):
    uid = message.from_user.id
    since = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT date, weight FROM weight_log
            WHERE user_id=? AND date>=?
            ORDER BY date
        """, (uid, since)).fetchall()

    if not rows:
        await message.answer(
            "No weight entries yet.\nUse `/weight 74.5` to log today's weight."
        )
        return

    # Text summary
    first_w, last_w = rows[0][1], rows[-1][1]
    change = last_w - first_w
    arrow = "📉" if change < 0 else ("📈" if change > 0 else "➡️")
    lines = ["⚖️ *Body Weight Log (last 30 days)*\n"]
    for date, w in rows:
        day = datetime.strptime(date, "%Y-%m-%d").strftime("%a %d %b")
        lines.append(f"  • {day}: *{w} kg*")
    lines.append(f"\n{arrow} Change: *{change:+.1f} kg* ({rows[0][1]}kg → {rows[-1][1]}kg)")
    await message.answer("\n".join(lines))

    # Line chart
    dates = [r[0] for r in rows]
    weights = [r[1] for r in rows]
    day_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%d %b") for d in dates]

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#0f3460")
    ax.yaxis.label.set_color("white")
    ax.xaxis.label.set_color("white")
    ax.title.set_color("white")

    ax.plot(day_labels, weights, color="#00b4d8", linewidth=2.5, marker="o",
            markersize=6, markerfacecolor="#e94560", markeredgecolor="white", markeredgewidth=1)
    ax.fill_between(range(len(weights)), weights,
                    min(weights) - 0.5, alpha=0.15, color="#00b4d8")
    ax.set_title("Body Weight Trend (last 30 days)", fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel("Weight (kg)")
    ax.set_ylim(min(weights) - 1, max(weights) + 1)

    # Rotate x labels if many entries
    step = max(1, len(day_labels) // 10)
    ax.set_xticks(range(0, len(day_labels), step))
    ax.set_xticklabels(day_labels[::step], rotation=30, ha="right", fontsize=8)

    # Annotate first and last
    ax.annotate(f"{weights[0]}kg", (0, weights[0]),
                textcoords="offset points", xytext=(5, 8),
                color="white", fontsize=8)
    ax.annotate(f"{weights[-1]}kg", (len(weights) - 1, weights[-1]),
                textcoords="offset points", xytext=(-30, 8),
                color="#e94560", fontsize=9, fontweight="bold")

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    await message.answer_photo(buf, caption=f"📉 Weight trend: {first_w}kg → {last_w}kg ({change:+.1f}kg)")


# ─── AI Chat Handler (Fitness Expert) ─────────────────────────────────────────

@dp.message()
async def fitness_chat(message: types.Message):
    """Handles free-text messages with a fitness-expert AI persona."""
    print(f">>> User: \n\t {message.text}")

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": FITNESS_SYSTEM_PROMPT},
                {"role": "assistant", "content": reference.response},
                {"role": "user", "content": message.text},
            ]
        )

        reference.response = response.choices[0].message.content
        print(f">>> FitBot: \n\t{reference.response}")
        await bot.send_message(chat_id=message.chat.id, text=reference.response)

    except Exception as e:
        print(f">>> OpenAI Error: {e}")
        await message.answer(
            "⚠️ AI chat is temporarily unavailable.\n\n"
            "But you can still use all built-in commands!\n"
            "Type /help to see what's available 💪",
            parse_mode="Markdown"
        )


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("🏋️ FitBot is starting...")
    asyncio.run(dp.start_polling(bot))