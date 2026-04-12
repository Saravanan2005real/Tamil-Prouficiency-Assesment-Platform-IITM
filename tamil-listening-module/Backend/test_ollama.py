"""
Quick test script to verify Ollama is running and accessible.
Run this before starting the Flask app to ensure Ollama is ready.
"""

import os
import sys
import requests

def test_ollama():
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
    
    print("=" * 60)
    print("Testing Ollama Connection")
    print("=" * 60)
    print(f"Ollama URL: {ollama_url}")
    print(f"Model: {ollama_model}")
    print()
    
    try:
        # Test 1: Check if Ollama server is running
        print("1. Checking if Ollama server is running...")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print("   ✓ Ollama server is running")
        else:
            print(f"   ✗ Ollama server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ✗ Cannot connect to Ollama at {ollama_url}")
        print(f"   → Start Ollama with: ollama serve")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    try:
        # Test 2: Check if model is available
        print("2. Checking if model is available...")
        models_response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if models_response.status_code == 200:
            models_data = models_response.json()
            available_models = [m.get('name', '') for m in models_data.get('models', [])]
            print(f"   Available models: {', '.join(available_models[:5])}")
            
            if ollama_model in available_models:
                print(f"   ✓ Model {ollama_model} is available")
            elif any(ollama_model.split(':')[0] in m for m in available_models):
                print(f"   ✓ Model variant of {ollama_model} is available")
            else:
                print(f"   ✗ Model {ollama_model} not found")
                print(f"   → Pull the model with: ollama pull {ollama_model}")
                return False
        else:
            print(f"   ✗ Cannot get model list (status {models_response.status_code})")
            return False
    except Exception as e:
        print(f"   ✗ Error checking models: {e}")
        return False
    
    try:
        # Test 3: Test a simple generation
        print("3. Testing model generation...")
        test_response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": "Hello",
                "stream": False
            },
            timeout=10
        )
        if test_response.status_code == 200:
            print("   ✓ Model generation test successful")
        else:
            print(f"   ✗ Model generation failed (status {test_response.status_code})")
            return False
    except Exception as e:
        print(f"   ✗ Error testing generation: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✓ All tests passed! Ollama is ready to use.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_ollama()
    sys.exit(0 if success else 1)

