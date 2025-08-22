// Global variables for managing state
let eventSource = null;
let ws = null;
let isCapturing = false;
let audioCtx = null;
let source = null;
let processor = null;
let audioBuffer = null;
let streamRef = null;  // Keep reference to stream
let lastSendTime = 0;

// Function to cleanup audio resources
function cleanup() {
    console.log('Cleaning up resources...');
    isCapturing = false;
    
    // Clean up audio processing
    if (processor) {
        try {
            processor.disconnect();
        } catch (e) {
            console.error('Error disconnecting processor:', e);
        }
    }
    if (source) {
        try {
            source.disconnect();
        } catch (e) {
            console.error('Error disconnecting source:', e);
        }
    }
    if (audioCtx) {
        try {
            audioCtx.close();
        } catch (e) {
            console.error('Error closing audio context:', e);
        }
    }
    
    // Clean up WebSocket
    if (ws) {
        try {
            ws.close(1000, 'Closing normally');
        } catch (e) {
            console.error('Error closing WebSocket:', e);
        }
    }
    
    // Stop media stream tracks
    if (streamRef) {
        try {
            streamRef.getTracks().forEach(track => track.stop());
        } catch (e) {
            console.error('Error stopping media stream:', e);
        }
    }
    
    // Reset all variables
    audioCtx = null;
    source = null;
    processor = null;
    audioBuffer = null;
    ws = null;
    streamRef = null;
    console.log('Cleanup completed');
}

// Start button handler for captions
document.getElementById("startBtn").onclick = () => {
    if (eventSource) return; // already running
    eventSource = new EventSource("http://127.0.0.1:5000/stream_caption");
    eventSource.onmessage = function(event) {
        if (!event.data) return;
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            chrome.scripting.executeScript({
                target: {tabId: tabs[0].id},
                func: (text) => {
                    let overlay = document.getElementById("realtime-caption");
                    if (!overlay) {
                        overlay = document.createElement("div");
                        overlay.id = "realtime-caption";
                        Object.assign(overlay.style, {
                            position: "fixed",
                            bottom: "10%",
                            left: "50%",
                            transform: "translateX(-50%)",
                            backgroundColor: "rgba(0,0,0,0.7)",
                            color: "white",
                            padding: "8px 15px",
                            borderRadius: "5px",
                            zIndex: "999999",
                            fontSize: "18px",
                            maxWidth: "80%",
                            wordWrap: "break-word",
                            textAlign: "center",
                        });
                        document.body.appendChild(overlay);
                    }
                    overlay.textContent = text;
                },
                args: [event.data]
            });
        });
    };
    eventSource.onerror = function(err) {
        console.log("SSE error:", err);
    };
};

// Stop button handler
document.getElementById("stopBtn").onclick = () => {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    cleanup();
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        chrome.scripting.executeScript({
            target: {tabId: tabs[0].id},
            func: () => {
                const el = document.getElementById("realtime-caption");
                if (el) el.remove();
            }
        });
    });
};

// Audio button handler
document.getElementById("audioBtn").onclick = () => {
    if (isCapturing) {
        console.log('Already capturing audio');
        return;
    }
    
    console.log('Attempting to capture tab audio...');
    chrome.tabCapture.capture({
        audio: true, 
        video: false
    }, function(stream) {
        if (!stream) {
            console.error('Tab audio capture failed');
            return;
        }
        
        try {
            // Setup WebSocket first
            ws = new WebSocket('ws://127.0.0.1:5010');
            ws.binaryType = 'arraybuffer';
            
            ws.onopen = function() {
                console.log('WebSocket connected');
                
                // Ping the server every 5 seconds to keep connection alive
                const pingInterval = setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(new ArrayBuffer(0));  // Empty buffer as ping
                    } else {
                        clearInterval(pingInterval);
                    }
                }, 5000);
                
                try {
                    // Store stream reference
                    streamRef = stream;
                    
                    // Initialize audio context and processing after WebSocket is ready
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 16000
                    });
                    source = audioCtx.createMediaStreamSource(stream);
                    processor = audioCtx.createScriptProcessor(4096, 1, 1);
                    audioBuffer = new Float32Array(0);
                    
                    // Create gain node and analyzer to monitor audio levels
                    const gainNode = audioCtx.createGain();
                    gainNode.gain.value = 1.0;
                    
                    const analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 2048;
                    
                    // Connect the audio graph for both playback and capture
                    // Path 1: source -> gain -> destination (for playback)
                    source.connect(gainNode);
                    gainNode.connect(audioCtx.destination);
                    
                    // Path 2: source -> processor (for capturing)
                    source.connect(processor);
                    
                    // Temporary connection to keep processor alive
                    const silentNode = audioCtx.createGain();
                    silentNode.gain.value = 0;
                    processor.connect(silentNode);
                    silentNode.connect(audioCtx.destination);
                    
                    // Start audio processing
                    // Set capturing flag before setting up processor
                    isCapturing = true;
                    console.log('Audio capture enabled');
                    
                    processor.onaudioprocess = function(e) {
                        if (!isCapturing || !ws || ws.readyState !== WebSocket.OPEN) return;
                        
                        const inputData = e.inputBuffer.getChannelData(0);
                        
                        // Convert to 16-bit PCM
                        const pcmData = new Int16Array(inputData.length);
                        let hasSignal = false;
                        
                        for (let i = 0; i < inputData.length; i++) {
                            // Scale to 16-bit range and clip
                            const s = Math.max(-1, Math.min(1, inputData[i]));
                            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                            if (Math.abs(pcmData[i]) > 200) {  // Threshold to detect non-silence
                                hasSignal = true;
                            }
                        }
                        
                        // Only send if we have actual audio signal
                        if (hasSignal) {
                            try {
                                ws.send(pcmData.buffer);
                                console.log('Sent audio chunk:', {
                                    size: pcmData.length,
                                    min: Math.min(...pcmData),
                                    max: Math.max(...pcmData)
                                });
                            } catch (err) {
                                console.error('WebSocket send error:', err);
                                cleanup();
                            }
                        }
                    };
                    
                    isCapturing = true;
                    console.log('Audio processing started');
                } catch (err) {
                    console.error('Audio setup error:', err);
                    cleanup();
                }
            };
            
            ws.onerror = function(e) {
                console.error('WebSocket error:', e);
                cleanup();
            };
            
            ws.onclose = function() {
                console.log('WebSocket closed');
                cleanup();
            };
            
        } catch (err) {
            console.error('Setup error:', err);
            cleanup();
        }
    });
};
