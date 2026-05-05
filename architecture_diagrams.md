# Prompt Builder Assistant Architecture

Here are the visual representations of the database schema and the application's core logic flow, generated using Mermaid diagrams.

## Database Entity-Relationship Diagram

This diagram maps out the SQLite database constructed using SQLAlchemy. It highlights the primary table `prompt_templates` and its one-to-many relationships with `few_shot_examples` and `execution_logs`.

```mermaid
erDiagram
    PROMPT_TEMPLATES {
        int id PK "Primary Key"
        string role "The assigned persona"
        text context "Environmental limits"
        text task "Core instructions"
        string reasoning_pattern "e.g., Chain-of-Draft"
        boolean use_cove "Enable Fact-Check list"
        boolean use_self_refine "Enable refinement loop"
    }
    
    FEW_SHOT_EXAMPLES {
        int id PK "Primary Key"
        int template_id FK "Foreign Key to prompt_templates"
        text input_text "Example input"
        text output_text "Expected output"
    }

    EXECUTION_LOGS {
        int id PK "Primary Key"
        int template_id FK "Foreign Key to prompt_templates"
        text compiled_prompt "The prompt sent to LLM"
        text llm_response "The response from Gemini"
        string hitl_status "pending, approved, rejected_and_refined"
    }

    PROMPT_TEMPLATES ||--o{ FEW_SHOT_EXAMPLES : "contains (1:N)"
    PROMPT_TEMPLATES ||--o{ EXECUTION_LOGS : "tracks (1:N)"
```

## High-Level Project Architecture

This structural flowchart maps out the physical and logical components of the web application, showing how the frontend, backend, database, and external APIs are organized.

```mermaid
flowchart TD
    subgraph Client [Client / Browser]
        subgraph ReactApp [Vite React App]
            App[App.jsx - Root]
            UI[PromptBuilder.jsx]
            S1[Stage 1: Config Form]
            S2[Stage 2: HITL Playground]
            
            App --> UI
            UI --> S1
            UI --> S2
        end
    end

    subgraph Server [Backend Server]
        subgraph FastAPIApp [FastAPI Application]
            Router[API Endpoints]
            Pipeline[Core Logic Pipeline]
            GeminiClient[Gemini HTTP Client]
            
            Router --> Pipeline
            Router --> GeminiClient
        end

        subgraph DBLayer [Data Persistence]
            ORM[SQLAlchemy ORM]
            DB[(SQLite DB)]
            
            ORM --> DB
        end
    end

    subgraph External [External Services]
        Gemini[Google Gemini API]
    end

    %% Network Connections
    ReactApp -- HTTP JSON --> Router
    GeminiClient -- HTTPS POST --> Gemini
    Pipeline --> ORM
    Router --> ORM
    
    %% Styling
    classDef client fill:#E0F7FA,stroke:#006064,stroke-width:2px,color:#006064
    classDef server fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#E65100
    classDef external fill:#EDE7F6,stroke:#4527A0,stroke-width:2px,color:#4527A0
    classDef database fill:#E8F5E9,stroke:#1B5E20,stroke-width:2px,color:#1B5E20

    class ReactApp client
    class FastAPIApp server
    class Gemini external
    class DBLayer database
```
