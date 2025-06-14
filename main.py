import io
import queue
import re
import sys

import pyaudio
import pygame
import google.auth
from google.cloud import speech, texttospeech
from agent import get_gemini_response

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

credentials, project = google.auth.default()
speech_client = speech.SpeechClient(credentials=credentials)
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

# Initialize audio playback
pygame.mixer.init()


class MicrophoneStream:
    def __init__(self, rate=RATE, chunk=CHUNK):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b"".join(data)


def listen_once():
    language_code = "en-US"
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
        single_utterance=True,
    )

    with MicrophoneStream() as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content=chunk) for chunk in audio_generator)
        responses = speech_client.streaming_recognize(streaming_config, requests)

        transcript = ""
        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript
            print(f"\rUser: {transcript}", end="", flush=True)

            if result.is_final:
                print()
                break

        return transcript.strip()


def synthesize_and_play(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Standard-C")
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    audio_stream = io.BytesIO(response.audio_content)
    audio_stream.seek(0)
    pygame.mixer.music.load(audio_stream, "mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue


def main():
    print("🎙️ Start speaking. Say 'exit' to quit.\n")
    while True:
        print("Listening for your input...")
        user_input = listen_once()

        if not user_input:
            print("No speech detected. Listening again...\n")
            continue

        if re.search(r"\b(exit|quit)\b", user_input, re.I):
            print("👋 Exiting.")
            break

        gemini_response = get_gemini_response(user_input)
        print(f"Agent: {gemini_response}\n")

        synthesize_and_play(gemini_response)


if __name__ == "__main__":
    main()
