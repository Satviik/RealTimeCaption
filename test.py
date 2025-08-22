# realtime_server.py
import soundcard as sc
import numpy as np
import queue
import threading
import time
from faster_whisper import WhisperModel
from llmmodel import clean_caption  # your gibberish-cleaning layer
from flask import Flask, jsonify
import warnings

warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

# ---------------- AUDIO / MODEL SETTINGS ----------------
SAMPLE_RATE = 16000
CHUNK_SEC = 1.5      # smaller chunks for lower latency
OVERLAP_SEC = 0.2    # reduced overlap for faster processing
CHUNK_SIZE = 1024

# Load Faster-Whisper model
model = WhisperModel("base", device="cuda", compute_type="float16")

# Queues
audio_queue = queue.Queue()
caption_queue = queue.Queue()


# ---------------- TAB AUDIO CAPTURE (WebSocket) ----------------
import asyncio
import websockets


def start_ws_audio_server():
    import asyncio
    import websockets

    async def audio_handler(websocket):
        print("Tab audio WebSocket connected")
        audio_buffer = np.array([], dtype=np.float32)
        connection_time = time.time()
        message_count = 0
        
        try:
            async for message in websocket:
                try:
                    # Skip empty messages (ping)
                    if len(message) == 0:
                        print("Received ping")
                        continue
                    
                    message_count += 1
                    if message_count % 10 == 0:  # Log every 10th message
                        print(f"Received {message_count} messages in {time.time() - connection_time:.1f}s")
                    
                    # Skip empty messages
                    if len(message) == 0:
                        print("Received empty message")
                        continue

                    # Convert incoming audio data
                    audio = np.frombuffer(message, dtype=np.int16)
                    if len(audio) == 0:
                        print("Received empty audio chunk")
                        continue
                        
                    # Convert to float32 and normalize
                    audio = audio.astype(np.float32)
                    audio = np.clip(audio / 32768.0, -1.0, 1.0)  # Normalize to [-1, 1]
                    
                    # Check audio levels
                    rms = np.sqrt(np.mean(np.square(audio)))
                    if rms < 0.01:  # Very quiet
                        print(f"Skipping quiet audio chunk: RMS = {rms:.3f}")
                        continue
                    
                    print(f"Processing audio chunk: RMS = {rms:.3f}, min = {audio.min():.3f}, max = {audio.max():.3f}")
                    
                    # Accumulate in buffer
                    audio_buffer = np.concatenate([audio_buffer, audio])
                    
                    # Process in chunks of 0.5 seconds
                    chunk_size = SAMPLE_RATE // 2
                    while len(audio_buffer) >= chunk_size:
                        chunk = audio_buffer[:chunk_size]
                        audio_buffer = audio_buffer[chunk_size:]
                        
                        # Reshape to stereo format (2 channels)
                        chunk = chunk.reshape(-1, 1)  # First make it a column
                        chunk = np.repeat(chunk, 2, axis=1)  # Duplicate for stereo
                        
                        # Put chunk in queue for processing
                        audio_queue.put(chunk)
                        print(f"Queued audio chunk of shape: {chunk.shape}")
                        
                except Exception as e:
                    print(f"Error processing audio data: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                    
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed normally")
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            print("WebSocket connection ended")

    def run_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        server = None

        async def start():
            nonlocal server
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    server = await websockets.serve(
                        audio_handler,
                        '127.0.0.1',
                        5010
                    )
                    await asyncio.Future()  # run forever
                    break
                except OSError as e:
                    if e.errno == 10048:  # Address already in use
                        print(f"Port 5010 is in use, waiting for cleanup... (attempt {retry_count + 1}/{max_retries})")
                        await asyncio.sleep(2)  # Wait longer between retries
                        retry_count += 1
                        continue
                    raise
                
            if retry_count >= max_retries:
                print("Failed to bind to port after maximum retries")
                return

        try:
            loop.run_until_complete(start())
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            if server:
                server.close()
                loop.run_until_complete(server.wait_closed())
            loop.close()

    run_server()

# ---------------- TRANSCRIPTION ----------------
def transcribe_audio():
    """Continuously fetch audio and transcribe with context-aware streaming."""
    buffer = np.zeros((0, 2), dtype=np.float32)  # stereo
    chunk_samples = int(SAMPLE_RATE * CHUNK_SEC)  # Convert to integer
    overlap_samples = int(SAMPLE_RATE * OVERLAP_SEC)
    last_text = ""  # for minimal memory trim at chunk boundaries

    while True:
        # Pull queued audio
        while not audio_queue.empty():
            chunk = audio_queue.get()
            print(f"Processing audio chunk of shape: {chunk.shape}")
            buffer = np.concatenate((buffer, chunk))

        # Process chunk if enough samples
        if len(buffer) >= chunk_samples:
            segment = buffer[:chunk_samples]
            buffer = buffer[chunk_samples - overlap_samples:]  # keep small overlap

            # Convert to mono
            mono_audio = np.mean(segment, axis=1).astype(np.float32)
            print(f"Transcribing mono audio of length: {len(mono_audio)}")

            # Transcribe with context memory
            segments, _ = model.transcribe(
                mono_audio,
                language="en",
                beam_size=1,
                vad_filter=True,
                word_timestamps=False,
                condition_on_previous_text=True
            )

            text = " ".join([seg.text for seg in segments]).strip()

            if text:
                # Trim repeated words from chunk boundary
                last_tail = " ".join(last_text.split()[-10:])  # keep last 10 words
                if last_tail and text.startswith(last_tail):
                    text = text[len(last_tail):].strip()

                cleaned = clean_caption(text)
                caption_queue.put(cleaned)
                print(f"[Transcript] {cleaned}")
                last_text += " " + text  # update memory

        time.sleep(0.1)  # small pause to reduce CPU load

# ---------------- FLASK SERVER ----------------
app = Flask(__name__)

@app.route("/get_caption")
def get_caption():
    if not caption_queue.empty():
        return jsonify({"caption": caption_queue.get()})
    return jsonify({"caption": ""})

def start_transcription():
    import threading, time
    # Start tab audio WebSocket server
    threading.Thread(target=start_ws_audio_server, daemon=True).start()
    # Start transcription thread
    threading.Thread(target=transcribe_audio, daemon=True).start()


# ---------------- MAIN ----------------
if __name__ == "__main__":
    start_transcription()
    app.run(port=5000)
