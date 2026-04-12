# LLM-as-a-Judge Setup Guide

The evaluation system now includes an LLM-as-a-judge feature for logical correctness checking of borderline cases (semantic similarity between 0.5-0.75).

## Features

- **Logical Correctness Evaluation**: Uses LLM to evaluate if user answers are logically correct compared to expected answers
- **Tamil Language Support**: Specialized prompts for Tamil language evaluation
- **Borderline Case Handling**: Automatically uses LLM judge when semantic similarity is ambiguous (0.5-0.75)
- **Graceful Fallback**: System continues to work even if LLM is unavailable

## Setup Options

### Option 1: Ollama (Recommended for Local Use)

1. **Install Ollama**: Download from https://ollama.ai/

2. **Pull a Tamil-capable model**:
   ```bash
   ollama pull llama3.1:8b
   # Or use a smaller model:
   ollama pull llama3.1:3b
   ```

3. **Set Environment Variables** (optional, defaults shown):
   ```bash
   # Windows PowerShell
   $env:OLLAMA_URL="http://localhost:11434"
   $env:OLLAMA_MODEL="llama3.1:8b"
   
   # Linux/Mac
   export OLLAMA_URL="http://localhost:11434"
   export OLLAMA_MODEL="llama3.1:8b"
   ```

4. **Start Ollama** (if not running as service):
   ```bash
   ollama serve
   ```

### Option 2: OpenAI API

1. **Get API Key**: Sign up at https://platform.openai.com/

2. **Set Environment Variables**:
   ```bash
   # Windows PowerShell
   $env:OPENAI_API_KEY="your-api-key-here"
   $env:OPENAI_MODEL="gpt-3.5-turbo"  # or "gpt-4"
   
   # Linux/Mac
   export OPENAI_API_KEY="your-api-key-here"
   export OPENAI_MODEL="gpt-3.5-turbo"
   ```

## How It Works

1. **Primary Evaluation**: Uses `paraphrase-multilingual-MiniLM-L12-v2` for fast semantic similarity
2. **Borderline Detection**: When similarity is 0.5-0.75, LLM judge is called
3. **Logical Checking**: LLM evaluates:
   - Logical correctness (not just semantic similarity)
   - Key idea presence
   - Negation/opposition detection
   - Tamil language nuances
4. **Decision**: If LLM confidence >= 0.6, its judgment is used; otherwise falls back to semantic similarity

## When LLM Judge is Used

- **Short Answer Questions (Q1)**: Borderline semantic similarity (0.5-0.75)
- **Long Answer Questions (Q3, Q4)**: Borderline semantic similarity (0.5-0.75)
- **All Question Types**: When primary evaluation is uncertain

## Fallback Behavior

If LLM is unavailable:
- System continues to work normally
- Uses semantic similarity thresholds as fallback
- No errors or crashes

## Testing

Test if LLM judge is available:
```python
from evaluator import _init_llm_judge, _llm_judge_logical_correctness

_init_llm_judge()

# Test with a sample
is_correct, confidence, reasoning = _llm_judge_logical_correctness(
    user_answer="பயனரின் பதில்",
    correct_answer="சரியான பதில்",
    question_text="கேள்வி"
)
print(f"Correct: {is_correct}, Confidence: {confidence}, Reasoning: {reasoning}")
```

## Troubleshooting

**LLM not detected:**
- Check if Ollama is running: `curl http://localhost:11434/api/tags`
- Check environment variables are set correctly
- For OpenAI: Verify API key is valid

**Slow evaluation:**
- Use a smaller model (e.g., `llama3.1:3b` instead of `llama3.1:8b`)
- LLM judge only activates for borderline cases, so most evaluations remain fast

**JSON parse errors:**
- Model might not be following JSON format strictly
- System will fallback to semantic similarity automatically

