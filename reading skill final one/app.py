#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Backend API for Tamil Reading Assessment Website
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import requests
import json
from functools import lru_cache

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import Tamil modules
# Removed local module imports as we are moving to Llama-exclusive evaluation

def get_ollama_config() -> tuple[str, str]:
    """Returns (base_url, model_name) for Ollama."""
    base_url = "http://localhost:11434"
    model_name = "llama3" # Defaulting to llama3 as per user's "llama model" request
    return base_url, model_name

def parse_json_from_text(text: str) -> dict:
    """Extracts JSON from text, handling potential Markdown formatting."""
    if not text: return {}
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Find start and end of JSON block
        json_content = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                if not in_block: in_block = True
                else: break
            elif in_block:
                json_content.append(line)
        text = "\n".join(json_content)
    
    try:
        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        return json.loads(text)
    except: return {}

def evaluate_with_llama(passage, question, user_answer, expected_answers):
    """Evaluates the user's answer using Groq AI (Llama-3.3-70B) for high accuracy."""
    api_key = "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"
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = f"""
    You are an expert Tamil language teacher. Your goal is to verify if a student TRULY read and understood the provided passage.
    
    TAMIL PASSAGE:
    {passage}
    
    QUESTION:
    {question}
    
    CORE CORRECT CONCEPTS (FOR REFERENCE):
    {", ".join(expected_answers)}
    
    STUDENT'S ANSWER:
    {user_answer}
    
    GRADING RULES:
    1. CORE MEANING IS KING: If the student's answer contains the core truth or fact required by the question (even if hidden in a long sentence), they MUST PASS.
    2. BE LENIENT AND TEACHER-LIKE: The student is learning. Do NOT penalize for wordiness, repeating the question in the answer, or using slightly different phrasing than the reference.
    3. IGNORE ALL ERRORS: Ignore spelling mistakes, punctuation, grammar, script variations, or mixed English/Tamil if the meaning is clear.
    4. FACTUAL CONSISTENCY: As long as the answer is factually correct according to the passage, it is 100% correct.
    
    SCORING:
    - If the core truth is present: "passed": true, "marks": 1, "finalScore": 1.0.
    - If the answer is factually wrong or completely unrelated: "passed": false, "marks": 0, "finalScore": 0.0.
    
    RETURN ONLY A VALID JSON OBJECT:
    {{
      "passed": boolean,
      "marks": number,
      "finalScore": number,
      "feedback": "Encouraging Tamil feedback (1 sentence)",
      "reasoning": "Brief English explanation of why this is correct/wrong"
    }}
    """

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a professional Tamil teacher grading reading assessments. You are encouraging and look for understanding rather than exact matching."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1, # Lower temperature for consistency
            "max_tokens": 500
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        raw_output = data['choices'][0]['message']['content']
        return parse_json_from_text(raw_output)
    except Exception as e:
        print(f"Groq Evaluation Error: {e}")
        return {"error": str(e)}

