from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text, text
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
    use_cove_verification = Column(Boolean, default=False)
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
    title = Column(String, nullable=True)

    template = relationship("PromptTemplate", back_populates="executions")

Base.metadata.create_all(bind=engine)

# --- Lightweight Migration ---
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE prompt_templates ADD COLUMN use_cove_verification BOOLEAN DEFAULT 0"))
        conn.commit()
    except Exception:
        pass  # Column already exists

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
    use_cove_verification: bool = False
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
    title: str | None = None

class SaveDirectRequest(BaseModel):
    template_id: int
    compiled_prompt: str

class RenameRequest(BaseModel):
    title: str

app = FastAPI(title="Prompt Builder API")

@app.get("/")
def read_root():
    return {"message": "Prompt Builder API is running. Please access the frontend UI at http://localhost:5173"}

# --- Core Logic ---
def compile_prompt_pipeline(data: PromptRequest) -> str:
    """Build a structured base prompt from user configuration."""
    sections = []

    # --- Identity & Persona ---
    if data.role and data.role.strip():
        sections.append(
            f"## Role & Persona\n"
            f"{data.role}\n"
            f"Maintain this role consistently throughout the entire response. "
            f"Your expertise should be evident in terminology, depth of analysis, and professional judgment."
        )

    # --- Context & Constraints ---
    if data.context and data.context.strip():
        sections.append(
            f"## Context & Technical Requirements\n"
            f"{data.context}"
        )

    # --- Task Instructions ---
    if data.task and data.task.strip():
        sections.append(
            f"## Task Instructions\n"
            f"{data.task}\n"
            f"Address every aspect of this task. If the task is ambiguous, state your assumptions explicitly before proceeding."
        )

    # --- Few-Shot Examples ---
    if data.examples:
        example_lines = ["## Examples (Few-Shot)\n"
                         "Follow the pattern demonstrated in these examples precisely:"]
        for i, ex in enumerate(data.examples, 1):
            example_lines.append(
                f"\n**Example {i}:**\n"
                f"- **Input:** {ex.input_text}\n"
                f"- **Expected Output:** {ex.output_text}"
            )
        sections.append("\n".join(example_lines))

    # --- Reasoning Strategy ---
    if data.reasoning_pattern and data.reasoning_pattern != "Zero-Shot":
        if data.reasoning_pattern == "Chain-of-Thought":
            sections.append(
                "## Reasoning Methodology: Chain-of-Thought (CoT)\n"
                "Before providing your final answer, think through the problem step-by-step:\n"
                "1. Identify the core problem or question.\n"
                "2. Break it down into logical sub-problems.\n"
                "3. Reason through each sub-problem sequentially, showing your work.\n"
                "4. Synthesize the sub-conclusions into a final, coherent answer.\n\n"
                "Present your reasoning path clearly before the final output."
            )
        elif data.reasoning_pattern == "Chain-of-Draft":
            sections.append(
                "## Reasoning Methodology: Chain-of-Draft (CoD)\n"
                "Use the Chain-of-Draft method — produce minimal, compressed reasoning steps:\n"
                "1. Each intermediate reasoning step must be **strictly under 5 words**.\n"
                "2. Use shorthand, abbreviations, and symbolic notation where possible.\n"
                "3. Only expand into full prose for the final answer.\n\n"
                "Format: Show the draft chain first, then the complete answer."
            )

    # --- Guardrails ---
    guardrail_items = []

    if data.use_cove_verification:
        guardrail_items.append(
            "### Chain-of-Verification (CoVe)\n"
            "After drafting your response, perform self-verification:\n"
            "1. Extract every factual claim from your response.\n"
            "2. For each claim, generate a targeted verification question.\n"
            "3. Answer each verification question independently.\n"
            "4. Compare the verification answers against your original claims.\n"
            "5. Correct any claims that fail verification before finalizing."
        )

    if data.use_cove:
        guardrail_items.append(
            "### Fact-Check List\n"
            "Conclude your response with a **Fact-Check List** section:\n"
            "- List each key factual claim from your response.\n"
            "- Mark each as ✅ Verified or ⚠️ Needs Review.\n"
            "- Cite the reasoning or source for each verification."
        )

    if guardrail_items:
        sections.append("## Quality Guardrails\n" + "\n\n".join(guardrail_items))

    # --- Output Constraints ---
    constraints = [
        "- No conversational filler or hedging language.",
        "- Be direct, precise, and technically rigorous.",
    ]
    if data.reasoning_pattern == "Chain-of-Draft":
        constraints.append("- Reasoning steps < 5 words each.")
    if data.use_cove:
        constraints.append("- Conclude with a Fact-Check List.")
    if data.use_cove_verification:
        constraints.append("- Include verification step before finalizing.")

    sections.append(
        "## Constraint Summary\n" + "\n".join(constraints)
    )

    return "\n\n".join(sections)


