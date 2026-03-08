import logging
import random
import math
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
import openai
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Config ────────────────────────────────────────────────────────────────────
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot)


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

@dispatcher.message_handler(commands=['start'])
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
    await message.reply(welcome_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['help'])
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
        "� /sleep — Sleep & recovery tips\n"
        "🎯 /challenge — Daily fitness challenge\n"
        "�🗑️ /clear — Clear conversation context\n\n"
        "💬 Or just send me any fitness question!"
    )
    await message.reply(help_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['workout'])
async def workout(message: types.Message):
    args = message.get_args().lower().strip()
    if not args:
        available = ", ".join(WORKOUTS.keys())
        await message.reply(
            f"⚠️ Please specify a muscle group!\n\n"
            f"Usage: `/workout <muscle>`\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return

    plan = WORKOUTS.get(args)
    if not plan:
        available = ", ".join(WORKOUTS.keys())
        await message.reply(
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
    await message.reply(response_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['bmi'])
async def bmi_calculator(message: types.Message):
    args = message.get_args().strip().split()
    if len(args) != 2:
        await message.reply(
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
        await message.reply(response_text, parse_mode="Markdown")

    except ValueError:
        await message.reply("❌ Please enter valid numbers.\nExample: `/bmi 70 175`", parse_mode="Markdown")


@dispatcher.message_handler(commands=['calories'])
async def calorie_calculator(message: types.Message):
    args = message.get_args().strip().split()
    if len(args) != 4:
        await message.reply(
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
            await message.reply("❌ Gender should be *male* or *female*.", parse_mode="Markdown")
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
        await message.reply(response_text, parse_mode="Markdown")

    except ValueError:
        await message.reply(
            "❌ Please enter valid numbers.\nExample: `/calories 70 175 25 male`",
            parse_mode="Markdown"
        )


@dispatcher.message_handler(commands=['nutrition'])
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
    await message.reply(response_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['motivation'])
async def motivation(message: types.Message):
    quote = random.choice(MOTIVATION_QUOTES)
    await message.reply(f"🔥 *Daily Motivation:*\n\n{quote}\n\n_Keep pushing! You got this!_ 🚀", parse_mode="Markdown")


@dispatcher.message_handler(commands=['clear'])
async def clear(message: types.Message):
    reference.response = ""
    await message.reply("🗑️ Conversation cleared! Start fresh 💪", parse_mode="Markdown")


@dispatcher.message_handler(commands=['water'])
async def water_intake(message: types.Message):
    args = message.get_args().strip().split()
    if len(args) != 1:
        await message.reply(
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
        await message.reply(response_text, parse_mode="Markdown")
    except ValueError:
        await message.reply("❌ Please enter a valid number.\nExample: `/water 70`", parse_mode="Markdown")


@dispatcher.message_handler(commands=['protein'])
async def protein_intake(message: types.Message):
    args = message.get_args().strip().split()
    if len(args) != 1:
        await message.reply(
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
        await message.reply(response_text, parse_mode="Markdown")
    except ValueError:
        await message.reply("❌ Please enter a valid number.\nExample: `/protein 70`", parse_mode="Markdown")


@dispatcher.message_handler(commands=['bodyfat'])
async def bodyfat_calculator(message: types.Message):
    args = message.get_args().strip().split()
    if len(args) != 4:
        await message.reply(
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
            await message.reply("❌ Gender should be *male* or *female*.", parse_mode="Markdown")
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
        await message.reply(response_text, parse_mode="Markdown")
    except ValueError:
        await message.reply("❌ Please enter valid numbers.\nExample: `/bodyfat male 85 38 175`", parse_mode="Markdown")


@dispatcher.message_handler(commands=['stretch'])
async def stretch(message: types.Message):
    args = message.get_args().lower().strip()
    if not args:
        available = ", ".join(STRETCHING_ROUTINES.keys())
        await message.reply(
            f"⚠️ Please specify a stretch type!\n\n"
            f"Usage: `/stretch <type>`\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return
    routine = STRETCHING_ROUTINES.get(args)
    if not routine:
        available = ", ".join(STRETCHING_ROUTINES.keys())
        await message.reply(
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
    await message.reply(response_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['warmup'])
async def warmup(message: types.Message):
    exercises = "\n".join(WARMUP_ROUTINES)
    response_text = (
        f"🔥 *Pre-Workout Warm-Up Routine (10 min)*\n"
        f"{'─' * 30}\n"
        f"{exercises}\n"
        f"{'─' * 30}\n"
        f"💡 _Always warm up before lifting to prevent injuries!_ 🛡️"
    )
    await message.reply(response_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['cardio'])
async def cardio(message: types.Message):
    args = message.get_args().lower().strip()
    if not args:
        available = ", ".join(CARDIO_PLANS.keys())
        await message.reply(
            f"⚠️ Please specify a level!\n\n"
            f"Usage: `/cardio <level>`\n"
            f"Available: _{available}_",
            parse_mode="Markdown"
        )
        return
    plan = CARDIO_PLANS.get(args)
    if not plan:
        available = ", ".join(CARDIO_PLANS.keys())
        await message.reply(
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
    await message.reply(response_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['sleep'])
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
    await message.reply(response_text, parse_mode="Markdown")


@dispatcher.message_handler(commands=['challenge'])
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
    await message.reply(response_text, parse_mode="Markdown")


# ─── AI Chat Handler (Fitness Expert) ─────────────────────────────────────────

@dispatcher.message_handler()
async def fitness_chat(message: types.Message):
    """Handles free-text messages with a fitness-expert AI persona."""
    print(f">>> User: \n\t {message.text}")

    try:
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[
                {"role": "system", "content": FITNESS_SYSTEM_PROMPT},
                {"role": "assistant", "content": reference.response},
                {"role": "user", "content": message.text},
            ]
        )

        reference.response = response['choices'][0]['message']['content']
        print(f">>> FitBot: \n\t{reference.response}")
        await bot.send_message(chat_id=message.chat.id, text=reference.response)

    except Exception as e:
        print(f">>> OpenAI Error: {e}")
        await message.reply(
            "⚠️ AI chat is temporarily unavailable.\n\n"
            "But you can still use all built-in commands!\n"
            "Type /help to see what's available 💪",
            parse_mode="Markdown"
        )


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("🏋️ FitBot is starting...")
    executor.start_polling(dispatcher, skip_updates=True)