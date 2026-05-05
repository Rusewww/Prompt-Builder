from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)
    context = Column(Text, nullable=False)
    task = Column(Text, nullable=False)
    reasoning_pattern = Column(String, default="Chain-of-Draft")
    use_cove = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    examples = relationship("FewShotExample", back_populates="template", cascade="all, delete-orphan")
    logs = relationship("ExecutionLog", back_populates="template")

class FewShotExample(Base):
    __tablename__ = "few_shot_examples"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id"))
    input_text = Column(Text, nullable=False)
    output_text = Column(Text, nullable=False)

    template = relationship("PromptTemplate", back_populates="examples")

class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id"))
    compiled_prompt = Column(Text, nullable=False)
    llm_response = Column(Text, nullable=True)
    hitl_status = Column(String, default="pending")
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

    template = relationship("PromptTemplate", back_populates="logs")