app = Flask(__name__, static_folder='static', static_url_path='')
# Highly permissive CORS for local development across multiple modules
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Passage sets for three levels
PASSAGES = {
    'basic': {
        'id': 'basic',
        'level': 'Basic',
        'title': 'Alarm Clock Habit',
        'paragraph': {
            'tamil': """ரமேஷ் தினமும் பள்ளிக்கு தாமதமாகச் செல்வான். எத்தனை தடவை அம்மா அழைத்தாலும், அவன் காலை எழுந்திருக்கவே மாட்டான். ஒரு நாள், ரமேஷின் அப்பா ஒரு புதிய அலாரம் கடிகாரத்தை வாங்கி கொடுத்தார். அது ஒவ்வொரு நாளும் காலை 6.00 மணிக்கு கூர்மையான சத்தத்துடன் ஒலிக்கும். முதல் நாளில், அலாரம் ஒலிக்கும்போது ரமேஷ் பயந்து எழுந்தான். ஆனால் சில நாட்களிலேயே அவன் அந்தச் சத்தத்துக்கு பழகிவிட்டான். அலாரம் ஒலித்தவுடன் படுக்கையைச் சீர்செய்து, முகம் கழுவி, நேரத்துக்கு பள்ளிக்குச் செல்வது அவனுக்கு ஒரு பழக்கமாகிவிட்டது. ஒரு வாரத்துக்குள் ஆசிரியரும் ரமேஷின் மாற்றத்தை கவனித்தார். "ரமேஷ், இந்த வாரம் நீ ஒருநாளும் தாமதமாகவில்லை!" என்று பாராட்டினார். அதைக் கேட்ட ரமேஷ் பெருமைப்பட, அலாரம் கடிகாரத்தை தனது 'சிறந்த உதவியாளர்' என்று சொல்லிக் கொண்டான்.""",
            'english': """Ramesh used to go to school late every day. No matter how many times his mother called him, he would not wake up in the morning. One day, Ramesh's father bought him a new alarm clock. It would ring sharply at 6:00 AM every morning. On the first day, when the alarm rang, Ramesh woke up frightened. But within a few days, he got used to that sound. After the alarm rang, making the bed, washing his face, and going to school on time became a habit for him. Within a week, the teacher also noticed Ramesh's change. "Ramesh, you haven't been late even once this week!" he praised. Hearing this, Ramesh felt proud and called the alarm clock his 'best helper'."""
        },
        'questions': {
            1: {
                'text_tamil': 'ரமேஷ் தினமும் எந்த பிரச்சனையை சந்தித்தான்?',
                'text_english': 'What problem did Ramesh face every day?',
                'marks': 1
            },
            2: {
                'text_tamil': 'ரமேஷின் அப்பா அவனுக்கு என்ன வாங்கித் தந்தார்?',
                'text_english': "What did Ramesh's father buy for him?",
                'marks': 1
            },
            3: {
                'text_tamil': 'ரமேஷின் மாற்றத்தை முதலில் யார் கவனித்தார்?',
                'text_english': "Who noticed Ramesh's change first?",
                'marks': 1
            },
            4: {
                'text_tamil': 'அலாரம் வந்த பின் ரமேஷின் காலை நேரத்தில் உருவான இரண்டு புதிய பழக்கங்களை பகுதியைப் பயன்படுத்திக் கூறுக.',
                'text_english': 'Using the passage, state two new morning habits that Ramesh developed after the alarm clock arrived.',
                'marks': 1
            },
            5: {
                'text_tamil': 'ஆசிரியர் ரமேஷை ஏன் பாராட்டினார் என்பதை பகுதியிலுள்ள தகவலின் அடிப்படையில் விளக்குக.',
                'text_english': 'Explain why the teacher praised Ramesh based on the information in the passage.',
                'marks': 1
            }
        },
        'expected_answers': {
            1: ["தாமதமாக பள்ளிக்கு செல்வது", "பள்ளிக்கு தாமதமாக வருவது", "தாமதமாக பள்ளிக்கு செல்லுதல்", "தாமதம்"],
            2: ["அலாரம் கடிகாரம்", "புதிய அலாரம் கடிகாரம்", "அலாரம் கடிகாரத்தை", "கடிகாரம்", "அலாரம்"],
            3: ["ஆசிரியர்", "ஆசிரியரும்", "ஆசிரியர் கவனித்தார்", "ஆசிரியர் முதலில் கவனித்தார்"],
            4: ["படுக்கையைச் சீர்செய்து முகம் கழுவி", "படுக்கையை சீர்செய்து முகம் கழுவுதல்", "சீர்செய்து கழுவி"],
            5: ["தாமதமாக வரவில்லை", "ஒரு வாரத்துக்குள் தாமதமாகவில்லை", "நேரத்துக்கு பள்ளிக்கு வந்தார்", "தாமதமாக வராததால்"]
        }
    },
    'intermediate': {
        'id': 'intermediate',
        'level': 'Intermediate',
        'title': 'Time Management Lesson',
        'paragraph': {
            'tamil': """குமார் தினமும் பள்ளி முடிந்ததும் நேரடியாக வீட்டுக்குச் செல்வதில்லை. வழியிலேயே நண்பர்களுடன் விளையாடி நேரத்தை கழிப்பான். அதனால் வீட்டுக்குச் செல்லும் போது மாலை தாமதமாகி விடும். வீட்டுப்பாடங்களை அவசரமாக செய்து முடிப்பதால், பல நேரங்களில் அவனுக்கு பாடங்கள் சரியாகப் புரியாது.

ஒரு நாள், வகுப்பில் நடந்த மாதாந்திரத் தேர்வில் குமார் எதிர்பார்த்த மதிப்பெண்களை பெறவில்லை. அதனால் அவன் மிகவும் மனமுடைந்தான். அந்த நாளில் அவனது அப்பா, “நேர மேலாண்மை முக்கியம்” என்று அவனிடம் அமைதியாக பேசினார்.

அடுத்த நாட்களில், குமார் பள்ளி முடிந்தவுடன் முதலில் வீட்டுக்குச் சென்று சிறிது நேரம் ஓய்வு எடுத்து, பின்னர் வீட்டுப்பாடங்களைச் செய்ய ஆரம்பித்தான். வீட்டுப்பாடங்களை முடித்த பிறகே விளையாட வேண்டும் என்று அவன் தன்னுக்கே ஒரு விதியை வைத்துக் கொண்டான்.

சில வாரங்களுக்குள், குமாருக்கு பாடங்கள் தெளிவாகப் புரியத் தொடங்கின. அடுத்த தேர்வில் அவன் முன்பை விட நல்ல மதிப்பெண்களை பெற்றான். இதைக் கண்ட ஆசிரியரும், குமாரின் முயற்சியை பாராட்டினார்.""",
            'english': """Kumar used to stop on the way home after school to play with friends and would reach home late. Because he rushed his homework, he often did not understand the lessons well. One month he did not get the marks he expected on the class test, which upset him. His father calmly told him that time management is important.

In the following days, Kumar began going straight home, resting briefly, then doing homework before playing. Within a few weeks he understood the lessons clearly and scored better in the next test. His teacher noticed this effort and praised him."""
        },
        'questions': {
            1: {
                'text_tamil': 'குமார் பள்ளி முடிந்த பிறகு வழியிலேயே என்ன செய்தான்?',
                'text_english': 'What did Kumar do on the way home after school?',
                'marks': 1
            },
            2: {
                'text_tamil': 'வீட்டுப்பாடங்களை அவசரமாகச் செய்ததால் குமாருக்கு என்ன ஏற்பட்டது?',
                'text_english': 'What happened because Kumar rushed his homework?',
                'marks': 1
            },
            3: {
                'text_tamil': 'மாதாந்திரத் தேர்வில் குமார் எதை பெறவில்லை?',
                'text_english': "What did Kumar fail to get in the monthly test?",
                'marks': 1
            },
            4: {
                'text_tamil': 'குமாரிடம் அவனது அப்பா எந்த ஒரு விஷயத்தை கூறினார்?',
                'text_english': 'What advice did Kumar’s father give him?',
                'marks': 1
            },
            5: {
                'text_tamil': 'சில வாரங்களுக்குள் குமாருக்கு ஏற்பட்ட கல்வி மாற்றம் என்ன?',
                'text_english': 'What academic change did Kumar experience within a few weeks?',
                'marks': 1
            }
        },
        'expected_answers': {
            1: [
                "நண்பர்களுடன் விளையாடினார்",
                "வழியிலேயே விளையாடினார்",
                "விளையாடி நேரம் கழித்தார்",
                "வழியில் நின்று நண்பர்களுடன் விளையாடினார்",
                "வழியில் தோழர்களுடன் நேரம் கழித்தார்",
                "வீட்டுக்குச் செல்லாமல் விளையாடினார்"
            ],
            2: [
                "பாடங்கள் சரியாகப் புரியவில்லை",
                "பாடங்கள் புரியாது",
                "அவருக்கு பாடங்கள் தெளிவாகப் புரியவில்லை",
                "புரிவதில் சிக்கல் ஏற்பட்டது",
                "குழப்பமாக இருந்தது"
            ],
            3: [
                "எதிர்பார்த்த மதிப்பெண்கள் கிடைக்கவில்லை",
                "கிடைக்க வேண்டிய மதிப்பெண்கள் கிடைக்கவில்லை",
                "வேண்டிய மதிப்பெண்கள் வரவில்லை",
                "நல்ல மதிப்பெண் கிடைக்கவில்லை",
                "உயர் மதிப்பெண் பெறவில்லை"
            ],
            4: [
                "நேர மேலாண்மை முக்கியம்",
                "நேரத்தை நன்றாக மேலாண்மை செய்ய வேண்டும்",
                "நேரத்தை திட்டமிடுவது முக்கியம்",
                "முதலில் வீட்டுப்பாடம் செய்து பின்னர் விளையாடு",
                "வீட்டுப்பாடத்தை முடித்து பின்னர் விளையாடு",
                "ஒழுங்காகச் செய்"
            ],
            5: [
                "பாடங்கள் தெளிவாகப் புரிந்தன",
                "அடுத்த தேர்வில் நல்ல மதிப்பெண்கள் பெற்றார்",
                "முந்தையதைவிட நல்ல மதிப்பெண்கள் பெற்றார்",
                "மேம்பாடு காணப்பட்டது",
                "முன்னேற்றம் அடைந்தார்"
            ]
        }
    },
    'advanced': {
        'id': 'advanced',
        'level': 'Advanced',
        'title': 'Aravind’s Study Journey',
        'paragraph': {
            'tamil': """அரவிந்த் கடந்த சில மாதங்களாகவே வகுப்பில் அமைதியாக இருப்பதை ஆசிரியர் கவனித்து வந்தார். முன்பு கேள்விகள் கேட்டு கலந்துகொள்வவன், இப்போது பெரும்பாலும் தலையைக் குனிந்து அமர்ந்திருப்பான். வீட்டுப்பாடங்களை அவன் முறையாகச் செய்து வந்தாலும், வகுப்பில் அவனது கவனம் சிதறியிருப்பது தெளிவாகத் தெரிந்தது. இதற்குக் காரணம், சமீபத்தில் அவனது தாயார் நீண்ட கால உடல்நலக் குறைவு காரணமாக மருத்துவமனையில் அனுமதிக்கப்பட்டிருந்ததே.

வீட்டில் தந்தை வேலை காரணமாக தாமதமாக வருவதால், இளைய சகோதரனைக் கவனிப்பது, வீட்டு வேலைகளில் உதவுவது போன்ற பொறுப்புகள் அரவிந்தின் மீது வந்தன. இரவு நேரங்களில் அவன் பாடங்களை படிக்க முயன்றாலும், மனஅழுத்தம் காரணமாக கவனம் நீண்ட நேரம் நிலைத்திருக்கவில்லை. இருந்தாலும், அவன் பள்ளிக்கான கடமைகளை தவிர்க்கவில்லை.

ஒருநாள், ஆசிரியர் அவனை தனியாக அழைத்து பேசினார். அந்த உரையாடல் தண்டிப்பதற்காகவும், எச்சரிப்பதற்காகவும் இல்லை; அவன் நிலையை முழுமையாக புரிந்து கொள்ளவே நடந்தது. தனது குடும்ப நிலையை வெளிப்படுத்திய பிறகு, அரவிந்தின் மனச்சுமை கணிசமாக குறைந்தது. ஆசிரியர் அவனுக்கு படிப்பை சிறு பகுதிகளாகப் பிரித்து, தினசரி அடையக்கூடிய இலக்குகளுடன் படிக்க ஆலோசனை வழங்கினார்.

அந்த ஆலோசனையை அரவிந்த் நடைமுறையில் கொண்டு வந்தான். தினமும் குறைந்த நேரம் என்றாலும், குறிப்பிட்ட நேரத்தில் முழு கவனத்துடன் படிக்கத் தொடங்கினான். சில வாரங்களில் அவனது கவனமும், புரிதலும் மேம்பட்டது. இறுதித் தேர்வில் அவன் எதிர்பார்த்ததை விட சிறந்த மதிப்பெண்களை பெற்றான். அந்த வெற்றி, அவனுக்கு தன்னம்பிக்கையையும் எதிர்காலம் குறித்து நம்பிக்கையையும் மீண்டும் வழங்கியது.""",
            'english': """For the past few months, Aravind’s teacher noticed that he was unusually quiet in class. Once active and asking questions, he now mostly sat with his head down. Although he completed his homework regularly, it was clear that his attention in class was scattered. The reason was that his mother had been admitted to the hospital for a long-standing illness.

At home, because his father came back late from work, Aravind had to look after his younger brother and help with household chores. At night he tried to study, but due to mental stress he could not maintain his focus for long. Even so, he did not neglect his school responsibilities.

One day, the teacher called him aside to talk. The conversation was not to scold or warn him, but to understand his situation fully. After sharing his family circumstances, Aravind felt a great sense of relief. The teacher advised him to break his studies into smaller parts and study each day with achievable goals.

Aravind began to follow this advice. Even if it was for a short time each day, he started studying at a fixed time with full concentration. Within a few weeks his focus and understanding improved. In the final exam, he scored better than he had expected. That success restored his self-confidence and gave him renewed hope for the future."""
        },
        'questions': {
            1: {
                'text_tamil': 'அரவிந்தின் படிப்பில் கவனம் குறையத் தொடங்கியதற்கான ஆரம்ப காரணம் என்ன?',
                'text_english': 'What was the initial reason for Aravind’s loss of focus in studies?',
                'marks': 1
            },
            2: {
                'text_tamil': 'பள்ளிப் பணிகளைச் செய்தபோதும் அரவிந்த் படிப்பில் முழு கவனம் செலுத்த முடியாததற்கான நேரடி காரணம் என்ன?',
                'text_english': 'What was the direct reason Aravind could not fully concentrate on his studies even while doing school work?',
                'marks': 1
            },
            3: {
                'text_tamil': 'ஆசிரியர் அரவிந்தை தனியாக அழைத்து பேசியதன் உடனடி விளைவு என்ன?',
                'text_english': 'What was the immediate effect after the teacher spoke to Aravind privately?',
                'marks': 1
            },
            4: {
                'text_tamil': 'அரவிந்தின் படிப்பு முன்னேற்றத்திற்கு ஆசிரியர் அளித்த குறிப்பிட்ட ஆலோசனை என்ன?',
                'text_english': 'What specific study advice did the teacher give Aravind that helped his progress?',
                'marks': 1
            },
            5: {
                'text_tamil': 'இறுதித் தேர்வில் அரவிந்தின் மதிப்பெண் முன்னேற்றத்திற்கு நேரடியாக காரணமான மாற்றம் எது?',
                'text_english': 'Which change directly led to Aravind’s improved marks in the final exam?',
                'marks': 1
            }
        },
        'expected_answers': {
            1: [
                "தாயார் மருத்துவமனையில் அனுமதிக்கப்பட்டது",
                "தாயார் நீண்ட கால உடல்நலக் குறைவு காரணமாக மருத்துவமனையில் அனுமதிக்கப்பட்டது",
                "அவனது தாயார் மருத்துவமனையில் அனுமதிக்கப்பட்டிருந்தது",
                "அம்மா மருத்துவமனையில் இருந்தது",
                "தாயாருக்கு உடல்நலக் குறைவு",
                "தாயார் நோய்வாய்ப்பட்டு மருத்துவமனையில்",
                "அவனது தாயார் நீண்ட கால உடல்நலக் குறைவு"
            ],
            2: [
                "மனஅழுத்தம்",
                "மனஅழுத்தம் காரணமாக",
                "மனச்சுமை",
                "மன அழுத்தம்",
                "அழுத்தம் காரணமாக",
                "மன அழுத்தம் காரணமாக கவனம் நிலைத்திருக்கவில்லை",
                "மனச்சுமை காரணமாக"
            ],
            3: [
                "மனச்சுமை குறைந்தது",
                "அரவிந்தின் மனச்சுமை கணிசமாக குறைந்தது",
                "மனச்சுமை கணிசமாக குறைந்தது",
                "மன அழுத்தம் குறைந்தது",
                "அவன் மனச்சுமை குறைந்தது",
                "சுமை குறைந்தது"
            ],
            4: [
                "படிப்பை சிறு பகுதிகளாகப் பிரித்து படிக்க",
                "சிறு பகுதிகளாகப் பிரித்து தினசரி இலக்குகளுடன் படிக்க",
                "படிப்பை பகுதிகளாக பிரித்து படிக்க",
                "சிறு பகுதிகளாக படிக்க",
                "தினசரி அடையக்கூடிய இலக்குகளுடன் படிக்க",
                "பாடங்களை பகுதிகளாக பிரித்து"
            ],
            5: [
                "குறிப்பிட்ட நேரத்தில் முழு கவனத்துடன் படித்தது",
                "தினமும் குறைந்த நேரம் என்றாலும் முழு கவனத்துடன் படித்தது",
                "குறிப்பிட்ட நேரத்தில் படிக்கத் தொடங்கினான்",
                "முழு கவனத்துடன் படித்தது",
                "சிறு பகுதிகளாக படித்து",
                "தினசரி படித்தது",
                "நெடுக்கமாக படித்தது"
            ]
        }
    }
}

