#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tamil Grammar and Vocabulary Error Detector using Ollama 3.0
Detects grammar and vocabulary errors in Tamil text using local Ollama model
ONLY DETECTS ERRORS - DOES NOT CORRECT THEM
"""

import os
import re
import requests
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_GRAMMAR_MODEL', 'llama3:latest')  # Default to llama3:latest, can be changed to llama3.2, etc.


class TamilGrammarVocabDetector:
    """
    Grammar and Vocabulary Error Detector using Ollama 3.0
    Uses local Ollama model to detect grammar and vocabulary errors in Tamil text
    """
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        """
        Initialize the detector
        
        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model: Ollama model name (default: llama3:latest)
        """
        self.base_url = base_url
        self.model = model
        self.available = False
        self._check_ollama_connection()
        
        # Grammar detector removed - grammar checking disabled in this module
        self.grammar_detector = None
    
    def _check_ollama_connection(self) -> bool:
        """Check if Ollama is available and the model exists"""
        try:
            logger.info(f"Checking Ollama connection at {self.base_url}...")
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                # Check if model exists (exact match or partial match)
                model_found = False
                for model_name in model_names:
                    if self.model in model_name or model_name in self.model:
                        model_found = True
                        self.model = model_name  # Use the exact model name
                        break
                
                if model_found:
                    self.available = True
                    logger.info(f"Ollama is available! Using model: {self.model}")
                    return True
                else:
                    logger.warning(f"Model '{self.model}' not found. Available models: {model_names}")
                    logger.warning(f"Please run: ollama pull {self.model}")
                    return False
            else:
                logger.error(f"Ollama returned status code: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}. Make sure Ollama is running.")
            logger.error("Start Ollama by running: ollama serve")
            return False
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
            return False
    
    def _call_ollama(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        Call Ollama API with a prompt
        
        Args:
            prompt: The prompt to send to Ollama
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response text or None if error
        """
        if not self.available:
            logger.error("Ollama is not available. Cannot detect errors.")
            return None
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent error detection
                        "num_predict": max_tokens
                    }
                },
                timeout=60  # 60 second timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            elif response.status_code == 404:
                logger.error(f"Model '{self.model}' not found. Please run: ollama pull {self.model}")
                return None
            else:
                logger.error(f"Ollama API returned status code: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return None
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out. The model might be too slow or the text too long.")
            return None
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None
    
    def detect_errors(self, text: str) -> Dict:
        """
        Detect grammar and vocabulary errors in Tamil text
        Uses rule-based grammar detection first, then Ollama for additional checks
        
        Args:
            text: Tamil text to check
            
        Returns:
            Dict with:
                - grammar_errors: List of grammar error dicts
                - vocabulary_errors: List of vocabulary error dicts
                - total_errors: int
                - error_count: int (grammar + vocabulary)
                - passed: bool (True if no errors found)
        """
        if not text or len(text.strip()) < 5:
            return {
                "grammar_errors": [],
                "vocabulary_errors": [],
                "total_errors": 0,
                "error_count": 0,
                "passed": True,
                "reason": "Text too short to check"
            }
        
        # STEP 1: Rule-based grammar detection (subject-verb agreement, etc.)
        rule_based_grammar_errors = []
        if self.grammar_detector:
            try:
                grammar_result = self.grammar_detector.detect_grammar_errors(text)
                rule_based_grammar_errors = grammar_result.get('grammar_errors', [])
                logger.info(f"Rule-based grammar check found {len(rule_based_grammar_errors)} errors")
            except Exception as e:
                logger.warning(f"Error in rule-based grammar detection: {e}")
        
        # STEP 2: Ollama-based detection (if available)
        ollama_grammar_errors = []
        ollama_vocab_errors = []
        
        if not self.available:
            # If Ollama not available, return rule-based results only
            total_errors = len(rule_based_grammar_errors)
            return {
                "grammar_errors": rule_based_grammar_errors,
                "vocabulary_errors": [],
                "total_errors": total_errors,
                "error_count": total_errors,
                "passed": total_errors == 0,
                "reason": "Ollama is not available. Using rule-based detection only.",
                "error_type": "ollama_not_available"
            }
        
        # Create prompt for error detection
        prompt = f"""You are an expert Tamil language grammar and vocabulary checker. Your task is to DETECT errors in the given Tamil text. DO NOT correct the errors, only identify them.

Tamil Text to Check:
{text}

Instructions:
1. Analyze the text for GRAMMAR ERRORS (sentence structure, verb forms, case markers, word order, etc.)
2. Analyze the text for VOCABULARY ERRORS (incorrect word usage, inappropriate word choices, semantic mismatches)
3. For each error found, provide:
   - Error type: GRAMMAR or VOCABULARY
   - Location: The exact word or phrase where the error occurs
   - Description: Brief explanation of what is wrong (in English or Tamil)
   - Severity: HIGH, MEDIUM, or LOW

CRITICAL RULES - NEVER FLAG AS ERRORS:
1. Articles (ஒரு, இந்த, அந்த) - These are ALWAYS valid and don't need case markers. NEVER flag them for "wrong case" or case marker errors.
2. Auxiliary verb "வேண்டும்" - This verb doesn't require strict subject-verb agreement. NEVER flag "வேண்டும்" for agreement errors.
3. "என்பது" - This is a valid Tamil construction meaning "it is that" or "that which is". NEVER flag "என்பது" for any grammar errors.
4. Possessive pronouns (என், உன், அவன், etc.) - These are valid without case markers. NEVER flag them for case marking errors.
5. Abstract nouns - These often don't require explicit case markers. Be conservative when flagging them.
6. Subject pronouns (அனைவரும், எல்லோரும், etc.) - These are valid as subjects without accusative markers.

IMPORTANT:
- Only detect CLEAR, OBVIOUS errors
- Be CONSERVATIVE - when in doubt, don't flag it as an error
- Only detect errors, DO NOT provide corrections
- Be specific about the location of each error
- Focus on actual errors, not stylistic preferences
- Consider Tamil grammar rules: verb conjugation, case markers, word order (SOV), etc.

Format your response as follows:
ERROR_TYPE: GRAMMAR/VOCABULARY
LOCATION: [word or phrase]
DESCRIPTION: [what is wrong]
SEVERITY: HIGH/MEDIUM/LOW

If no errors are found, respond with:
NO_ERRORS: true

Begin analysis:"""

        logger.info(f"Calling Ollama to detect errors in text (length: {len(text)} chars)")
        response_text = self._call_ollama(prompt)
        
        if not response_text:
            # If Ollama fails, return rule-based results only
            total_errors = len(rule_based_grammar_errors)
            return {
                "grammar_errors": rule_based_grammar_errors,
                "vocabulary_errors": [],
                "total_errors": total_errors,
                "error_count": total_errors,
                "passed": total_errors == 0,
                "reason": "Error calling Ollama API. Using rule-based detection only.",
                "error_type": "ollama_api_error"
            }
        
        # Parse the Ollama response
        ollama_errors = self._parse_ollama_response(response_text, text)
        ollama_grammar_errors = [e for e in ollama_errors if e.get('error_type') == 'GRAMMAR']
        ollama_vocab_errors = [e for e in ollama_errors if e.get('error_type') == 'VOCABULARY']
        
        # Combine rule-based and Ollama grammar errors (avoid duplicates)
        all_grammar_errors = rule_based_grammar_errors.copy()
        
        # Add Ollama grammar errors that don't duplicate rule-based ones
        for ollama_err in ollama_grammar_errors:
            # Check if this error is already covered by rule-based detection
            is_duplicate = False
            ollama_location = ollama_err.get('location', '').lower()
            ollama_desc = ollama_err.get('description', '').lower()
            
            for rule_err in rule_based_grammar_errors:
                rule_location = rule_err.get('location', '').lower()
                rule_desc = rule_err.get('description', '').lower()
                # If locations overlap or descriptions are similar, skip
                if ollama_location in rule_location or rule_location in ollama_location:
                    is_duplicate = True
                    break
                if 'subject' in ollama_desc and 'verb' in ollama_desc and 'subject' in rule_desc and 'verb' in rule_desc:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                all_grammar_errors.append(ollama_err)
        
        total_errors = len(all_grammar_errors) + len(ollama_vocab_errors)
        
        logger.info(f"Rule-based: {len(rule_based_grammar_errors)} grammar errors")
        logger.info(f"Ollama: {len(ollama_grammar_errors)} grammar errors, {len(ollama_vocab_errors)} vocabulary errors")
        logger.info(f"Total: {len(all_grammar_errors)} grammar errors, {len(ollama_vocab_errors)} vocabulary errors")
        
        return {
            "grammar_errors": all_grammar_errors,
            "vocabulary_errors": ollama_vocab_errors,
            "total_errors": total_errors,
            "error_count": total_errors,
            "passed": total_errors == 0,
            "reason": f"Found {total_errors} errors" if total_errors > 0 else "No errors found",
            "raw_response": response_text
        }
    
    def _parse_ollama_response(self, response: str, original_text: str) -> List[Dict]:
        """
        Parse Ollama response to extract error information
        
        Args:
            response: Raw response from Ollama
            original_text: Original text that was checked
            
        Returns:
            List of error dicts
        """
        errors = []
        
        # Check if no errors
        if re.search(r'NO_ERRORS:\s*true', response, re.IGNORECASE):
            return errors
        
        # Split response into lines
        lines = response.split('\n')
        
        current_error = {}
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - save current error if complete
                if current_error and 'error_type' in current_error:
                    errors.append(current_error)
                    current_error = {}
                continue
            
            # Check for error type
            if re.match(r'ERROR_TYPE:', line, re.IGNORECASE):
                # Save previous error if exists
                if current_error and 'error_type' in current_error:
                    errors.append(current_error)
                
                # Start new error
                match = re.search(r'ERROR_TYPE:\s*(GRAMMAR|VOCABULARY)', line, re.IGNORECASE)
                if match:
                    current_error = {
                        'error_type': match.group(1).upper(),
                        'location': '',
                        'description': '',
                        'severity': 'MEDIUM'
                    }
            
            # Check for location
            elif re.match(r'LOCATION:', line, re.IGNORECASE):
                match = re.search(r'LOCATION:\s*(.+)', line, re.IGNORECASE)
                if match:
                    current_error['location'] = match.group(1).strip()
            
            # Check for description
            elif re.match(r'DESCRIPTION:', line, re.IGNORECASE):
                match = re.search(r'DESCRIPTION:\s*(.+)', line, re.IGNORECASE)
                if match:
                    current_error['description'] = match.group(1).strip()
            
            # Check for severity
            elif re.match(r'SEVERITY:', line, re.IGNORECASE):
                match = re.search(r'SEVERITY:\s*(HIGH|MEDIUM|LOW)', line, re.IGNORECASE)
                if match:
                    current_error['severity'] = match.group(1).upper()
        
        # Save last error if exists
        if current_error and 'error_type' in current_error:
            errors.append(current_error)
        
        # If no structured errors found, try to extract from free-form text
        if not errors:
            errors = self._extract_errors_from_freeform(response, original_text)
        
        return errors
    
    def _extract_errors_from_freeform(self, response: str, original_text: str) -> List[Dict]:
        """
        Extract errors from free-form response if structured format not found
        
        Args:
            response: Raw response from Ollama
            original_text: Original text that was checked
            
        Returns:
            List of error dicts
        """
        errors = []
        
        # Look for common error indicators
        error_patterns = [
            (r'grammar\s+error[:\s]+(.+?)(?:\n|$)', 'GRAMMAR'),
            (r'vocabulary\s+error[:\s]+(.+?)(?:\n|$)', 'VOCABULARY'),
            (r'error[:\s]+(.+?)(?:\n|$)', 'GRAMMAR'),  # Default to grammar
        ]
        
        for pattern, error_type in error_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                error_desc = match.group(1).strip()
                if error_desc and len(error_desc) > 5:  # Valid error description
                    errors.append({
                        'error_type': error_type,
                        'location': '',
                        'description': error_desc,
                        'severity': 'MEDIUM'
                    })
        
        return errors
    
    def check_grammar(self, text: str) -> Dict:
        """
        Check only grammar errors
        
        Args:
            text: Tamil text to check
            
        Returns:
            Dict with grammar error information
        """
        result = self.detect_errors(text)
        
        return {
            "passed": len(result.get('grammar_errors', [])) == 0,
            "grammar_errors": result.get('grammar_errors', []),
            "error_count": len(result.get('grammar_errors', [])),
            "reason": result.get('reason', ''),
            "total_errors": len(result.get('grammar_errors', []))
        }
    
    def check_vocabulary(self, text: str) -> Dict:
        """
        Check only vocabulary errors
        
        Args:
            text: Tamil text to check
            
        Returns:
            Dict with vocabulary error information
        """
        result = self.detect_errors(text)
        
        return {
            "passed": len(result.get('vocabulary_errors', [])) == 0,
            "vocabulary_errors": result.get('vocabulary_errors', []),
            "error_count": len(result.get('vocabulary_errors', [])),
            "reason": result.get('reason', ''),
            "total_errors": len(result.get('vocabulary_errors', []))
        }


# ============================================================================
# SIMPLE USAGE FUNCTIONS
# ============================================================================

# Global detector instance (lazy loading)
_detector_instance = None

def get_detector(base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL) -> TamilGrammarVocabDetector:
    """Get or create global detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = TamilGrammarVocabDetector(base_url=base_url, model=model)
    return _detector_instance

def detect_errors(text: str, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL) -> Dict:
    """
    Simple function to detect grammar and vocabulary errors
    
    Usage:
        from tamil_grammar_vocab_ollama import detect_errors
        result = detect_errors('நான் படிக்கிறேன்')
        print(result['grammar_errors'])
        print(result['vocabulary_errors'])
    """
    detector = get_detector(base_url=base_url, model=model)
    return detector.detect_errors(text)

def check_grammar(text: str, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL) -> Dict:
    """
    Simple function to check grammar errors only
    
    Usage:
        from tamil_grammar_vocab_ollama import check_grammar
        result = check_grammar('நான் படிக்கிறேன்')
        print(result['grammar_errors'])
    """
    detector = get_detector(base_url=base_url, model=model)
    return detector.check_grammar(text)

def check_vocabulary(text: str, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL) -> Dict:
    """
    Simple function to check vocabulary errors only
    
    Usage:
        from tamil_grammar_vocab_ollama import check_vocabulary
        result = check_vocabulary('நான் படிக்கிறேன்')
        print(result['vocabulary_errors'])
    """
    detector = get_detector(base_url=base_url, model=model)
    return detector.check_vocabulary(text)


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == '__main__':
    import sys
    import io
    
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*70)
    print("Tamil Grammar and Vocabulary Error Detector using Ollama 3.0")
    print("="*70)
    
    # Create detector
    detector = TamilGrammarVocabDetector()
    
    if not detector.available:
        print("\n[!] ERROR: Ollama is not available!")
        print("    Please:")
        print("    1. Start Ollama: ollama serve")
        print(f"    2. Pull the model: ollama pull {OLLAMA_MODEL}")
        sys.exit(1)
    
    # Test cases
    test_cases = [
        "நான் படிக்கிறேன்",  # Should be correct
        "நான் படிக்கிறான்",  # Wrong verb form (should be படிக்கிறேன் for first person)
        "நான் புத்தகம் படிக்கிறேன்",  # Should be correct
        "நான் படம் சாப்பிடுகிறேன்",  # Vocabulary error (படம் + சாப்பிடு is wrong)
    ]
    
    print("\n[*] Testing error detection:")
    print("-"*70)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n[{i}] Text: {test_text}")
        print("-"*70)
        
        result = detector.detect_errors(test_text)
        
        if result.get('error_type') == 'ollama_not_available':
            print("  [!] Ollama is not available")
            continue
        
        grammar_errors = result.get('grammar_errors', [])
        vocab_errors = result.get('vocabulary_errors', [])
        total = result.get('total_errors', 0)
        
        print(f"  Total errors: {total}")
        print(f"  Grammar errors: {len(grammar_errors)}")
        print(f"  Vocabulary errors: {len(vocab_errors)}")
        
        if grammar_errors:
            print("\n  Grammar Errors:")
            for j, error in enumerate(grammar_errors, 1):
                print(f"    {j}. Location: {error.get('location', 'N/A')}")
                print(f"       Description: {error.get('description', 'N/A')}")
                print(f"       Severity: {error.get('severity', 'N/A')}")
        
        if vocab_errors:
            print("\n  Vocabulary Errors:")
            for j, error in enumerate(vocab_errors, 1):
                print(f"    {j}. Location: {error.get('location', 'N/A')}")
                print(f"       Description: {error.get('description', 'N/A')}")
                print(f"       Severity: {error.get('severity', 'N/A')}")
        
        if total == 0:
            print("  ✓ No errors found!")
    
    print("\n" + "="*70)
    print("Testing complete!")
    print("="*70)

