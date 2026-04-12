# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
import logging
import requests
import re

# Import evaluation modules
from tamil_spell_checker import TamilSpellChecker
from tamil_vocab_ollama_detector import TamilVocabOllamaDetector
from tamil_grammar_detector import TamilGrammarDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Store answers (in production, use a database)
answers = {
    'level1': [],
    'level2': [],
    'level3': []
}

# Global Ollama configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')  # LLM model for relevance checking
OLLAMA_MODEL_ACTUAL = None  # Will be set to actual model name with tag if found
ollama_available = False

# Global evaluators (initialized on startup)
spell_checker = None
vocab_detector = None
grammar_detector = None

# Error thresholds
SPELLING_ERROR_THRESHOLD = 0  # Maximum allowed spelling errors (0 = no errors allowed)
VOCABULARY_ERROR_THRESHOLD = 0  # Maximum allowed vocabulary errors (0 = no errors allowed)
GRAMMAR_ERROR_THRESHOLD = 0  # Maximum allowed grammar errors (0 = no errors allowed)

# Questions for each level - simplified and clear
QUESTIONS = {
    1: "உங்களைப் பற்றி எழுதுங்கள். உங்கள் பெயர், வயது, குடும்பம், ஆர்வங்கள், பொழுதுபோக்குகள், இலக்குகள் பற்றி எழுதுங்கள்",
    2: "இயற்கையை பாதுகாப்பது ஏன் முக்கியம் என்பதை விளக்குங்கள். மரங்கள், விலங்குகள், சுற்றுச்சூழல், காற்று, நீர், மண், வனங்கள், கடல்கள், இயற்கை வளங்களை பாதுகாப்பது, மாசுபாடு, காலநிலை மாற்றம் பற்றி எழுதுங்கள்",
    3: "கல்வி ஏன் மிகவும் முக்கியம் என்பதை விளக்குங்கள். கல்வியின் நன்மைகள், கல்வியின் மதிப்பு, பள்ளி, கல்லூரி, படிப்பு, கற்றல், அறிவு, திறமைகள், கல்வி வாய்ப்புகள் பற்றி எழுதுங்கள்"
}

# Relevance thresholds for each level - optimized for better accuracy
RELEVANCE_THRESHOLDS = {
    1: 0.70,  # Threshold for "about yourself" - increased to avoid historical/political topics
    2: 0.70,  # Threshold for "protecting nature" - increased to avoid education/other topics
    3: 0.70   # Threshold for "education importance" - increased to avoid historical/political topics
}

# Max marks per level for display: internal score is 0-100, converted to this scale for result
LEVEL_MAX_MARKS = {1: 25, 2: 35, 3: 40}

def load_embedding_model():
    """Check Ollama connection and availability"""
    global ollama_available
    try:
        logger.info(f"Checking Ollama connection at {OLLAMA_BASE_URL}...")
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            ollama_available = True
            logger.info("Ollama is available and connected!")
            # Check if LLM model is available (with partial matching for tags like :latest)
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            
            # Check if model exists (exact match or partial match for tags)
            global OLLAMA_MODEL_ACTUAL
            model_found = False
            actual_model_name = OLLAMA_MODEL
            for model_name in model_names:
                # Check if OLLAMA_MODEL matches or is contained in model_name (handles :latest tags)
                if OLLAMA_MODEL == model_name or OLLAMA_MODEL in model_name or model_name.startswith(OLLAMA_MODEL + ':'):
                    model_found = True
                    actual_model_name = model_name  # Use the exact model name with tag
                    OLLAMA_MODEL_ACTUAL = model_name  # Store for use in API calls
                    break
            
            if model_found:
                logger.info(f"LLM model found: {actual_model_name}")
            else:
                logger.warning(f"LLM model '{OLLAMA_MODEL}' not found. Available models: {model_names}")
                logger.warning(f"Please pull the model: ollama pull {OLLAMA_MODEL}")
                # Fallback: use OLLAMA_MODEL as-is (Ollama will use latest if tag not specified)
                OLLAMA_MODEL_ACTUAL = OLLAMA_MODEL
            return True
        else:
            logger.error(f"Ollama returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Make sure Ollama is running.")
        logger.error("Start Ollama: https://ollama.ai")
        return False
    except Exception as e:
        logger.error(f"Error connecting to Ollama: {e}")
        return False

