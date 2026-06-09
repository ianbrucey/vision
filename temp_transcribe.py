import whisper
import os

def transcribe_audio(file_path):
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]

if __name__ == "__main__":
    file1 = "sample_files/URecorder_20260609_075715.m4a"
    file2 = "sample_files/URecorder_20260609_081059.m4a"

    print(f"Transcribing {file1}...")
    transcription1 = transcribe_audio(file1)
    print(f"Transcription for {file1}:\n{transcription1}\n")

    print(f"Transcribing {file2}...")
    transcription2 = transcribe_audio(file2)
    print(f"Transcription for {file2}:\n{transcription2}\n")