# Order to present passages (limit to two pages as requested)
PASSAGE_ORDER = ['basic', 'intermediate', 'advanced']

def _get_passage(paragraph_id=None):
    """Return passage dict, defaulting to the first in order."""
    pid = paragraph_id or PASSAGE_ORDER[0]
    return PASSAGES.get(pid)


@app.route('/api/paragraphs', methods=['GET'])
def get_all_paragraphs():
    """Get all passages with questions (without expected answers)."""
    passages = []
    for pid in PASSAGE_ORDER:
        passage = PASSAGES.get(pid)
        if passage:
            passages.append({
                'id': passage['id'],
                'level': passage['level'],
                'title': passage['title'],
                'paragraph': passage['paragraph'],
                'questions': passage['questions']
            })
    return jsonify({'passages': passages})


@app.route('/api/paragraph', methods=['GET'])
def get_paragraph():
    """Get the first paragraph (backward compatibility)."""
    first = _get_passage()
    return jsonify({'paragraph': first['paragraph']}) if first else jsonify({'paragraph': {}})


@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Get questions for the first paragraph (backward compatibility)."""
    first = _get_passage()
    return jsonify({'questions': first['questions']}) if first else jsonify({'questions': {}})

@app.route('/api/evaluate', methods=['POST', 'OPTIONS'])
def evaluate_answer():
    """Evaluate a single answer using Llama AI."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        if not request.json:
            return jsonify({
                'error': 'No JSON data received',
                'success': False
            }), 400
            
        data = request.json
        question_number = int(data.get('questionNumber'))
        paragraph_id = data.get('paragraphId') or PASSAGE_ORDER[0]
        passage = _get_passage(paragraph_id)
        
        if not passage:
            return jsonify({
                'error': 'Invalid passage selected',
                'success': False
            }), 400
        
        questions = passage.get('questions', {})
        expected_answers_map = passage.get('expected_answers', {})
        user_answer = data.get('userAnswer', '').strip()
        
        if question_number not in questions:
            return jsonify({
                'error': 'Invalid question number for this passage',
                'success': False
            }), 400
        
        if not user_answer:
            return jsonify({
                'error': 'Answer cannot be empty',
                'success': False
            }), 400
        
        max_marks = questions.get(question_number, {}).get('marks', 1)
        expected_answers = expected_answers_map.get(question_number, [])
        
        # Use AI for Evaluation exclusively
        eval_result = evaluate_with_llama(
            passage['paragraph']['tamil'],
            questions[question_number]['text_tamil'],
            user_answer,
            expected_answers
        )
        
        # If AI failed, return error instead of falling back to broken modules
        if eval_result.get('error') or not eval_result:
            return jsonify({
                'error': f"AI Evaluation failed: {eval_result.get('error', 'Unknown error')}",
                'success': False
            }), 500

        # Return AI Results
        return jsonify({
            'success': True,
            'questionNumber': question_number,
            'userAnswer': user_answer,
            'marks': eval_result.get('marks', 0),
            'maxMarks': max_marks,
            'passed': eval_result.get('passed', False),
            'finalScore': eval_result.get('finalScore', 0),
            'feedback': eval_result.get('feedback', ''),
            'reasoning': eval_result.get('reasoning', ''),
            'question_text': questions[question_number]['text_tamil'],
            'expected_answers': expected_answers,
            'scores': {
                'final': (eval_result.get('finalScore', 0) or 0) * 100
            }
        })

        
    except ValueError as e:
        return jsonify({
            'error': f'Invalid input: {str(e)}',
            'success': False
        }), 400
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in evaluate_answer: {error_trace}")
        return jsonify({
            'error': f'Server error: {str(e)}',
            'success': False,
            'traceback': error_trace if app.debug else None
        }), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_teacher_report():
    """
    Generate a detailed, personalized teacher's report based on all 4 modules using Groq AI.
    """
    try:
        data = request.json or {}
        api_key = "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"
        
        # Build a highly detailed prompt for the Groq AI
        prompt = f"""You are an ELITE Tamil Language Professor (தமிழ் பேராசிரியர்) dedicated to precision, linguistic excellence, and academic rigor.
Your mission is to analyze the student's 4-module assessment (Listening, Speaking, Reading, Writing) and generate a world-class "Linguistic Diagnostic & Correction Report".

### 🔎 MISSION:
Perform a deep-tissue analysis of the student's performance. For EVERY mistake identified in the data, you MUST pinpoint the exact nature of the error, categorize it using specific labels, and provide a clear academic path to correction.

### 🔴 ERROR CATEGORIZATION COMMANDS:
For every incorrect answer, use one of these EXACT labels:
1. **[HEARING ERROR]**: Use if the student misheard or misinterpreted the audio content.
2. **[LOGICAL ERROR]**: Use if the student understood the words but misinterpreted the context, intent, or logic.
3. **[SPELLING ERROR]**: Use if the student made a mistake in Tamil script characters or word formation.
4. **[PRONUNCIATION ERROR]**: Use for speaking inaccuracies identified in the transcript or metadata.
5. **[VOCABULARY ERROR]**: Use if the student used an incorrect word for the intended meaning.

### 📋 REPORT STRUCTURE (MANDATORY):

# 👨‍🏫 Linguistic Diagnostic & Academic Correction Report

## 1. Executive Performance Portrait (செயல்திறன் சுருக்கம்)
- A professional synthesis of the student's current Tamil standing.
- High-level identification of their primary linguistic barriers (e.g., phonetic confusion, syntax errors).

## 2. Granular Error Diagnostics (க்ருதாவான தவறு பகுப்பாய்வு)
For EACH module (Listening, Speaking, Reading, Writing) provided in the data, you MUST list all wrong answers:

#### Module: [Module Name]
---
**ERROR CASE #1**
- **Command**: [ERROR TYPE COMMAND]
- **The Mistake (தவறு)**: "Exact text/answer provided by the student in Tamil script"
- **The Correction (சரிபார்த்தல்)**: "The perfectly correct Tamil answer/version"
- **The Diagnostic**: Explain exactly WHAT the mistake was in English. Mention specifically if it was a hearing error, logical error, or spelling mistake.
- **The Lesson**: Explain WHY this is a common pitfall for English speakers. Teach the specific Tamil grammar/phonetic rule here.
- **Fix Logic**: Provide a 1-sentence 'Command-style' instruction on how to fix this.

## 3. Linguistic Common Pitfalls (பொதுவான மொழியியல் தவறுகள்)
- Identify and explain the top 3 recurring linguistic patterns across and within modules.

## 4. Academic Roadmap for Mastery (மேம்பாட்டிற்கான செயல் திட்டம்)
- Provide 3-5 prestigious, actionable steps to reach the next level of Tamil proficiency.

### 📊 STUDENT ASSESSMENT DATA FOR ANALYSIS:
{json.dumps(data, indent=2, ensure_ascii=False)}

### 📜 FINAL INSTRUCTIONS:
- LANGUAGE: English is the primary medium of instruction. Use Tamil script for all examples.
- TRANSPARENCY: If no data is available for a module, state "Assessment Data Missing".
- PERSPECTIVE: Speak as a supportive but demanding Professor who believes in the student's potential. Be exact, point out the mistakes specifically.
"""
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are an Elite Tamil Professor. You provide extremely detailed, academically rigorous reports. You point out exactly where the student went wrong by comparing their answer to the correct one."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 4096
        }
        
        print("🚀 Requesting report from Groq AI...")
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            report_text = result['choices'][0]['message']['content']
            print("✅ Report generated successfully via Groq.")
            return jsonify({
                'success': True,
                'report': report_text
            })
        else:
            print(f"❌ Groq Error: {response.text}")
            return jsonify({
                'success': False,
                'error': f"Groq response error: {response.status_code}"
            })
            
    except Exception as e:
        print(f"❌ Error in generate_teacher_report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'reading'}

@app.route('/')
def index():
    """Serve the main HTML page"""
    from flask import send_from_directory
    return send_from_directory('static', 'index.html')

@app.route('/flowchart')
def flowchart():
    """Serve the evaluation flowchart page"""
    from flask import send_from_directory
    return send_from_directory('static', 'evaluation-flowchart.html')

@app.route('/rules')
def rules():
    from flask import send_from_directory
    return send_from_directory('static', 'index.html')

@app.route('/page1')
def page1():
    from flask import send_from_directory
    return send_from_directory('static', 'page1.html')

@app.route('/page2')
def page2():
    from flask import send_from_directory
    return send_from_directory('static', 'page2.html')

@app.route('/page3')
def page3():
    from flask import send_from_directory
    return send_from_directory('static', 'page3.html')

@app.route('/results')
def results_page():
    from flask import send_from_directory
    return send_from_directory('static', 'result.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files (CSS, JS, etc.)"""
    from flask import send_from_directory
    # Only serve files that exist in static folder
    import os
    static_path = os.path.join('static', filename)
    if os.path.exists(static_path) and os.path.isfile(static_path):
        return send_from_directory('static', filename)
    else:
        from flask import abort
        abort(404)

if __name__ == '__main__':
    print("=" * 70)
    print("Tamil Reading Assessment Website")
    print("=" * 70)
    print("Starting Flask server...")
    print("Open your browser and go to: http://localhost:5003")
    print("=" * 70)
    print()
    app.run(debug=True, host='0.0.0.0', port=5003)