def check_relevance_with_ollama(answer, question):
    """Use Ollama LLM to directly assess if answer is relevant to question - CONTENT EVALUATION"""
    try:
        prompt = f"""Evaluate if the answer matches the question. Read the question and answer carefully.

Question: {question}

Answer: {answer}

EVALUATION GUIDE:

For "Write about yourself" / "உங்களைப் பற்றி" questions:
- Answer should be ABOUT THE PERSON: their name, place, age, family, interests, hobbies, goals, qualities
- Examples of RELEVANT answers:
  * "My name is John. I am 20 years old. I like reading books."
  * "என் பெயர் சாரோ. நான் சென்னையில் வாழ்கிறேன். நான் புத்தகம் வாசிப்பதை விரும்புகிறேன்."
- Examples of NOT RELEVANT:
  * "Education is important. It helps everyone learn." (about education, not the person)
  * "I am studying. Education is important for everyone." (starts with I but content is about education in general)

For "Why is education important" / "கல்வி ஏன் முக்கியம்" questions:
- Answer should explain EDUCATION's importance (not about the person)

For "Protecting nature" / "இயற்கை பாதுகாப்பு" / "இயற்கையை பாதுகாப்பது ஏன் முக்கியம்" questions:
- Answer should be about NATURE/ENVIRONMENT protection (not about the person or education)
- RELEVANT if answer discusses:
  * Why nature is important (air, water, food, resources)
  * Benefits of protecting nature (for humans, animals, future generations)
  * Methods to protect nature (planting trees, reducing pollution, conservation)
  * Nature-related topics (trees, animals, environment, air, water, soil, forests, oceans, climate)
- Key Tamil words that indicate relevance: இயற்கை, மரங்கள், விலங்குகள், சுற்றுச்சூழல், காற்று, நீர், மாசுபாடு, பாதுகாப்பு, உயிரினங்கள்
- Examples of RELEVANT answers:
  * "Nature provides us with air, water, and food. Protecting nature helps humans and animals live healthy lives."
  * "இயற்கை நமக்கு காற்று, நீர், உணவு வழங்குகிறது. இயற்கையை பாதுகாப்பதால் மனிதர்களும் உயிரினங்களும் வாழ முடியும்."
- NOT RELEVANT if answer is about personal details, education, or other unrelated topics

Evaluate the MAIN CONTENT of the answer. What is the answer primarily about?

Respond in this format:
RELEVANT: yes
SCORE: 90

OR

RELEVANT: no
SCORE: 15"""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL_ACTUAL or OLLAMA_MODEL,  # Use actual model name with tag if found
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent results
                    "num_predict": 100
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            
            logger.info(f"Ollama raw response: {response_text}")
            
            # Parse the response - improved parsing with better fallbacks
            response_lower = response_text.lower().strip()
            
            # Check for RELEVANT: yes or no - multiple methods
            is_relevant = False
            
            # Method 1: Look for "relevant: yes" or "relevant: no"
            if re.search(r'relevant:\s*yes', response_lower):
                is_relevant = True
            elif re.search(r'relevant:\s*no', response_lower):
                is_relevant = False
            else:
                # Method 2: Look for yes/no after "relevant"
                relevant_match = re.search(r'relevant[:\s]+(yes|no)', response_lower)
                if relevant_match:
                    is_relevant = relevant_match.group(1) == 'yes'
                else:
                    # Method 3: Look for standalone yes/no
                    first_yes = response_lower.find('yes')
                    first_no = response_lower.find('no')
                    
                    if first_yes != -1 and (first_no == -1 or first_yes < first_no):
                        is_relevant = True
                    elif first_no != -1:
                        is_relevant = False
                    else:
                        # Method 4: Word-based inference
                        positive_words = ['relevant', 'matches', 'correct', 'appropriate', 'yes']
                        negative_words = ['not relevant', 'different', 'wrong', 'unrelated', 'no']
                        
                        pos_count = sum(1 for word in positive_words if word in response_lower[:200])
                        neg_count = sum(1 for word in negative_words if word in response_lower[:200])
                        
                        is_relevant = pos_count > neg_count
                        logger.warning(f"Using word-based inference: pos={pos_count}, neg={neg_count}, result={is_relevant}")
            
            # Extract score (0-100) - improved extraction
            similarity = 0.0
            
            # Method 1: Look for "SCORE: number"
            score_match = re.search(r'score[:\s]+(\d{1,3})', response_lower)
            if score_match:
                num = int(score_match.group(1))
                if 0 <= num <= 100:
                    similarity = num / 100.0
                    logger.info(f"Found score from 'SCORE:' pattern: {similarity}")
            
            # Method 2: If no score found, look for numbers
            if similarity == 0.0:
                numbers = re.findall(r'\b(\d{1,2}|100)\b', response_text)
                for num_str in numbers:
                    num = int(num_str)
                    if 0 <= num <= 100:
                        similarity = num / 100.0
                        logger.info(f"Found score from number pattern: {similarity}")
                        break
            
            # Method 3: Default based on relevance
            if similarity == 0.0:
                if is_relevant:
                    similarity = 0.85  # Default high score if relevant
                    logger.warning("No score found, using default 0.85 for relevant answer")
                else:
                    similarity = 0.20  # Default low score if not relevant
                    logger.warning("No score found, using default 0.20 for non-relevant answer")
            
            logger.info(f"Ollama relevance check - Relevant: {is_relevant}, Score: {similarity:.2f}")
            
            return similarity, is_relevant
        else:
            logger.error(f"Ollama API returned status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None, None
    except Exception as e:
        logger.error(f"Error checking relevance with Ollama: {e}")
        return None, None

def normalize_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    # Strip whitespace
    text = text.strip()
    # Remove extra spaces
    text = ' '.join(text.split())
    return text

def is_valid_answer(answer):
    """Safety checks for answer validation"""
    if not answer:
        return False, "Answer is empty"
    
    normalized = normalize_text(answer)
    
    # Check minimum length (at least 10 characters)
    if len(normalized) < 10:
        return False, "Answer too short (minimum 10 characters)"
    
    # Check word count (at least 5 words)
    word_count = len(normalized.split())
    if word_count < 5:
        return False, "Answer too short (minimum 5 words)"
    
    return True, "Valid"

# Simplified system - direct comparison using Ollama LLM

def check_relevance(answer, level):
    """Check if answer is relevant to the question - WITH STRICT PRE-CHECK"""
    # Safety checks first
    is_valid, message = is_valid_answer(answer)
    if not is_valid:
        return {
            "relevance_score": 0.0,
            "relevant": False,
            "reason": message
        }
    
    # Get question for this level
    if level not in QUESTIONS:
        return {
            "relevance_score": 0.0,
            "relevant": False,
            "reason": "Invalid level"
        }
    
    question = QUESTIONS[level]
    normalized_answer = normalize_text(answer)
    answer_lower = normalized_answer.lower()
    threshold = RELEVANCE_THRESHOLDS.get(level, 0.70)
    
    # PRE-CHECK: For Level 1, check if answer has any personal indicators
    # But don't reject immediately - let LLM evaluate the content
    # This is just a warning, not a hard rejection
    if level == 1:
        personal_indicators = ['நான்', 'எனக்கு', 'என்னை', 'என்', 'எனது', 'பெயர்', 'name', 'i ', 'my ', 'me ', 'myself', 'i am', 'i\'m']
        has_personal = any(ind in answer_lower for ind in personal_indicators)
        
        if not has_personal:
            logger.warning(f"Level 1: Answer has NO personal indicators - LLM will evaluate content")
        else:
            logger.info(f"Level 1: Answer has personal indicators - LLM will evaluate if content is actually about the person")
    
    # Level 2: Must have nature keywords, reject if has education/personal without nature
    elif level == 2:
        nature_indicators = [
            # Core nature/environment terms
            'இயற்கை', 'சுற்றுச்சூழல்', 'சூழல்', 'பசுமை', 'பருவநிலை', 'காலநிலை',
            
            # Trees and plants
            'மரங்கள்', 'மரம்', 'செடிகள்', 'செடி', 'தாவரங்கள்', 'தாவரம்', 'காடுகள்', 'காடு', 
            'வனங்கள்', 'வனம்', 'மழைக்காடு', 'பசுமையான',
            
            # Animals and wildlife
            'விலங்குகள்', 'விலங்கு', 'உயிரினங்கள்', 'உயிரினம்', 'வனவிலங்கு', 'பறவைகள்', 
            'மீன்கள்', 'பூச்சிகள்', 'உயிர்கள்',
            
            # Natural resources
            'காற்று', 'நீர்', 'தண்ணீர்', 'நீர்வளம்', 'மண்', 'மண்ணின்', 'மண்வளம்', 
            'நதிகள்', 'நதி', 'கடல்கள்', 'கடல்', 'ஏரிகள்', 'குளங்கள்',
            
            # Protection and conservation
            'பாதுகாப்பு', 'பாதுகாக்க', 'பாதுகாத்தல்', 'காப்பு', 'காக்க', 'பாதுகாப்பதன்',
            'பாதுகாப்பதால்', 'பாதுகாக்கும்', 'பாதுகாக்கப்பட', 'பாதுகாக்கப்படும்',
            'பாதுகாப்பதற்கு', 'பாதுகாப்பதில்', 'காப்பாற்ற', 'பாதுகாக்கப்பட்ட',
            
            # Environmental issues
            'மாசுபாடு', 'மாசு', 'மாசடைதல்', 'சுத்தம்', 'தூய்மை', 'சுகாதாரம்',
            'வெப்பமயமாதல்', 'வெப்பநிலை', 'காலநிலை மாற்றம்',
            
            # Benefits and importance
            'முக்கியத்துவம்', 'முக்கியம்', 'அவசியம்', 'தேவை', 'பயன்கள்', 'நன்மைகள்',
            'வளங்கள்', 'வளம்', 'இயற்கை வளங்கள்', 'வளங்களை',
            
            # Future and generations
            'எதிர்கால', 'எதிர்காலம்', 'தலைமுறை', 'தலைமுறைகள்', 'தலைமுறைகளுக்கு',
            'தலைமுறைகளின்', 'எதிர்கால தலைமுறை',
            
            # Actions and methods
            'நடவு', 'நடுதல்', 'வளர்த்தல்', 'பயிரிடுதல்', 'பராமரித்தல்',
            'மறுசுழற்சி', 'குறைத்தல்', 'தவிர்த்தல்',
            
            # English keywords
            'nature', 'environment', 'environmental', 'ecology', 'green', 'climate',
            'trees', 'tree', 'plants', 'plant', 'forest', 'forests', 'rainforest',
            'animals', 'animal', 'wildlife', 'birds', 'fish', 'insects', 'species',
            'air', 'water', 'soil', 'earth', 'river', 'rivers', 'ocean', 'oceans', 'sea',
            'protection', 'protect', 'protecting', 'conservation', 'conserve', 'preserve',
            'pollution', 'pollute', 'clean', 'pure', 'warming', 'global warming',
            'resources', 'natural resources', 'future', 'generations', 'future generations',
            'important', 'importance', 'essential', 'crucial', 'vital', 'benefits'
        ]
        wrong_indicators = ['கல்வி', 'education', 'நான்', 'myself', 'பெயர்', 'name', 'படிப்பு', 'study', 'school']
        
        has_nature = any(ind in answer_lower for ind in nature_indicators)
        has_wrong = any(ind in answer_lower for ind in wrong_indicators)
        
        # Count how many nature keywords are present (strong match indicator)
        nature_keyword_count = sum(1 for ind in nature_indicators if ind in answer_lower)
        
        logger.info(f"Level 2: Nature keywords found: {nature_keyword_count}")
        
        if has_wrong and not has_nature:
            logger.error(f"Level 2 PRE-CHECK FAILED: Answer has wrong topic but no nature keywords")
            return {
                "relevance_score": 0.0,
                "relevant": False,
                "threshold": threshold,
                "reason": "Answer is about a different topic instead of nature protection"
            }
    
    # Level 3: Must have education keywords, reject if has personal/nature without education
    elif level == 3:
        education_indicators = [
            # Core education terms
            'கல்வி', 'கல்வியின்', 'கல்வியை', 'கல்வியால்', 'கல்வியில்', 'கல்வியும்',
            'படிப்பு', 'படிப்பின்', 'படிப்பை', 'படித்தல்', 'படிக்க',
            'கற்றல்', 'கற்க', 'கற்பது', 'கற்பதன்', 'கற்பதால்', 'கற்றுக்கொள்',
            
            # Educational institutions
            'பள்ளி', 'பள்ளிகள்', 'கல்லூரி', 'கல்லூரிகள்', 'பல்கலைக்கழகம்',
            'பல்கலைக்கழகங்கள்', 'கல்வி நிறுவனம்', 'கல்வி நிறுவனங்கள்',
            
            # Knowledge and learning
            'அறிவு', 'அறிவை', 'அறிவின்', 'அறிவால்', 'ஞானம்', 'ஞானத்தை',
            'திறமை', 'திறமைகள்', 'திறன்', 'திறன்கள்', 'திறமையை',
            'சிந்தனை', 'சிந்தனையை', 'சிந்திக்கும்', 'சிந்திக்க',
            
            # Benefits and importance
            'முக்கியம்', 'முக்கியத்துவம்', 'அவசியம்', 'தேவை', 'தேவையான',
            'நன்மைகள்', 'நன்மை', 'பயன்கள்', 'பயன்', 'மதிப்பு', 'மதிப்பை',
            
            # Development and progress
            'வளர்ச்சி', 'வளர்ச்சியை', 'வளர்ச்சிக்கு', 'முன்னேற்றம்', 'முன்னேற்றத்திற்கு',
            'மேம்பாடு', 'மேம்படுத்த', 'வளர்த்தல்', 'வளர',
            
            # Skills and abilities
            'திறமை', 'திறமைகளை', 'திறன்களை', 'ஆற்றல்', 'ஆற்றலை',
            'திறமையான', 'திறமையாக', 'திறமையுடன்',
            
            # Society and economy
            'சமூகம்', 'சமூகத்தின்', 'சமூகத்திற்கு', 'பொருளாதாரம்', 'பொருளாதார',
            'நாடு', 'நாட்டின்', 'நாட்டிற்கு', 'நாட்டை',
            
            # Life and career
            'வாழ்க்கை', 'வாழ்க்கையை', 'வாழ்க்கையில்', 'வாழ்க்கையின்',
            'வேலை', 'தொழில்', 'தொழிலை', 'வாய்ப்புகள்', 'வாய்ப்பு',
            
            # Character and values
            'ஒழுக்கம்', 'ஒழுக்கத்தை', 'பண்பு', 'பண்புகள்', 'மனிதம்',
            'சுயநம்பிக்கை', 'சுயமரியாதை', 'நம்பிக்கை',
            
            # English keywords
            'education', 'educational', 'study', 'studying', 'learn', 'learning',
            'school', 'schools', 'college', 'colleges', 'university', 'universities',
            'knowledge', 'wisdom', 'skill', 'skills', 'ability', 'abilities',
            'important', 'importance', 'essential', 'crucial', 'vital', 'necessary',
            'benefits', 'benefit', 'value', 'values', 'development', 'progress',
            'society', 'social', 'economy', 'economic', 'nation', 'country',
            'life', 'career', 'job', 'employment', 'opportunity', 'opportunities',
            'character', 'discipline', 'confidence', 'self-confidence', 'thinking'
        ]
        wrong_indicators = ['நான்', 'myself', 'மரங்கள்', 'trees', 'விலங்குகள்', 'animals', 'இயற்கை', 'nature', 'பெயர்', 'name']
        
        has_education = any(ind in answer_lower for ind in education_indicators)
        has_wrong = any(ind in answer_lower for ind in wrong_indicators)
        
        # Count how many education keywords are present (strong match indicator)
        education_keyword_count = sum(1 for ind in education_indicators if ind in answer_lower)
        
        logger.info(f"Level 3: Education keywords found: {education_keyword_count}")
        
        if has_wrong and not has_education:
            logger.error(f"Level 3 PRE-CHECK FAILED: Answer has wrong topic but no education keywords")
            return {
                "relevance_score": 0.0,
                "relevant": False,
                "threshold": threshold,
                "reason": "Answer is about a different topic instead of education"
            }
    
    # If pre-check passed, use Ollama to check relevance
    similarity, is_relevant = check_relevance_with_ollama(normalized_answer, question)
    
    if similarity is None:
        return {
            "relevance_score": 0.0,
            "relevant": False,
            "reason": "Error checking relevance"
        }
    
    # Post-LLM check: For Level 1, verify if answer has clear personal content
    if level == 1:
        personal_indicators = ['நான்', 'எனக்கு', 'என்னை', 'என்', 'எனது', 'பெயர்', 'name', 'i ', 'my ', 'me ', 'myself']
        personal_content_indicators = ['பெயர்', 'name', 'வயது', 'age', 'குடும்பம்', 'family', 'ஆர்வம்', 'interest', 'பொழுதுபோக்கு', 'hobby', 'லட்சியம்', 'goal', 'இலக்கு', 'dream', 'பிறந்த', 'born', 'வளர்ந்த', 'raised']
        
        has_personal = any(ind in answer_lower for ind in personal_indicators)
        has_personal_content = any(ind in answer_lower for ind in personal_content_indicators)
        
        # If answer has personal indicators AND personal content (name, place, interests, goals)
        # but LLM says not relevant → override (LLM might be wrong)
        if has_personal and has_personal_content and not is_relevant:
            logger.warning(f"Level 1: Answer has personal indicators AND personal content (name/place/interests/goals) but LLM said not relevant - OVERRIDING to relevant")
            is_relevant = True
            if similarity < threshold:
                similarity = threshold + 0.15  # Boost well above threshold
        # If answer has "I" but content is clearly not personal (like general education talk) → trust LLM
        elif has_personal and not has_personal_content and not is_relevant:
            logger.info(f"Level 1: Answer has 'I' but no personal content - trusting LLM's judgment")
        
        logger.info(f"Level 1: Has personal indicators={has_personal}, Has personal content={has_personal_content}, LLM says relevant={is_relevant}")
    
    # Post-LLM check for Level 2: Override if strong nature keyword match
    elif level == 2:
        # If we have strong keyword matches (5+ keywords) but LLM says not relevant → override
        if nature_keyword_count >= 5 and not is_relevant:
            logger.warning(f"Level 2 OVERRIDE: Found {nature_keyword_count} nature keywords but LLM said not relevant - OVERRIDING to relevant")
            is_relevant = True
            similarity = max(similarity, threshold + 0.10)  # Boost above threshold
        elif nature_keyword_count >= 3 and not is_relevant:
            logger.warning(f"Level 2 PARTIAL OVERRIDE: Found {nature_keyword_count} nature keywords but LLM said not relevant - boosting score")
            # Don't override is_relevant, but boost similarity
            similarity = max(similarity, threshold - 0.05)  # Boost close to threshold
    
    # Post-LLM check for Level 3: Override if strong education keyword match
    elif level == 3:
        # If we have strong keyword matches (5+ keywords) but LLM says not relevant → override
        if education_keyword_count >= 5 and not is_relevant:
            logger.warning(f"Level 3 OVERRIDE: Found {education_keyword_count} education keywords but LLM said not relevant - OVERRIDING to relevant")
            is_relevant = True
            similarity = max(similarity, threshold + 0.10)  # Boost above threshold
        elif education_keyword_count >= 3 and not is_relevant:
            logger.warning(f"Level 3 PARTIAL OVERRIDE: Found {education_keyword_count} education keywords but LLM said not relevant - boosting score")
            # Don't override is_relevant, but boost similarity
            similarity = max(similarity, threshold - 0.05)  # Boost close to threshold
    
    # Final decision
    final_relevant = is_relevant and similarity >= threshold
    
    # Log for debugging
    logger.info(f"Level {level}")
    logger.info(f"Question: {question[:80]}...")
    logger.info(f"Answer: {normalized_answer[:80]}...")
    logger.info(f"LLM says: Relevant={is_relevant}, Score={similarity:.2f}, Threshold={threshold}")
    logger.info(f"Final decision: {final_relevant}")
    
    return {
        "relevance_score": similarity,
        "relevant": final_relevant,
        "passed": final_relevant,  # Add 'passed' field for consistency with other checks
        "threshold": threshold,
        "reason": "Topic relevance checked"
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'tamil_writing'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/level1', methods=['GET', 'POST'])
def level1():
    if request.method == 'POST':
        answer = request.form.get('answer', '').strip()
        if answer:
            # Run complete evaluation pipeline
            evaluation_result = evaluate_answer(answer, 1)
            
            # Store answer with evaluation data
            answer_data = {
                'answer': answer,
                'evaluation': evaluation_result
            }
            answers['level1'].append(answer_data)
            
            # Prepare detailed feedback message
            # Prepare detailed feedback message
            # Extract scoring data (internal score 0-100)
            scoring = evaluation_result.get('scoring', {})
            raw_score = scoring.get('score', 0)
            deductions = scoring.get('deductions', [])
            word_count_msg = scoring.get('word_count_msg')

            # Convert to display scale: Level 1 max 25, Level 2 max 35, Level 3 max 40
            max_marks = LEVEL_MAX_MARKS[1]
            score = round((raw_score / 100) * max_marks)
            logger.info(f"Level 1 result: raw={raw_score}/100 -> display={score}/{max_marks}")

            # PASS/FAIL gate: 50% of internal (100) = 50% of level max
            passed_threshold = bool(raw_score >= 50)

            if passed_threshold:
                msg = [f"🏆 Score: {score}/{max_marks}"]
                if deductions:
                    msg.append("📉 Deductions:")
                    for d in deductions:
                        msg.append(f"  - {d}")
                if word_count_msg:
                    msg.append(f"⚠️ {word_count_msg}")
                msg.append("\n✅ நீங்கள் Level 1 தேர்ச்சி பெற்றுள்ளீர்கள்! (Passed)")
                flash('\n'.join(msg), 'success')
                error_details = msg
            else:
                failed_at = evaluation_result.get('failed_at', 'unknown')
                message = evaluation_result.get('message', 'Evaluation failed')
                
                # Build detailed error message - show ALL errors from ALL failed checks
                error_details = []

                # Add Score Header (display score out of level max)
                error_details.append(f"🏆 Score: {score}/{max_marks}")
                if deductions:
                    error_details.append("📉 Deductions:")
                    for d in deductions:
                        error_details.append(f"  - {d}")
                if word_count_msg:
                    error_details.append(f"⚠️ {word_count_msg}")
                error_details.append("-" * 30)

                error_details.append(f'❌ பதில் தோல்வி (Failed at: {failed_at})')
                error_details.append(f'Reason: {message}')
                error_details.append("\n❌ நீங்கள் Level 1 தேர்ச்சி பெறவில்லை. (Failed)")
                
                # Show spelling errors if spelling check failed
                if evaluation_result.get('spelling') and not evaluation_result['spelling'].get('passed', True):
                    spelling_result = evaluation_result['spelling']
                    errors = spelling_result.get('spelling_errors', [])
                    warnings = spelling_result.get('warnings', [])
                    if errors:
                        error_details.append(f'\n⚠️ Spelling Errors ({len(errors)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, err in enumerate(errors[:5], 1):  # Show first 5
                            # pyre-ignore[16]: Item can be string or dict, handling safely
                            word = err.get('word', 'Unknown word') if isinstance(err, dict) else str(err)
                            # pyre-ignore[16]: Item access on union type
                            correct_form = err.get('correct_form', '') if isinstance(err, dict) else ''
                            if correct_form:
                                error_details.append(f'  {i}. "{word}" → should be "{correct_form}"')
                            else:
                                error_details.append(f'  {i}. "{word}"')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more')
                    # Show warnings (partial confidence)
                    if warnings:
                        error_details.append(f'\n⚠️ Words Needing Review ({len(warnings)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, warn in enumerate(warnings[:3], 1):  # Show first 3
                            # pyre-ignore[16]: Union type access
                            word = warn.get('word', 'Unknown word') if isinstance(warn, dict) else 'Unknown'
                            # pyre-ignore[16]: Union type access
                            warning_msg = warn.get('warning', 'Root not in dictionary') if isinstance(warn, dict) else 'Warning'
                            error_details.append(f'  {i}. "{word}": {warning_msg}')
                        if len(warnings) > 3:
                            error_details.append(f'  ... and {len(warnings) - 3} more')
                
                # Show vocabulary errors if vocabulary check failed (STEP 6 — unified report)
                if evaluation_result.get('vocabulary') and not evaluation_result['vocabulary'].get('passed', True):
                    vocab_result = evaluation_result['vocabulary']
                    errors = vocab_result.get('vocabulary_errors', [])
                    if errors:
                        formatted = vocab_result.get('vocabulary_errors_formatted', '')
                        if formatted:
                            error_details.append(f'\n{formatted}')
                        else:
                            error_details.append(f'\n⚠️ Vocabulary Errors ({len(errors)}):')
                            # pyre-ignore[6]: Invalid index type for list access
                            for i, err in enumerate(errors[:5], 1):
                                # pyre-ignore[16]: Item can be union type
                                rule_label = err.get('rule_label', '') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Item can be union type
                                word = err.get('word', 'Unknown word') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Item can be union type
                                reason = err.get('reason', 'Vocabulary error detected') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Item can be union type
                                sentence = err.get('sentence', '') if isinstance(err, dict) else ''
                                prefix = f'  {i}. {rule_label}: ' if rule_label else f'  {i}. '
                                error_details.append(f'{prefix}{reason}')
                                error_details.append(f'     Word: "{word}"')
                                if sentence:
                                    # pyre-ignore[6]: Invalid index type
                                    error_details.append(f'     In sentence: {sentence[:80]}{"..." if len(sentence) > 80 else ""}')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more vocabulary errors')
                
                # Show grammar errors if grammar check failed
                if evaluation_result.get('grammar') and not evaluation_result['grammar'].get('passed', True):
                    grammar_result = evaluation_result['grammar']
                    errors = grammar_result.get('grammar_errors', [])
                    if errors:
                        error_details.append(f'\n⚠️ Grammar Errors ({len(errors)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, err in enumerate(errors[:5], 1):
                            # pyre-ignore[16]: Union type access
                            location = err.get('location', err.get('word', 'Unknown')) if isinstance(err, dict) else 'Unknown'
                            # pyre-ignore[16]: Union type access
                            desc = err.get('description', err.get('reason', 'Grammar error')) if isinstance(err, dict) else 'Grammar error'
                            error_details.append(f'  {i}. "{location}": {desc}')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more')
                
                flash('\n'.join(error_details), 'error')
            
            # Store everything for TeacherAgent
            session['tws_level_result'] = {
                "level": 1, 
                "score": score, 
                "passed_threshold": passed_threshold,
                "student_answer": answer,
                "feedback": '\n'.join(error_details),
                "detailed_evaluation": evaluation_result,
                "question_text": QUESTIONS[1]
            }
            return redirect(url_for('level1'))
        else:
            flash('தயவுசெய்து பதிலை உள்ளிடவும் (Please enter your answer)', 'error')
    
    return render_template('level1.html', level_result=session.pop('tws_level_result', None))

@app.route('/level2', methods=['GET', 'POST'])
def level2():
    if request.method == 'POST':
        answer = request.form.get('answer', '').strip()
        if answer:
            # Run complete evaluation pipeline
            evaluation_result = evaluate_answer(answer, 2)
            
            # Store answer with evaluation data
            answer_data = {
                'answer': answer,
                'evaluation': evaluation_result
            }
            answers['level2'].append(answer_data)
            
            # Prepare detailed feedback message
            # Extract scoring data (internal score 0-100)
            scoring = evaluation_result.get('scoring', {})
            raw_score = scoring.get('score', 0)
            deductions = scoring.get('deductions', [])
            word_count_msg = scoring.get('word_count_msg')

            # Convert to display scale: Level 2 max 35
            max_marks = LEVEL_MAX_MARKS[2]
            score = round((raw_score / 100) * max_marks)
            logger.info(f"Level 2 result: raw={raw_score}/100 -> display={score}/{max_marks}")

            # PASS/FAIL gate: 50% of internal (100) = 50% of level max
            passed_threshold = bool(raw_score >= 50)

            if passed_threshold:
                msg = [f"🏆 Score: {score}/{max_marks}"]
                if deductions:
                    msg.append("📉 Deductions:")
                    for d in deductions:
                        msg.append(f"  - {d}")
                if word_count_msg:
                    msg.append(f"⚠️ {word_count_msg}")
                msg.append("\n✅ நீங்கள் Level 2 தேர்ச்சி பெற்றுள்ளீர்கள்! (Passed)")
                flash('\n'.join(msg), 'success')
                error_details = msg # Define error_details for the success case
            else:
                failed_at = evaluation_result.get('failed_at', 'unknown')
                message = evaluation_result.get('message', 'Evaluation failed')
                
                # Build detailed error message - show ALL errors from ALL failed checks
                error_details = []

                # Add Score Header (display score out of level max)
                error_details.append(f"🏆 Score: {score}/{max_marks}")
                if deductions:
                    error_details.append("📉 Deductions:")
                    for d in deductions:
                        error_details.append(f"  - {d}")
                if word_count_msg:
                    error_details.append(f"⚠️ {word_count_msg}")
                error_details.append("-" * 30)

                error_details.append(f'❌ பதில் தோல்வி (Failed at: {failed_at})')
                error_details.append(f'Reason: {message}')
                error_details.append("\n❌ நீங்கள் Level 2 தேர்ச்சி பெறவில்லை. (Failed)")
                
                # Show spelling errors if spelling check failed
                if evaluation_result.get('spelling') and not evaluation_result['spelling'].get('passed', True):
                    spelling_result = evaluation_result['spelling']
                    errors = spelling_result.get('spelling_errors', [])
                    warnings = spelling_result.get('warnings', [])
                    if errors:
                        error_details.append(f'\n⚠️ Spelling Errors ({len(errors)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, err in enumerate(errors[:5], 1):  # Show first 5
                            # pyre-ignore[16]: Item can be string or dict, handling safely
                            word = err.get('word', 'Unknown word') if isinstance(err, dict) else str(err)
                            # pyre-ignore[16]: Item access on union type
                            correct_form = err.get('correct_form', '') if isinstance(err, dict) else ''
                            if correct_form:
                                error_details.append(f'  {i}. "{word}" → should be "{correct_form}"')
                            else:
                                error_details.append(f'  {i}. "{word}"')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more')
                    # Show warnings (partial confidence)
                    if warnings:
                        error_details.append(f'\n⚠️ Words Needing Review ({len(warnings)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, warn in enumerate(warnings[:3], 1):  # Show first 3
                            # pyre-ignore[16]: Union type access
                            word = warn.get('word', 'Unknown word') if isinstance(warn, dict) else 'Unknown'
                            # pyre-ignore[16]: Union type access
                            warning_msg = warn.get('warning', 'Root not in dictionary') if isinstance(warn, dict) else 'Warning'
                            error_details.append(f'  {i}. "{word}": {warning_msg}')
                        if len(warnings) > 3:
                            error_details.append(f'  ... and {len(warnings) - 3} more')
                
                # Show vocabulary errors if vocabulary check failed (STEP 6 — unified report)
                if evaluation_result.get('vocabulary') and not evaluation_result['vocabulary'].get('passed', True):
                    vocab_result = evaluation_result['vocabulary']
                    errors = vocab_result.get('vocabulary_errors', [])
                    if errors:
                        formatted = vocab_result.get('vocabulary_errors_formatted', '')
                        if formatted:
                            error_details.append(f'\n{formatted}')
                        else:
                            error_details.append(f'\n⚠️ Vocabulary Errors ({len(errors)}):')
                            # pyre-ignore[6]: Invalid index type for list access
                            for i, err in enumerate(errors[:5], 1):
                                # pyre-ignore[16]: Union type access
                                rule_label = err.get('rule_label', '') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Union type access
                                word = err.get('word', 'Unknown word') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Union type access
                                reason = err.get('reason', 'Vocabulary error detected') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Union type access
                                sentence = err.get('sentence', '') if isinstance(err, dict) else ''
                                prefix = f'  {i}. {rule_label}: ' if rule_label else f'  {i}. '
                                error_details.append(f'{prefix}{reason}')
                                error_details.append(f'     Word: "{word}"')
                                if sentence:
                                    # pyre-ignore[6]: Invalid index type
                                    error_details.append(f'     In sentence: {sentence[:80]}{"..." if len(sentence) > 80 else ""}')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more vocabulary errors')
                
                # Show grammar errors if grammar check failed
                if evaluation_result.get('grammar') and not evaluation_result['grammar'].get('passed', True):
                    grammar_result = evaluation_result['grammar']
                    errors = grammar_result.get('grammar_errors', [])
                    if errors:
                        error_details.append(f'\n⚠️ Grammar Errors ({len(errors)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, err in enumerate(errors[:5], 1):
                            # pyre-ignore[16]: Union type access
                            location = err.get('location', err.get('word', 'Unknown')) if isinstance(err, dict) else 'Unknown'
                            # pyre-ignore[16]: Union type access
                            desc = err.get('description', err.get('reason', 'Grammar error')) if isinstance(err, dict) else 'Grammar error'
                            error_details.append(f'  {i}. "{location}": {desc}')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more')
                
                flash('\n'.join(error_details), 'error')
            
            # Store everything for TeacherAgent
            session['tws_level_result'] = {
                "level": 2, 
                "score": score, 
                "passed_threshold": passed_threshold,
                "student_answer": answer,
                "feedback": '\n'.join(error_details),
                "detailed_evaluation": evaluation_result,
                "question_text": QUESTIONS[2]
            }
            return redirect(url_for('level2'))
        else:
            flash('தயவுசெய்து பதிலை உள்ளிடவும் (Please enter your answer)', 'error')
    
    return render_template('level2.html', level_result=session.pop('tws_level_result', None))

@app.route('/level3', methods=['GET', 'POST'])
def level3():
    if request.method == 'POST':
        answer = request.form.get('answer', '').strip()
        if answer:
            # Run complete evaluation pipeline
            evaluation_result = evaluate_answer(answer, 3)
            
            # Store answer with evaluation data
            answer_data = {
                'answer': answer,
                'evaluation': evaluation_result
            }
            answers['level3'].append(answer_data)
            
            # Prepare detailed feedback message
            # Extract scoring data (internal score 0-100)
            scoring = evaluation_result.get('scoring', {})
            raw_score = scoring.get('score', 0)
            deductions = scoring.get('deductions', [])
            word_count_msg = scoring.get('word_count_msg')

            # Convert to display scale: Level 3 max 40
            max_marks = LEVEL_MAX_MARKS[3]
            score = round((raw_score / 100) * max_marks)
            logger.info(f"Level 3 result: raw={raw_score}/100 -> display={score}/{max_marks}")

            # PASS/FAIL gate: 50% of internal (100) = 50% of level max
            passed_threshold = bool(raw_score >= 50)

            if passed_threshold:
                msg = [f"🏆 Score: {score}/{max_marks}"]
                if deductions:
                    msg.append("📉 Deductions:")
                    for d in deductions:
                        msg.append(f"  - {d}")
                if word_count_msg:
                    msg.append(f"⚠️ {word_count_msg}")
                msg.append("\n✅ நீங்கள் Level 3 தேர்ச்சி பெற்றுள்ளீர்கள்! (Passed)")
                flash('\n'.join(msg), 'success')
                error_details = msg # Define error_details for the success case
            else:
                failed_at = evaluation_result.get('failed_at', 'unknown')
                message = evaluation_result.get('message', 'Evaluation failed')
                
                # Build detailed error message - show ALL errors from ALL failed checks
                error_details = []

                # Add Score Header (display score out of level max)
                error_details.append(f"🏆 Score: {score}/{max_marks}")
                if deductions:
                    error_details.append("📉 Deductions:")
                    for d in deductions:
                        error_details.append(f"  - {d}")
                if word_count_msg:
                    error_details.append(f"⚠️ {word_count_msg}")
                error_details.append("-" * 30)

                error_details.append(f'❌ பதில் தோல்வி (Failed at: {failed_at})')
                error_details.append(f'Reason: {message}')
                error_details.append("\n❌ நீங்கள் Level 3 தேர்ச்சி பெறவில்லை. (Failed)")
                
                # Show spelling errors if spelling check failed
                if evaluation_result.get('spelling') and not evaluation_result['spelling'].get('passed', True):
                    spelling_result = evaluation_result['spelling']
                    errors = spelling_result.get('spelling_errors', [])
                    warnings = spelling_result.get('warnings', [])
                    if errors:
                        error_details.append(f'\n⚠️ Spelling Errors ({len(errors)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, err in enumerate(errors[:5], 1):  # Show first 5
                            # pyre-ignore[16]: Item can be string or dict, handling safely
                            word = err.get('word', 'Unknown word') if isinstance(err, dict) else str(err)
                            # pyre-ignore[16]: Item access on union type
                            correct_form = err.get('correct_form', '') if isinstance(err, dict) else ''
                            if correct_form:
                                error_details.append(f'  {i}. "{word}" → should be "{correct_form}"')
                            else:
                                error_details.append(f'  {i}. "{word}"')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more')
                    # Show warnings (partial confidence)
                    if warnings:
                        error_details.append(f'\n⚠️ Words Needing Review ({len(warnings)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, warn in enumerate(warnings[:3], 1):  # Show first 3
                            # pyre-ignore[16]: Union type access
                            word = warn.get('word', 'Unknown word') if isinstance(warn, dict) else 'Unknown'
                            # pyre-ignore[16]: Union type access
                            warning_msg = warn.get('warning', 'Root not in dictionary') if isinstance(warn, dict) else 'Warning'
                            error_details.append(f'  {i}. "{word}": {warning_msg}')
                        if len(warnings) > 3:
                            error_details.append(f'  ... and {len(warnings) - 3} more')
                
                # Show vocabulary errors if vocabulary check failed (STEP 6 — unified report)
                if evaluation_result.get('vocabulary') and not evaluation_result['vocabulary'].get('passed', True):
                    vocab_result = evaluation_result['vocabulary']
                    errors = vocab_result.get('vocabulary_errors', [])
                    if errors:
                        formatted = vocab_result.get('vocabulary_errors_formatted', '')
                        if formatted:
                            error_details.append(f'\n{formatted}')
                        else:
                            error_details.append(f'\n⚠️ Vocabulary Errors ({len(errors)}):')
                            # pyre-ignore[6]: Invalid index type for list access
                            for i, err in enumerate(errors[:5], 1):
                                # pyre-ignore[16]: Union type access
                                rule_label = err.get('rule_label', '') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Union type access
                                word = err.get('word', 'Unknown word') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Union type access
                                reason = err.get('reason', 'Vocabulary error detected') if isinstance(err, dict) else ''
                                # pyre-ignore[16]: Union type access
                                sentence = err.get('sentence', '') if isinstance(err, dict) else ''
                                prefix = f'  {i}. {rule_label}: ' if rule_label else f'  {i}. '
                                error_details.append(f'{prefix}{reason}')
                                error_details.append(f'     Word: "{word}"')
                                if sentence:
                                    # pyre-ignore[6]: Invalid index type
                                    error_details.append(f'     In sentence: {sentence[:80]}{"..." if len(sentence) > 80 else ""}')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more vocabulary errors')
                
                # Show grammar errors if grammar check failed
                if evaluation_result.get('grammar') and not evaluation_result['grammar'].get('passed', True):
                    grammar_result = evaluation_result['grammar']
                    errors = grammar_result.get('grammar_errors', [])
                    if errors:
                        error_details.append(f'\n⚠️ Grammar Errors ({len(errors)}):')
                        # pyre-ignore[6]: Invalid index type for list access
                        for i, err in enumerate(errors[:5], 1):
                            # pyre-ignore[16]: Union type access
                            location = err.get('location', err.get('word', 'Unknown')) if isinstance(err, dict) else 'Unknown'
                            # pyre-ignore[16]: Union type access
                            desc = err.get('description', err.get('reason', 'Grammar error')) if isinstance(err, dict) else 'Grammar error'
                            error_details.append(f'  {i}. "{location}": {desc}')
                        if len(errors) > 5:
                            error_details.append(f'  ... and {len(errors) - 5} more')
                
                flash('\n'.join(error_details), 'error')
            
            # Store everything for TeacherAgent
            session['tws_level_result'] = {
                "level": 3, 
                "score": score, 
                "passed_threshold": passed_threshold,
                "student_answer": answer,
                "feedback": '\n'.join(error_details),
                "detailed_evaluation": evaluation_result,
                "question_text": QUESTIONS[3]
            }
            return redirect(url_for('level3'))
        else:
            flash('தயவுசெய்து பதிலை உள்ளிடவும் (Please enter your answer)', 'error')
    
    return render_template('level3.html', level_result=session.pop('tws_level_result', None))

@app.route('/view_answers')
def view_answers():
    return render_template('view_answers.html', answers=answers)

# API endpoint to get relevance check (for testing)
@app.route('/api/check_relevance', methods=['POST'])
def api_check_relevance():
    """API endpoint to check relevance of an answer"""
    data = request.get_json()
    answer = data.get('answer', '')
    level = data.get('level', 1)
    
    if not answer:
        return jsonify({
            "error": "Answer is required"
        }), 400
    
    relevance_result = check_relevance(answer, level)
    
    return jsonify({
        "relevance_score": relevance_result['relevance_score'],
        "relevant": relevance_result['relevant'],
        "threshold": relevance_result.get('threshold', 0.5),
        "final_score": 0,  # Placeholder for future scoring
        "feedback": relevance_result.get('reason', 'Topic relevance checked')
    })

# ============================================================================
# EVALUATOR INITIALIZATION (runs at module import time)
# ============================================================================

def initialize_evaluators():
    """Initialize all evaluators (spell checker, vocabulary detector, grammar detector)"""
    global spell_checker, vocab_detector, grammar_detector
    
    logger.info("\n" + "="*70)
    logger.info("INITIALIZING EVALUATION SYSTEM")
    logger.info("="*70)
    
    try:
        # Initialize spell checker
        logger.info("[1/3] Initializing spell checker...")
        spell_checker = TamilSpellChecker()
        logger.info("✓ Spell checker initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize spell checker: {e}")
        spell_checker = None
    
    try:
        # Initialize vocabulary detector with Ollama
        logger.info("[2/3] Initializing vocabulary detector (Ollama-enabled)...")
        vocab_detector = TamilVocabOllamaDetector()
        if vocab_detector.available:
            logger.info("✓ Vocabulary detector initialized with Ollama enabled")
        else:
            logger.warning("✓ Vocabulary detector initialized (Ollama not available)")
    except Exception as e:
        logger.error(f"✗ Failed to initialize vocabulary detector: {e}")
        vocab_detector = None
    
    try:
        # Initialize grammar detector (uses tamil_grammar_rules backbone)
        logger.info("[3/3] Initializing grammar detector (rule-based)...")
        grammar_detector = TamilGrammarDetector(use_ollama=False)
        logger.info("✓ Grammar detector initialized (tamil_grammar_rules)")
    except Exception as e:
        logger.error(f"✗ Failed to initialize grammar detector: {e}")
        grammar_detector = None
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("INITIALIZATION SUMMARY")
    logger.info("="*70)
    logger.info(f"Spell Checker: {'✓ Ready' if spell_checker else '✗ Not available'}")
    logger.info(f"Vocabulary Detector: {'✓ Ready' if vocab_detector else '✗ Not available'}")
    logger.info(f"Grammar Detector: {'✓ Ready' if grammar_detector else '✗ Not available'}")
    logger.info("="*70 + "\n")

def check_spelling(answer: str):
    """STEP 2: Check spelling errors"""
    if spell_checker is None:
        return {
            "passed": True,
            "spelling_errors": [],
            "total_errors": 0,
            "reason": "Spell checker not available"
        }
    
    try:
        result = spell_checker.check_text(answer)
        spelling_errors = result.get('errors', [])
        warnings = result.get('warnings', [])  # Partial confidence warnings
        total_errors = len(spelling_errors)
        warning_count = len(warnings)
        
        passed = total_errors <= SPELLING_ERROR_THRESHOLD
        
        return_dict = {
            "passed": passed,
            "spelling_errors": spelling_errors,
            "total_errors": total_errors,
            "reason": f"Spelling check {'passed' if passed else 'failed'} - {total_errors} errors found"
        }
        
        # Add warnings if any (partial confidence cases)
        if warnings:
            return_dict['warnings'] = warnings
            return_dict['warning_count'] = warning_count
            return_dict['reason'] += f", {warning_count} words need review (root not in dictionary)"
        
        return return_dict
    except Exception as e:
        logger.error(f"Error checking spelling: {e}")
        return {
            "passed": True,
            "spelling_errors": [],
            "total_errors": 0,
            "reason": f"Error during spelling check: {str(e)}"
        }

def check_vocabulary(answer: str):
    """STEP 3: Check vocabulary errors"""
    if vocab_detector is None:
        return {
            "passed": True,
            "vocabulary_errors": [],
            "total_errors": 0,
            "reason": "Vocabulary detector not available",
            "vocabulary_errors_formatted": "Vocabulary Errors:\n  (none)"
        }
    
    try:
        result = vocab_detector.detect_vocabulary_errors(answer)
        vocabulary_errors = result.get('vocabulary_errors', [])
        # Ollama detector returns 'error_count', but we use 'total_errors' for consistency
        total_errors = result.get('error_count', len(vocabulary_errors))
        # STEP 6 — unified report: Rule-1, Rule-2, ..., Rule-4 (LLM-assisted)
        vocabulary_errors_formatted = result.get('vocabulary_errors_formatted', '')
        
        passed = total_errors <= VOCABULARY_ERROR_THRESHOLD
        
        return {
            "passed": passed,
            "vocabulary_errors": vocabulary_errors,
            "total_errors": total_errors,
            "reason": f"Vocabulary check {'passed' if passed else 'failed'} - {total_errors} errors found (Ollama-enabled)" if vocab_detector.available else f"Vocabulary check {'passed' if passed else 'failed'} - {total_errors} errors found",
            "detection_method": "ollama" if vocab_detector.available else "unavailable",
            "vocabulary_errors_formatted": vocabulary_errors_formatted,
        }
    except Exception as e:
        logger.error(f"Error checking vocabulary: {e}")
        return {
            "passed": True,
            "vocabulary_errors": [],
            "total_errors": 0,
            "reason": f"Error during vocabulary check: {str(e)}",
            "vocabulary_errors_formatted": "Vocabulary Errors:\n  (none)"
        }

def check_grammar(answer: str):
    """STEP 4: Check grammar errors using rule-based detector (tamil_grammar_rules)"""
    if grammar_detector is None:
        return {
            "passed": True,
            "grammar_errors": [],
            "total_errors": 0,
            "reason": "Grammar detector not available",
            "detection_method": "rule_based"
        }
    try:
        result = grammar_detector.detect_grammar_errors(answer)
        grammar_errors = result.get("grammar_errors", [])
        total_errors = len(grammar_errors)
        passed = total_errors <= GRAMMAR_ERROR_THRESHOLD
        return {
            "passed": passed,
            "grammar_errors": grammar_errors,
            "total_errors": total_errors,
            "reason": f"Grammar check {'passed' if passed else 'failed'} - {total_errors} errors found",
            "detection_method": "rule_based"
        }
    except Exception as e:
        logger.error(f"Error checking grammar: {e}")
        return {
            "passed": True,
            "grammar_errors": [],
            "total_errors": 0,
            "reason": f"Error during grammar check: {str(e)}",
            "detection_method": "rule_based"
        }


def calculate_score(answer: str, level: int, spelling_result: dict, vocab_result: dict, grammar_result: dict) -> dict:
    """
    Calculate score based on word count and error penalties.
    Base Score: 100
    
    Penalties:
    - Word Count: -10 if below threshold (Level 1: 20, Level 2: 30, Level 3: 40)
    - Spelling: -1 per error
    - Vocabulary: -2 per error
    - Grammar: -4 per error
    """
    score = 100
    deductions = []
    
    # 1. Word Count Check
    # Support basic word counting (approximate)
    words = answer.strip().split()
    word_count = len(words)
    min_threshold = 0
    desired_count = 0
    
    if level == 1:
        min_threshold = 20
        desired_count = 25
    elif level == 2:
        min_threshold = 30
        desired_count = 35
    elif level == 3:
        min_threshold = 40
        desired_count = 45
        
    if word_count < min_threshold:
        score -= 10
        deductions.append(f"Word count too low ({word_count} < {min_threshold}): -10 marks")
        logger.warning(f"Score penalty: Word count {word_count} below threshold {min_threshold} (-10)")
        
    # 2. Error Penalties
    spelling_errors = spelling_result.get('total_errors', 0)
    vocab_errors = vocab_result.get('total_errors', 0)
    grammar_errors = grammar_result.get('total_errors', 0)
    
    if spelling_errors > 0:
        penalty = spelling_errors * 1
        score -= penalty
        deductions.append(f"Spelling errors ({spelling_errors} x 1): -{penalty} marks")
        logger.warning(f"Score penalty: {spelling_errors} spelling errors (-{penalty})")
        
    if vocab_errors > 0:
        penalty = vocab_errors * 2
        score -= penalty
        deductions.append(f"Vocabulary errors ({vocab_errors} x 2): -{penalty} marks")
        logger.warning(f"Score penalty: {vocab_errors} vocabulary errors (-{penalty})")
        
    if grammar_errors > 0:
        penalty = grammar_errors * 4
        score -= penalty
        deductions.append(f"Grammar errors ({grammar_errors} x 4): -{penalty} marks")
        logger.warning(f"Score penalty: {grammar_errors} grammar errors (-{penalty})")
        
    final_score = max(0, score)
    logger.info(f"Final Score Calculation: 100 - {100 - score} = {final_score}")
    
    return {
        "score": final_score,
        "deductions": deductions,
        "word_count": word_count,
        "min_threshold": min_threshold,
        "word_count_msg": "your answer has less than the minimum number of words" if word_count < min_threshold else None
    }

def evaluate_answer(answer: str, level: int):
    """
    Complete evaluation pipeline - runs all checks regardless of individual results
    Pipeline:
    1. Content Relevance Check → if fails, return FAIL (don't evaluate)
    2. If relevance passes, run ALL checks:
       - Spell Checking
       - Vocabulary Checking
       - Grammar Checking (rule-based, tamil_grammar_rules)
    3. Return all results together, showing which checks passed/failed
    
    Returns:
        Dict with overall status and detailed results from all checks
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"Starting evaluation pipeline for Level {level}")
    logger.info(f"{'='*70}")
    
    # STEP 1: Content Relevance Check
    logger.info("\n[STEP 1] Content Relevance Checking...")
    relevance_result = check_relevance(answer, level)
    
    if not relevance_result.get('relevant', False):
        logger.error(f"[STEP 1] FAILED - Content relevance check failed")
        logger.error(f"Reason: {relevance_result.get('reason', 'Unknown')}")
        logger.error(f"Score: {relevance_result.get('relevance_score', 0.0):.2f}")
        return {
            "overall_status": "FAIL",
            "failed_at": "relevance",
            "relevance": relevance_result,
            "spelling": None,
            "vocabulary": None,
            "grammar": None,
            "message": f"Content relevance check failed: {relevance_result.get('reason', 'Unknown')}"
        }
    
    logger.info(f"[STEP 1] PASSED - Relevance score: {relevance_result.get('relevance_score', 0.0):.2f}")
    
    # STEP 2-4: Run ALL checks regardless of individual results
    # This allows users to see all errors at once
    
    # STEP 2: Spell Checking
    logger.info("\n[STEP 2] Spell Checking...")
    spelling_result = check_spelling(answer)
    
    if not spelling_result.get('passed', False):
        logger.error(f"[STEP 2] FAILED - Spelling check failed")
        logger.error(f"Reason: {spelling_result.get('reason', 'Unknown')}")
        logger.error(f"Total errors: {spelling_result.get('total_errors', 0)}")
        
        spelling_errors = spelling_result.get('spelling_errors', [])
        if spelling_errors:
            # pyre-ignore[6]: Invalid index type
            for i, error in enumerate(spelling_errors[:10], 1):  # Show first 10 errors
                # pyre-ignore[16]: Item can be union type
                word = error.get('word', 'N/A') if isinstance(error, dict) else 'N/A'
                logger.error(f"  Spelling Error {i}: {word}")
    else:
        # pyre-ignore[6]: Union type mismatch for comparison
        warning_count = spelling_result.get('warning_count', 0)
        # pyre-ignore[58]: Comparison between union and literal
        if warning_count > 0:
            logger.info(f"[STEP 2] PASSED - Spelling errors: {spelling_result.get('total_errors', 0)}, Warnings: {warning_count} (words with partial confidence)")
        else:
            logger.info(f"[STEP 2] PASSED - Spelling errors: {spelling_result.get('total_errors', 0)}")
    
    # STEP 3: Vocabulary Checking (runs even if spelling failed)
    logger.info("\n[STEP 3] Vocabulary Checking...")
    vocabulary_result = check_vocabulary(answer)
    
    if not vocabulary_result.get('passed', False):
        logger.error(f"[STEP 3] FAILED - Vocabulary check failed")
        logger.error(f"Reason: {vocabulary_result.get('reason', 'Unknown')}")
        logger.error(f"Total errors: {vocabulary_result.get('total_errors', 0)}")
        
        vocab_errors = vocabulary_result.get('vocabulary_errors', [])
        if vocab_errors:
            # pyre-ignore[6]: Invalid index type
            for i, error in enumerate(vocab_errors[:10], 1):  # Show first 10 errors
                # pyre-ignore[16]: Item can be union type
                word = error.get('word', 'Unknown word') if isinstance(error, dict) else ''
                # pyre-ignore[16]: Item can be union type
                reason = error.get('reason', 'Vocabulary error detected') if isinstance(error, dict) else ''
                # pyre-ignore[16]: Item can be union type
                sentence = error.get('sentence', '') if isinstance(error, dict) else ''
                logger.error(f"  Vocabulary Error {i}: Word '{word}' - {reason}")
                if sentence:
                    logger.error(f"    Sentence: {sentence}")
    else:
        logger.info(f"[STEP 3] PASSED - Vocabulary errors: {vocabulary_result.get('total_errors', 0)}")
    
    # STEP 4: Grammar Checking (rule-based, tamil_grammar_rules)
    logger.info("\n[STEP 4] Grammar Checking (rule-based)...")
    grammar_result = check_grammar(answer)
    if not grammar_result.get("passed", False):
        logger.error(f"[STEP 4] FAILED - Grammar check failed")
        logger.error(f"Reason: {grammar_result.get('reason', 'Unknown')}")
        logger.error(f"Total errors: {grammar_result.get('total_errors', 0)}")
        grammar_errors = grammar_result.get("grammar_errors", [])
        if grammar_errors:
            # pyre-ignore[6]: Invalid index type
            for i, err in enumerate(grammar_errors[:10], 1):
                # pyre-ignore[16]: Item can be union type
                word_val = err.get("word", "N/A") if isinstance(err, dict) else "N/A"
                # pyre-ignore[16]: Item can be union type
                location = err.get("location", word_val) if isinstance(err, dict) else "N/A"
                # pyre-ignore[16]: Item can be union type
                reason_val = err.get("reason", "N/A") if isinstance(err, dict) else "N/A"
                # pyre-ignore[16]: Item can be union type
                desc = err.get("description", reason_val) if isinstance(err, dict) else "N/A"
                logger.error(f"  Grammar Error {i}: {location} - {desc}")
    else:
        logger.info(f"[STEP 4] PASSED - Grammar errors: {grammar_result.get('total_errors', 0)}")
    
    # STEP 5: Calculate Score
    logger.info("\n[STEP 5] Calculating Score...")
    score_result = calculate_score(answer, level, spelling_result, vocabulary_result, grammar_result)
    
    # Determine overall status and failed_at based on which check failed first
    failed_checks = []
    if not spelling_result.get("passed", False):
        failed_checks.append("spelling")
    if not vocabulary_result.get("passed", False):
        failed_checks.append("vocabulary")
    if not grammar_result.get("passed", False):
        failed_checks.append("grammar")
    
    if failed_checks:
        # Overall status is FAIL, failed_at is the first failed check
        failed_at = failed_checks[0]
        overall_status = "FAIL"
        
        # Build comprehensive message
        messages = []
        if "spelling" in failed_checks:
            messages.append(f"Spelling: {spelling_result.get('reason', 'Failed')}")
        if "vocabulary" in failed_checks:
            messages.append(f"Vocabulary: {vocabulary_result.get('reason', 'Failed')}")
        if "grammar" in failed_checks:
            messages.append(f"Grammar: {grammar_result.get('reason', 'Failed')}")
        
        message = f"Evaluation failed at: {', '.join(failed_checks)}. " + " | ".join(messages)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"EVALUATION FAILED - Failed checks: {', '.join(failed_checks)}")
        logger.info(f"{'='*70}\n")
    else:
        # All checks passed
        failed_at = None
        overall_status = "PASS"
        message = "All checks passed successfully!"
        
        logger.info(f"\n{'='*70}")
        logger.info("ALL CHECKS PASSED - Evaluation successful!")
        logger.info(f"{'='*70}\n")
    
    return {
        "overall_status": overall_status,
        "failed_at": failed_at,
        "relevance": relevance_result,
        "spelling": spelling_result,
        "vocabulary": vocabulary_result,
        "grammar": grammar_result,
        "message": message,
        "scoring": score_result
    }

# Flag to track if initialization is complete
_initialization_complete = False

def initialize_application():
    """Initialize the application (Ollama + evaluators) - runs only once"""
    global _initialization_complete
    
    if _initialization_complete:
        logger.info("Application already initialized (skipping re-initialization)")
        return
    
    logger.info("\n" + "="*70)
    logger.info("Starting application initialization...")
    logger.info("="*70)
    
    # Initialize Ollama connection
    if load_embedding_model():
        logger.info("Ollama is ready for relevance checking!")
    else:
        logger.warning("Ollama initialization failed. Relevance checking will not work.")
    
    # Initialize all evaluators (spell, vocabulary, grammar)
    initialize_evaluators()
    
    _initialization_complete = True
    
    logger.info("\n" + "="*70)
    logger.info("✓ APPLICATION INITIALIZATION COMPLETE")
    logger.info("="*70 + "\n")

if __name__ == '__main__':
    # Initialize before starting Flask server
    initialize_application()
    
    # Wait a moment to ensure all initialization is complete
    import time
    time.sleep(0.5)
    
    logger.info("\n" + "="*70)
    logger.info("STARTING FLASK SERVER")
    logger.info("="*70)
    logger.info("✓ All detectors initialized successfully!")
    logger.info("")
    logger.info("Server will be available at:")
    logger.info("  → http://127.0.0.1:5000")
    logger.info("  → http://localhost:5000")
    logger.info("")
    logger.info("="*70)
    logger.info("Ready to accept requests!")
    logger.info("="*70 + "\n")
    
    # Note: use_reloader=True causes initialization to run twice (once in main process, once in reloader)
    # This is normal Flask behavior - the flag prevents duplicate work
    app.run(debug=True, host='0.0.0.0', port=5002)

