from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Prompt Builder API")

# Pydantic схеми для валідації вхідних даних
class ExampleSchema(BaseModel):
    input_text: str
    output_text: str

class PromptRequest(BaseModel):
    role: str
    context: str
    task: str
    reasoning_pattern: str
    use_cove: bool
    examples: List 

class PromptResponse(BaseModel):
    compiled_prompt: str
    status: str

# Конвеєрний компілятор промпту
def compile_prompt_pipeline(data: PromptRequest) -> str:
    prompt = f"Role: {data.role}\n\n"
    prompt += f"Context & Constraints:\n{data.context}\n\n"
    prompt += f"Task:\n{data.task}\n\n"
    
    # Ін'єкція патерну Few-Shot
    if data.examples:
        prompt += "Examples:\n"
        for i, ex in enumerate(data.examples, 1):
            prompt += f"  Example {i} Input: {ex.input_text}\n"
            prompt += f"  Example {i} Output: {ex.output_text}\n"
        prompt += "\n"
    
    # Ін'єкція патерну міркування для економії токенів
    if data.reasoning_pattern == "Chain-of-Draft":
        prompt += "Reasoning Strategy: Use Chain-of-Draft. Keep your intermediate reasoning steps strictly under 5 words per step.\n\n"
    elif data.reasoning_pattern == "Chain-of-Thought":
        prompt += "Reasoning Strategy: Think step-by-step.\n\n"
        
    # Ін'єкція запобіжника від галюцинацій (CoVe)
    if data.use_cove:
        prompt += "Guardrails: Conclude your response with a discrete Fact-Check List verifying your claims.\n"
        
    return prompt

@app.post("/api/compile", response_model=PromptResponse)
async def create_and_compile_prompt(request: PromptRequest):
    """
    Ендпоінт отримує дані з UI, компілює їх та зупиняє конвеєр
    для перевірки людиною (HITL).
    """
    try:
        compiled = compile_prompt_pipeline(request)
        # Збереження у БД опускається для стислості лістингу
        return PromptResponse(
            compiled_prompt=compiled,
            status="pending_human_review" # Переривання графа
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))