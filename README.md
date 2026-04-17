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
        F[CRNN + CTC - Writing]
        G[Wav2Vec 2.0 - Speaking]
        H[Formant Analyzer - Listening]
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

## 🧩 Core Modules & Architecture

### 1. 📖 Reading Skill Module
Evaluates comprehension through semantic similarity and syntactic accuracy using transformer-based models.

**Architecture:**
```mermaid
graph LR
    Input[Tamil Answer Input] --> BERT[Tamil-BERT-Base Engine]
    BERT --> Semantic[Semantic Similarity Score]
    BERT --> Logic[Logic & Contradiction Check]
    Semantic & Logic --> Teacher[AI Teacher Evaluation]
    Teacher --> Result[Final Reading Score]
```

### 2. ✍️ Writing Skill Module
Uses advanced OCR and Linguistic validation to score handwritten Tamil input.

**Architecture:**
```mermaid
graph TD
    Canvas[Handwriting Digital Canvas] --> Raster[Image Processing]
    Raster --> OCR[CRNN + CTC / ResNet OCR]
    OCR --> Text[Tamil Text Extraction]
    Text --> Lexicon[Lexicon & Spell Checker]
    Lexicon --> Grammar[Grammar Validation Engine]
    Grammar --> FinalScore[Writing Proficiency Score]
```

### 3. 🗣️ Speaking Skill Module
Leverages fine-tuned acoustic models to assess pronunciation, fluency, and phoneme accuracy.

**Architecture:**
```mermaid
graph TD
    Mic[Microphone Input] --> Buff[Audio Buffer Processing]
    Buff --> W2V[Wav2Vec 2.0 Model]
    W2V --> Phoneme[Phoneme Mapping]
    Phoneme --> Match[Reference Signal Alignment]
    Match --> Pron[Pronunciation Score]
```

### 4. 👂 Listening Skill Module
Focuses on phonetic comprehension and audio-visual correlation.

**Architecture:**
```mermaid
graph TD
    Playback[Stimulus Audio Playback] --> User[User Interaction]
    User --> Comp[Comprehension Challenge]
    Comp --> Phonetic[Phonetic Accuracy Engine]
    Phonetic --> Formant[Formant Analysis]
    Formant --> Report[Detailed Listening Report]
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
| **API Layer** | FastAPI, Node.js | Service orchestration and scoring consolidation. |
| **NLP Engine** | Tamil BERT, Ollama (Llama 3) | Semantic analysis and grammar detection. |
| **Vision Engine** | PyTorch, CRNN, CTC Loss | Handwritten Tamil script recognition (OCR). |
| **Audio Engine** | Wav2Vec 2.0, Librosa | Phoneme mapping and audio feature extraction. |
| **Storage** | MongoDB, PostgreSQL | Persistence of profiles and certifications. |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- CUDA-enabled GPU (Highly recommended for OCR and BERT modules)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Saravanan2005real/Tamil-Prouficiency-Assesment-Platform-IITM.git
   cd Tamil-Prouficiency-Assesment-Platform-IITM
   ```

2. **Initialize Submodules**:
   Each module can be run independently using the provided batch/shell scripts:
   - **Reading Module**: `reading skill final one/run.sh`
   - **Writing Module**: `tamil writing skill/app.py`
   - **Speaking Module**: `speaking tamil/START_BACKEND.bat`

---

## 📜 Documentation
Detailed technical specifications for each layer are available in the `/docs` directory and within each module's respective README.

---

**Developed for IIT Madras - Tamil Proficiency Assessment Initiative**