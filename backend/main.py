from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import asyncio

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

app = FastAPI(title="Prompt Builder API")

# --- Core Logic ---
def compile_prompt_pipeline(data: PromptRequest) -> str:
    prompt = f"Role: {data.role}\n\n"
    prompt += f"Context & Constraints:\n{data.context}\n\n"
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
    # Create DB Template
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

    compiled = compile_prompt_pipeline(request)
    return PromptResponse(template_id=db_template.id, compiled_prompt=compiled)

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_prompt(request: ExecuteRequest, db: Session = Depends(get_db)):
    # Mock LLM Delay
    await asyncio.sleep(1)
    
    mock_response = f"Here is the simulated LLM output for your prompt:\n\n[START OUTPUT]\nI am acting as the requested role.\nHere is the completion for the task...\n[END OUTPUT]"
    
    db_execution = ExecutionLog(
        template_id=request.template_id,
        compiled_prompt=request.compiled_prompt,
        llm_response=mock_response,
        hitl_status="pending"
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)

    return ExecuteResponse(
        execution_id=db_execution.id,
        llm_response=mock_response,
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
    
    new_prompt = db_exec.compiled_prompt + f"\n\nPrevious Response:\n{db_exec.llm_response}\n\nCritique: Analyze your previous response for logical errors and rewrite it."
    
    # Mock delay
    await asyncio.sleep(1)
    refined_response = f"Here is the refined output after critique:\n\n[REFINED OUTPUT]\nCorrected the previous logic...\n[END REFINED OUTPUT]"
    
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