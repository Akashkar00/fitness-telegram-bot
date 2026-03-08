# How to Create Virtual Environment and Install Dependencies

conda create -n telebot python=3.11 -y

conda activate telebot

pip install -r requirements.txt


## Telegram setup:

1. search for botfather
2. /newbot
   - chatgpt88
   - chatgpt88_bot

   Now click on the url


### AIogram docs
https://docs.aiogram.dev/en/latest/


4. Create a `.env` file in the root directory and add your OpenAI API key and Telegram BOT TOKEN as follows:

```ini
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_BOT_TOKEN=xxxxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

