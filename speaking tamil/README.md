# 🗣️ Tamil Speaking Assessment Module

## 🏗️ Module Architecture

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

## Overview
This module evaluates Tamil pronunciation and fluency using a fine-tuned Wav2Vec 2.0 model. It provides real-time feedback through an AI Teacher Agent.

## Features
- **Wav2Vec 2.0 Integration**: High-accuracy phoneme recognition for Tamil.
- **Formant Analysis**: Detailed acoustic analysis for vowel clarity.
- **Interactive Avatar**: Real-time feedback via a visual teacher agent.

## Setup
Refer to [README_SETUP.md](README_SETUP.md) for detailed installation and execution instructions.
