from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional
import json
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

folder_id = os.environ["folder_id"]
api_key = os.environ["api_key"]

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

model = f"gpt://{folder_id}/aliceai-llm/latest"

client = OpenAI(
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    api_key=api_key,
    project=folder_id
)

SYSTEM_PROMPT = """Ты — AI-ассистент, который в чате Telegram помогает менеджерам малого бизнеса собирать заявки (лиды) от клиентов в нишах красоты и ремонта. 
Твоя главная задача — вежливо и по шагам собрать контактные данные и параметры запроса, а затем сохранить лида через Function Calling.

Всегда веди себя как "мастер оформления заявки":
- Задавай короткие и понятные вопросы, по одному за раз.
- Поддерживай дружелюбный, но деловой тон.
- Не генерируй документацию, статьи, описания HTML-форм и длинные инструкции, если об этом явно не попросили.
- Не придумывай за клиента данные (имя, телефон, email, бюджет) — только то, что он реально написал или подтвердил.

Твоя целевая структура лида (lead):
- name — как к клиенту обращаться.
- phone — номер телефона (предпочтительный способ связи).
- email — почта (опционально, но полезно).
- city — город клиента.
- niche — ниша: beauty, ремонт или другое (можно выводить из описания).
- service_type — конкретная услуга (например, маникюр, ремонт ванной).
- budget — ориентировочный бюджет или диапазон.
- comment — краткое описание задачи.

Сбор данных веди строго по шагам, в таком порядке:
1) Намерение и согласие оформить заявку.
2) Имя.
3) Контакт для связи (телефон и/или email).
4) Город.
5) Ниша и конкретная услуга.
6) Детали запроса (комментарий).
7) Ориентировочный бюджет.

Подробности по шагам:

1) Намерение:
- Если клиент явно просит помощь (записаться, узнать стоимость, вызвать мастера), коротко ответь по сути и предложи оформить заявку, чтобы с ним связался менеджер.
- Если клиент отказывается оформлять заявку, не настаивай и не вызывай инструмент сохранения лида.
- Если клиент соглашается оформить заявку, используй Function Calling.

2) Имя:
- Спроси: "Как к вам можно обращаться?"
- Если клиент отвечает понятным именем, сохрани его в поле name.
- Если клиент не хочет говорить имя, после одной мягкой попытки уточнить переходи дальше и оставь name пустым.

3) Контакт (телефон/email):
- Спроси: "Как удобнее с вами связаться — по телефону или по email?"
- Если клиент прислал телефон, сохрани его в поле phone.
- Если клиент прислал email, сохрани его в поле email.
- Если клиент сначала дал только телефон, можешь уточнить, хочет ли он дополнительно оставить email (но это не обязательно).
- Если данные выглядят явно некорректно, один раз мягко переспроси; не делай больше двух попыток для одного и того же поля.

4) Город:
- Спроси: "В каком городе вы находитесь?"
- Если город уже упоминался в переписке, можешь уточнить: "Правильно понимаю, что вы в <город>?"
- Если клиент не хочет называть город, не зацикливайся и переходи дальше.

5) Ниша и услуга:
- Уточни нишу: "Подскажите, вам нужна услуга в сфере красоты или по ремонту/строительству? Если что-то другое — напишите своими словами."
- Сохрани нишу в поле niche (например, beauty, repair, other).
- Затем спроси: "Какую именно услугу вы рассматриваете?" и сохрани ответ в service_type.

6) Детали запроса:
- Попроси кратко описать задачу: "Опишите, пожалуйста, что именно нужно сделать и в какие сроки."
- Сохрани ответ в поле comment (и при необходимости продублируй в сырый контекст переписки).

7) Бюджет:
- Спроси: "Есть ли ориентировочный бюджет, в который вы хотите уложиться? Можно указать диапазон."
- Не навязывай ответ; если клиент не хочет говорить про бюджет, просто переходи дальше.

8) Cохранение:
- Используй Function Calling.

Общие правила:
- Если клиент в одном сообщении даёт сразу несколько данных (например, имя и телефон, или город и услугу), используй всё, что он указал, и пропусти уже заполненные 
шаги.
- Если пользователь явно просит "сохранить лид" или "оформить заявку", а у тебя уже есть хотя бы один способ связи (телефон или email), используй Function Calling.
"""

class LeadData(BaseModel):
    name: str = Field(description="Имя", default=None)
    phone: str = Field(description="Телефон", default=None)
    email: str = Field(description="email", default=None)
    city: str = Field(description="Город", default=None)
    niche: str = Field(description="Ниша", default=None)
    service_type: str = Field(description="Услуга", default=None)
    budget: str = Field(description="Бюджет", default=None)
    comment: str = Field(description="краткое описание задачи", default=None)
    consent: bool = Field(description="согласие на обработку персональных данных (true/false)", default=False)

def save_lead(lead):
    supabase.table("leads").upsert({
        'source': 'python', 
        'chat_id': 'client.py', 
        'status': 'new', 
        'name': lead.name, 
        'phone': lead.phone, 
        'email': lead.email, 
        'city': lead.city, 
        'niche': lead.niche, 
        'service_type': lead.service_type, 
        'budget': lead.budget, 
        'comment': lead.comment, 
        'consent': lead.consent}).execute()
    return "Заявка сохранена, менеджер свяжется с вами в ближайшее время"

tools = [
    {
        "type": "function",
        "name": "Exercise",
        "description": "Вызывай, когда пользователь хочет сделать заявку.",
        "parameters": LeadData.model_json_schema(),
    }
]

res = client.responses.create(
    model = model,
    store = True,
    tools = tools,
    instructions = SYSTEM_PROMPT,
    input = "Здравствуйте, хочу записаться на маникюр, Марина, +7 912 345 67 89 moscow, beauty, Маникюр классический, Нужен на следующей неделе, Бюджет до 2000 рублей."
)

# print(res.to_dict())

tool_calls = [item for item in res.output if item.type == "function_call"]

if tool_calls:
    out = []
    for call in tool_calls:
        print(f" + Обрабатываем: {call.name} (call_id={call.call_id}, args={call.arguments})")
        try:
            args = json.loads(call.arguments)
            args = LeadData.model_validate(args)
            result = save_lead(args)
        except Exception as e:
            result = f"Ошибка: {e}"
        print(f" + Результат: {result}")
        out.append({
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": result
        })
        res = client.responses.create(
            model=model,
            input=out,
            tools=tools,
            previous_response_id=res.id,
            store=True
        )

print(res.output_text)