@app.post("/api/compile", response_model=PromptResponse)
async def compile_prompt(request: PromptRequest, db: Session = Depends(get_db)):
    # 1. Save Base Template Configuration
    db_template = PromptTemplate(
        role=request.role,
        context=request.context,
        task=request.task,
        reasoning_pattern=request.reasoning_pattern,
        use_cove=request.use_cove,
        use_cove_verification=request.use_cove_verification,
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

    # 3. Use Gemini to optimize the prompt using a detailed rubric
    improvement_instruction = (
        "You are a world-class Prompt Engineer specializing in LLM optimization.\n\n"
        "## Your Task\n"
        "Transform the raw prompt configuration below into a production-grade, highly effective prompt. "
        "Do NOT answer the prompt — ONLY rewrite and optimize it.\n\n"
        "## Optimization Rubric (apply all that are relevant)\n"
        "1. **Persona Grounding**: Expand the role into specific behavioral constraints — what the persona DOES, "
        "what expertise they apply, and what tone/style they use.\n"
        "2. **Task Decomposition**: If the task is broad, break it into clear numbered sub-tasks "
        "with explicit deliverables for each.\n"
        "3. **Output Format Specification**: Define the exact format the response should follow "
        "(e.g., sections, code blocks, lists, tables). Be prescriptive.\n"
        "4. **Boundary Rules**: Add explicit constraints — what the model should NOT do, "
        "scope limitations, and edge cases to address.\n"
        "5. **Reasoning Integration**: If a reasoning pattern (CoT, CoD) is specified, "
        "weave it naturally into the task flow rather than as a separate appendix.\n"
        "6. **Example Enhancement**: If few-shot examples are provided, frame them as a pattern "
        "the model must follow precisely.\n"
        "7. **Guardrail Embedding**: If verification/fact-checking is requested, make it a mandatory "
        "numbered step in the output process, not just a suggestion.\n"
        "8. **Specificity Injection**: Replace any vague instructions with concrete, measurable criteria.\n\n"
        "## Output Rules\n"
        "- Output ONLY the optimized prompt text.\n"
        "- No meta-commentary, no introductions, no conclusions.\n"
        "- Preserve every constraint, role, task, reasoning pattern, and guardrail from the original.\n"
        "- Use clear Markdown formatting (headers, numbered lists, bold) for readability.\n\n"
        "## Raw Prompt Configuration to Optimize:\n"
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
            is_favorite=exec_log.is_favorite,
            title=exec_log.title
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

@app.patch("/api/prompts/library/{exec_id}/rename")
def rename_library_item(exec_id: int, request: RenameRequest, db: Session = Depends(get_db)):
    db_exec = db.query(ExecutionLog).filter(ExecutionLog.id == exec_id).first()
    if not db_exec:
        raise HTTPException(status_code=404, detail="Item not found")
    db_exec.title = request.title
    db.commit()
    return {"status": "success", "title": db_exec.title}

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
