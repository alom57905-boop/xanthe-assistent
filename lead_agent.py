from agent import Agent
from beauty import instruction 
from pydantic import BaseModel, Field
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_lead(lead, session_id):
    supabase.table("leads").upsert({
        'source': 'Telegram', 
        'chat_id': session_id, 
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

class SaveLeadData(BaseModel):

    name: str = Field(description="Имя", default=None)
    phone: str = Field(description="Телефон", default=None)
    email: str = Field(description="email", default=None)
    city: str = Field(description="Город", default=None)
    niche: str = Field(description="Ниша", default=None)
    service_type: str = Field(description="Услуга", default=None)
    budget: str = Field(description="Бюджет", default=None)
    comment: str = Field(description="краткое описание задачи", default=None)
    consent: bool = Field(description="согласие на обработку персональных данных (true/false)", default=False)

    def process(self, session_id):
        return save_lead(self, session_id)
    
lead_agent = Agent(
    instruction=instruction,
    tools=[SaveLeadData],
)

if __name__ == '__main__':
    
    # print(lead_agent("Здравствуйте, хочу записаться на маникюр, Марина, +7 912 345 67 89 Москва, красота, Маникюр классический, Нужен на следующей неделе, Бюджет до 5000 рублей.").output_text)

    instruction_user = """
    Ты - простой человек, и тебе нужно записаться в салон красоты. 
    Консультант будет задавать тебе вопросы для заполнения заявки.
    На кажды вопрос консультанта отвечай одной фразой. Никогда 
    не продолжай диалог, больше, чем одной фразой. Не пиши реплики от лица консультанта или кого-то другого.
    """

    user = Agent(instruction=instruction_user)

    msg = "Добрый день!"
    for i in range(20):
        print(f"**Посетитель:** {msg}")
        msg = lead_agent(msg).output_text
        print(f"**Консультант:** {msg}")
        msg = user(msg).output_text
        if "До свидания" in msg:
            break