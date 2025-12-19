from dotenv import load_dotenv
import os
from openai import OpenAI
from pydantic import BaseModel
import json

load_dotenv()

folder_id = os.environ["folder_id"]
api_key = os.environ["api_key"]

model = f"gpt://{folder_id}/aliceai-llm/latest"

client = OpenAI(
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    api_key=api_key,
    project=folder_id
)

class Agent():

    def __init__(self, instruction, tools = [], session_id='default', model=model,tool_choice='auto'):
        self.instruction = instruction
        self.model = model
        self.tool_choice = tool_choice
        self.tool_map = { x.__name__ : x for x in tools if issubclass(x, BaseModel) }
        self.tools = [
            self._create_tool_annot(x) for x in tools
        ]
        self.user_sessions = {}

    def _create_tool_annot(self, x):
        if issubclass(x, BaseModel):
            return {
                "type": "function",
                "name": x.__name__,
                "description": x.__doc__,
                "parameters": x.model_json_schema(),
            }
        else:
            return x

    def __call__(self, message, session_id='default'):
        s = self.user_sessions.get(session_id,{ 'last_reply_id' : None, 'history' : [] })
        s['history'].append({ 'role': 'user', 'content': message })
        res = client.responses.create(
            model = self.model,
            store = True,
            tools = self.tools,
            tool_choice = self.tool_choice,
            instructions = self.instruction,
            previous_response_id = s['last_reply_id'],
            input = message
        )
        # Обрабатываем вызов локальных инструментов
        tool_calls = [item for item in res.output if item.type == "function_call"]
        if tool_calls:
            s['history'].append({ 'role' : 'func_call', 'content' : res.output_text })
            out = []
            for call in tool_calls:
                print(f" + Обрабатываем: {call.name} ({call.arguments})")
                try:
                    fn = self.tool_map[call.name]
                    obj = fn.model_validate(json.loads(call.arguments))
                    result = obj.process(session_id)
                except Exception as e:
                    result = f"Ошибка: {e}"
                print(f" + Результат: {result}")
                out.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": result
                })
                res = client.responses.create(
                    model=self.model,
                    input=out,
                    tools=self.tools,
                    previous_response_id=res.id,
                    store=True
                )
        # Обрабатываем запросы на MCP Approval
        mcp_approve = [ item for item in res.output if item.type == "mcp_approval_request"]
        if mcp_approve:
            res = client.responses.create(
                model=self.model,
                previous_response_id=res.id,
                tools = self.tools,
                input=[{
                    "type": "mcp_approval_response",
                    "approve": True,
                    "approval_request_id": m.id
                }
                for m in mcp_approve
                ])
        s['last_reply_id'] = res.id
        s['history'].append({ 'role' : 'assistant', 'content' : res.output_text })
        self.user_sessions[session_id]=s
        return res

    def history(self, session_id='default'):
        return self.user_sessions[session_id]['history']
