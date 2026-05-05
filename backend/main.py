from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

# --- Constants & Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY is not set in the environment.")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

async def call_gemini(prompt: str) -> str:
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(GEMINI_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(part.get("text", "") for part in parts)
                return text
            return "Error: No content generated."
        except Exception as e:
            print("Gemini API Error:", str(e))
            raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./prompt_builder.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    context = Column(Text)
    task = Column(Text)
    reasoning_pattern = Column(String)
    use_cove = Column(Boolean)
    use_self_refine = Column(Boolean, default=False)
    
    examples = relationship("FewShotExample", back_populates="template")
    executions = relationship("ExecutionLog", back_populates="template")

class FewShotExample(Base):
    __tablename__ = "few_shot_examples"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id"))
    input_text = Column(Text)
    output_text = Column(Text)

    template = relationship("PromptTemplate", back_populates="examples")

class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id"))
    compiled_prompt = Column(Text)
    llm_response = Column(Text)
    hitl_status = Column(String) # pending, approved, rejected
    is_favorite = Column(Boolean, default=False)

    template = relationship("PromptTemplate", back_populates="executions")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---
class ExampleSchema(BaseModel):
    input_text: str
    output_text: str

class PromptRequest(BaseModel):
    role: str
    context: str
    task: str
    reasoning_pattern: str
    use_cove: bool
    use_self_refine: bool = False
    examples: List[ExampleSchema] = []

class PromptResponse(BaseModel):
    template_id: int
    compiled_prompt: str

class ExecuteRequest(BaseModel):
    template_id: int
    compiled_prompt: str

class ExecuteResponse(BaseModel):
    execution_id: int
    llm_response: str
    status: str

class RefineRequest(BaseModel):
    execution_id: int

class LibraryItem(BaseModel):
    id: int
    role: str
    task: str
    compiled_prompt: str
    is_favorite: bool

class SaveDirectRequest(BaseModel):
    template_id: int
    compiled_prompt: str

app = FastAPI(title="Prompt Builder API")

@app.get("/")
def read_root():
    return {"message": "Prompt Builder API is running. Please access the frontend UI at http://localhost:5173"}

# --- Core Logic ---
def compile_prompt_pipeline(data: PromptRequest) -> str:
    prompt = ""
    if data.role and data.role.strip():
        prompt += f"Role: {data.role}\n\n"
    if data.context and data.context.strip():
        prompt += f"Context & Constraints:\n{data.context}\n\n"
    if data.task and data.task.strip():
        prompt += f"Task:\n{data.task}\n\n"
    
    if data.examples:
        prompt += "Examples:\n"
        for i, ex in enumerate(data.examples, 1):
            prompt += f"  Example {i} Input: {ex.input_text}\n"
            prompt += f"  Example {i} Output: {ex.output_text}\n"
        prompt += "\n"
    
    if data.reasoning_pattern == "Chain-of-Draft":
        prompt += "Reasoning Strategy: Use Chain-of-Draft. Keep your intermediate reasoning steps strictly under 5 words per step.\n\n"
    elif data.reasoning_pattern == "Chain-of-Thought":
        prompt += "Reasoning Strategy: Think step-by-step.\n\n"
        
    if data.use_cove:
        prompt += "Guardrails: Conclude your response with a discrete Fact-Check List verifying your claims.\n"
        
    return prompt

@app.post("/api/compile", response_model=PromptResponse)
async def compile_prompt(request: PromptRequest, db: Session = Depends(get_db)):
    # 1. Save Base Template Configuration
    db_template = PromptTemplate(
        role=request.role,
        context=request.context,
        task=request.task,
        reasoning_pattern=request.reasoning_pattern,
        use_cove=request.use_cove,
        use_self_refine=request.use_self_refine
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    for ex in request.examples:
        db_example = FewShotExample(template_id=db_template.id, input_text=ex.input_text, output_text=ex.output_text)
        db.add(db_example)
    db.commit()

    # 2. Compile Base Prompt
    base_prompt = compile_prompt_pipeline(request)

    # 3. Use Gemini to Improve the Prompt
    improvement_instruction = (
        "You are an expert AI Architect and Prompt Engineer.\n"
        "Your task is to take the following raw user prompt configuration and improve it into a highly optimized, "
        "professional, and robust prompt ready to be sent to an LLM.\n"
        "CRITICAL RULES:\n"
        "- Do NOT answer the prompt itself, ONLY rewrite it.\n"
        "- Provide STRICTLY the prompt text with no conversational filler, no introductions, and no conclusions. Output ONLY the optimized prompt.\n"
        "- Ensure you maintain all the original constraints, roles, task instructions, and reasoning patterns specified.\n\n"
        "### Raw Prompt Configuration:\n"
        f"{base_prompt}"
    )
    
    improved_prompt = await call_gemini(improvement_instruction)

    return PromptResponse(template_id=db_template.id, compiled_prompt=improved_prompt)

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_prompt(request: ExecuteRequest, db: Session = Depends(get_db)):
    # Use Gemini to generate the real response based on the compiled prompt
    real_response = await call_gemini(request.compiled_prompt)
    
    db_execution = ExecutionLog(
        template_id=request.template_id,
        compiled_prompt=request.compiled_prompt,
        llm_response=real_response,
        hitl_status="pending"
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)

    return ExecuteResponse(
        execution_id=db_execution.id,
        llm_response=real_response,
        status="pending"
    )

@app.post("/api/hitl/approve")
async def approve_execution(execution_id: int, db: Session = Depends(get_db)):
    db_exec = db.query(ExecutionLog).filter(ExecutionLog.id == execution_id).first()
    if not db_exec:
        raise HTTPException(status_code=404, detail="Execution not found")
    db_exec.hitl_status = "approved"
    db.commit()
    return {"status": "success"}

@app.post("/api/refine", response_model=ExecuteResponse)
async def refine_execution(request: RefineRequest, db: Session = Depends(get_db)):
    db_exec = db.query(ExecutionLog).filter(ExecutionLog.id == request.execution_id).first()
    if not db_exec:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    db_exec.hitl_status = "rejected_and_refined"
    
    # Construct the critique prompt
    new_prompt = db_exec.compiled_prompt + f"\n\nPrevious Response:\n{db_exec.llm_response}\n\nCritique: Analyze your previous response for logical errors and rewrite it."
    
    # Use Gemini to generate the refined response
    refined_response = await call_gemini(new_prompt)
    
    db_new_exec = ExecutionLog(
        template_id=db_exec.template_id,
        compiled_prompt=new_prompt,
        llm_response=refined_response,
        hitl_status="pending"
    )
    db.add(db_new_exec)
    db.commit()
    db.refresh(db_new_exec)
    
    return ExecuteResponse(
        execution_id=db_new_exec.id,
        llm_response=refined_response,
        status="pending"
    )

@app.get("/api/prompts/library", response_model=List[LibraryItem])
def get_prompt_library(db: Session = Depends(get_db)):
    # Fetch all approved execution logs
    approved_executions = db.query(ExecutionLog).filter(ExecutionLog.hitl_status == "approved").all()
    
    library = []
    for exec_log in approved_executions:
        template = exec_log.template
        library.append(LibraryItem(
            id=exec_log.id,
            role=template.role if template else "Unknown",
            task=template.task if template else "Unknown",
            compiled_prompt=exec_log.compiled_prompt,
            is_favorite=exec_log.is_favorite
        ))
    
    return library[::-1]

@app.delete("/api/prompts/library/{exec_id}")
def delete_library_item(exec_id: int, db: Session = Depends(get_db)):
    db_exec = db.query(ExecutionLog).filter(ExecutionLog.id == exec_id).first()
    if not db_exec:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_exec)
    db.commit()
    return {"status": "deleted"}

@app.patch("/api/prompts/library/{exec_id}/favorite")
def toggle_favorite(exec_id: int, db: Session = Depends(get_db)):
    db_exec = db.query(ExecutionLog).filter(ExecutionLog.id == exec_id).first()
    if not db_exec:
        raise HTTPException(status_code=404, detail="Item not found")
    db_exec.is_favorite = not db_exec.is_favorite
    db.commit()
    return {"status": "success", "is_favorite": db_exec.is_favorite}

@app.post("/api/prompts/save_direct")
def save_prompt_direct(request: SaveDirectRequest, db: Session = Depends(get_db)):
    db_execution = ExecutionLog(
        template_id=request.template_id,
        compiled_prompt=request.compiled_prompt,
        llm_response="",
        hitl_status="approved",
        is_favorite=False
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)
    return {"status": "success", "execution_id": db_execution.id}
