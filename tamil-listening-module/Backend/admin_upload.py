"""
Internal admin pipeline for processing audio files.
Usage: python admin_upload.py --audio <path> --level <1|2|3>
"""

import argparse
import json
import shutil
from pathlib import Path

from asr import transcribe_audio
from question_generator import generate_questions


def main(audio_path, level):
    """
    Main pipeline: Copy audio → Transcribe → Generate questions → Save files.
    
    Args:
        audio_path: Path to input audio file (str)
        level: Level number (int: 1, 2, or 3)
    """
    audio_path = Path(audio_path)
    
    # Validate inputs
    if not audio_path.exists():
        raise FileNotFoundError(f"❌ Audio file not found: {audio_path}")
    
    if level not in [1, 2, 3]:
        raise ValueError(f"❌ Invalid level: {level}. Must be 1, 2, or 3")
    
    print(f"\n🚀 Starting admin pipeline for Level {level}")
    print(f"   Audio: {audio_path}")
    print("-" * 60)
    
    # Step 1: Copy audio to uploads/audio/
    print("\n📁 Step 1: Copying audio file...")
    upload_dir = Path("uploads/audio")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    dest_audio = upload_dir / audio_path.name
    shutil.copy(audio_path, dest_audio)
    print(f"   ✅ Audio copied to: {dest_audio}")
    
    # Step 2: Transcribe audio using ASR
    print(f"\n🎙️ Step 2: Running ASR transcription...")
    transcript_text = transcribe_audio(dest_audio)
    
    # Step 3: Save transcript to data/transcripts/
    print(f"\n📝 Step 3: Saving transcript...")
    transcript_dir = Path("data/transcripts")
    transcript_dir.mkdir(parents=True, exist_ok=True)
    
    transcript_file = transcript_dir / f"{audio_path.stem}.txt"
    transcript_file.write_text(transcript_text, encoding="utf-8")
    print(f"   ✅ Transcript saved: {transcript_file}")
    
    # Step 4: Generate questions from transcript
    print(f"\n❓ Step 4: Generating questions...")
    questions = generate_questions(transcript_text, level)
    
    # Step 5: Save questions to data/questions/
    print(f"\n💾 Step 5: Saving questions...")
    question_dir = Path("data/questions")
    question_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as level-specific JSON file
    question_file = question_dir / f"level{level}.json"
    
    # If file exists, append; otherwise create new
    if question_file.exists():
        with open(question_file, 'r', encoding='utf-8') as f:
            existing_questions = json.load(f)
    else:
        existing_questions = []
    
    # Add new questions with metadata
    question_data = {
        "audio_file": audio_path.name,
        "transcript_file": transcript_file.name,
        "questions": questions
    }
    existing_questions.append(question_data)
    
    with open(question_file, 'w', encoding='utf-8') as f:
        json.dump(existing_questions, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Questions saved: {question_file}")
    print(f"   📊 Total questions added: {len(questions)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ ADMIN PIPELINE COMPLETE")
    print("=" * 60)
    print(f"   Audio:     {dest_audio}")
    print(f"   Transcript: {transcript_file}")
    print(f"   Questions:  {question_file}")
    print(f"   Level:      {level}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Internal admin pipeline for audio processing"
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to audio file"
    )
    parser.add_argument(
        "--level",
        required=True,
        type=int,
        choices=[1, 2, 3],
        help="Level number (1, 2, or 3)"
    )
    
    args = parser.parse_args()
    main(args.audio, args.level)
