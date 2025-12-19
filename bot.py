import telebot
from lead_agent import lead_agent
import os
from dotenv import load_dotenv

load_dotenv()

telegram_token = os.environ["tg_token"]

bot = telebot.TeleBot(telegram_token)

sessions = {}

# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start(message):
    session_id = message.chat.id
    print(f"Starting on session {session_id}, msg={message.text}")
    ans = lead_agent(message.text, session_id=session_id)
    bot.send_message(message.chat.id, ans.output_text)


# Обработчик для всех входящих сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    session_id = message.chat.id
    print(f"Answering on session {session_id}, msg={message.text}")
    answer = lead_agent(message.text, session_id=session_id)
    bot.send_message(message.chat.id, answer.output_text)

# Запуск бота
print("Бот готов к работе")
bot.polling(none_stop=True)