// content.js
let overlay = null;

function createOverlay() {
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
}

function updateCaption(text) {
    createOverlay();
    overlay.textContent = text; // always replace old caption
}





// --- Caption Overlay via SSE (unchanged) ---
function startCaptionStream() {
    const eventSource = new EventSource("http://127.0.0.1:5000/stream_caption");
    eventSource.onmessage = function(event) {
        if (event.data && event.data.trim() !== "") {
            updateCaption(event.data);
        }
    };
    eventSource.onerror = function(err) {
        console.log("SSE error:", err);
    };
}

startCaptionStream();
