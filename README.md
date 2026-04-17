# 🏆 Unified Tamil Language Proficiency (UTLAP) Platform

![UTLAP Banner](docs/assets/banner.png)

[![Tamil Language](https://img.shields.io/badge/Language-Tamil-blue.svg)](https://en.wikipedia.org/wiki/Tamil_language)
[![Platform](https://img.shields.io/badge/Platform-Assessment-green.svg)](#)
[![Stack](https://img.shields.io/badge/Stack-Python%20%7C%20Node.js%7C%20AI-orange.svg)](#)

A state-of-the-art, multimodal assessment platform designed for **IIT Madras** to evaluate proficiency in the Tamil language. The platform integrates deep learning models for speech, handwriting, and semantic text analysis to provide a comprehensive 4-dimensional evaluation.

---

## 🏗️ Overall System Architecture

The UTLAP platform follows a 4-layer IEEE-standard architecture, ensuring scalability, modularity, and high-performance AI orchestration.

```mermaid
graph TD
    %% Layer 1
    subgraph MIL [Layer 1: Multimodal Interface Layer]
        A[Officer Portal - React/Native]
        B[Admin Interface - Analytics]
        C[Input Modalities - Speech/Pen/Text]
    end

    %% Layer 2
    subgraph AOL [Layer 2: Application Orchestration Layer]
        D[Assessment Orchestrator - API Gateway]
    end

    %% Layer 3
    subgraph ILE [Layer 3: Intelligent Linguistic Engine]
        direction TB
        E[Tamil BERT-NP - Reading]
        F[OCR & Linguistic Detectors - Writing]
        G[Whisper & Wav2Vec 2.0 - Speaking]
        H[Standardized Evaluators - Listening]
        I[AI TEACHER AGENT - Convolutional Reasoning]
    end

    %% Layer 4
    subgraph KML [Layer 4: Knowledge Management Layer]
        J[(Question Bank - QB)]
        K[(User Profile Store)]
        L[(Certificate Repository)]
    end

    %% Connections
    MIL --> AOL
    AOL --> ILE
    ILE --> KML
    
    %% Internal ILE connections
    E & F & G & H --> I
```

---

## 🧩 Module-Specific Architectures

### 1. 📖 Reading Skill Module (LLM-Optimized)
Evaluates comprehension through deep semantic analysis using ultra-high-parameter models.

**Architecture:**
```mermaid
graph TD
    User[Student Answer - Tamil] --> Gate[Input Normalization]
    Passage[Context Passage] & Question[Level Question] & User --> Groq[Groq API - Llama 3.3-70B]
    Groq --> Analysis{Semantic Analysis}
    Analysis --> Valid[Core Meaning Validation]
    Analysis --> Logic[Logic & Contradiction Check]
    Valid & Logic --> Output[JSON Response: Score, Feedback, Reasoning]
    Output --> Synthesis[Integrated Teacher Report Generator]
```

### 2. ✍️ Writing Skill Module (Hybrid Evaluation)
Uses a combination of local linguistic rules and LLM content analysis to score handwritten or typed Tamil.

**Architecture:**
```mermaid
graph TD
    Input[Handwritten/Typed Tamil] --> Clean[Text Normalizer]
    Clean --> Relevance{Topic Relevance Gate}
    Relevance --> LLM[Ollama - Llama 3.2]
    Clean --> Linguistic{Linguistic Detectors}
    Linguistic --> Spell[Tamil Spell Checker]
    Linguistic --> Vocab[Ollama Vocab Detector]
    Linguistic --> Grammar[Grammar Rule Engine]
    LLM & Spell & Vocab & Grammar --> Scoring[Weighted Score Aggregation]
    Scoring --> Threshold{Pass/Fail Gate - 50%}
```

### 3. 🗣️ Speaking Skill Module (Two-Step Assessment)
Leverages a robust multi-stage pipeline to evaluate both the validity of the response and the quality of speech.

**Architecture:**
```mermaid
graph TD
    Audio[Audio Input] --> Whisper[Whisper STT - Tamil]
    Whisper --> Transcript[Tamil Transcript]
    Transcript --> Gate[Step 4: Readiness Gate]
    Gate --> Rel[Ollama Relevance Check]
    Gate --> Suff[Sufficiency & Word Count]
    Rel & Suff --> Skill[Step 5: Skill Assessment]
    Skill --> A[Fluency & Pronunciation - Acoustic]
    Skill --> B[Lexical & Coherence - LLM]
    Skill --> C[Confidence - Statistical]
    A & B & C --> Final[Weighted Overall Score]
```

### 4. 👂 Listening Skill Module (Multi-Metric Diagnostic)
Focuses on standardized correctness across multiple linguistic dimensions.

**Architecture:**
```mermaid
graph TD
    Playback[Audio Stimulus] --> User[User Response]
    User --> Eval[Standardized Evaluator]
    Eval --> Acc[Accuracy Module: MCQ/Matching]
    Eval --> Pre[Precision Module: Exact Order]
    Eval --> Rel[Relevance Module: Semantic Similarity]
    Rel --> LLM[Ollama - Semantic Embedding]
    Acc & Pre & Rel --> Diagn[Learner Level Diagnosis]
    Diagn --> Skill[Beginner / Intermediate / Pro]
```

---

## 🖥️ Visual Preview

![Dashboard Mockup](docs/assets/dashboard.png)
*Figure 1: Unified Assessment Dashboard Mockup*

---

## 🛠️ Technological Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React, HTML5 Canvas, TailwindCSS | User interface and multimodal capture. |
| **STT Engine** | OpenAI Whisper (Tamil) | High-accuracy speech-to-text conversion. |
| **NLP Engine** | Llama 3.3 (Groq), Llama 3.2 (Ollama) | Semantic analysis and topic relevance. |
| **Linguistic Logic** | Custom Python Rule Engines | Grammar, Spelling, and Vocabulary detection. |
| **Audio Analysis** | Librosa, NumPy, Whisper Logprobs | Fluency and Pronunciation metrics. |
| **Storage** | MongoDB, PostgreSQL | Persistence of profiles and certifications. |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- Ollama (running locally with `llama3.2` and `qwen2.5:3b`)
- Groq API Key (for Reading Module)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Saravanan2005real/Tamil-Prouficiency-Assesment-Platform-IITM.git
   ```

2. **Module Execution**:
   Each module can be run independently:
   - **Reading Module**: `reading skill final one/run.sh` (Port 5003)
   - **Writing Module**: `tamil writing skill/app.py` (Port 5000)
   - **Speaking Module**: `speaking tamil/START_BACKEND.bat` (Port 5002)
   - **Listening Module**: `tamil-listening-module/START_BACKEND.bat` (Port 5001)

---

**Developed for IIT Madras - Tamil Proficiency Assessment Initiative**