document.addEventListener("DOMContentLoaded", () => {
    const scriptEditor = document.getElementById("scriptEditor");
    const wordCount = document.getElementById("wordCount");
    const charCount = document.getElementById("charCount");
    const estDuration = document.getElementById("estDuration");
    
    // Narrators speak roughly 130 - 150 words per minute (WPM).
    const WPM = 140;

    if (scriptEditor) {
        scriptEditor.addEventListener("input", (e) => {
            const text = e.target.value.trim();
            const words = text ? text.split(/\s+/).length : 0;
            const chars = text.length;
            
            wordCount.textContent = words;
            charCount.textContent = chars;
            
            // Duration calculation
            const durationSec = Math.round((words / WPM) * 60);
            estDuration.textContent = durationSec + "s";
        });
    }
});

// Helper to get CSRF token from cookies
function getCsrfToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === 'csrftoken=') {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

// Show feedback toasts
function showToast(message, type = "success") {
    const toastEl = document.getElementById('liveToast');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');
    
    if (toastEl) {
        toastTitle.textContent = type === "success" ? "Notification" : "Engine Alert";
        toastBody.textContent = message;
        
        // Remove existing border classes
        toastEl.classList.remove('border-success', 'border-danger', 'border-warning');
        if (type === "success") {
            toastEl.classList.add('border-success');
        } else if (type === "danger") {
            toastEl.classList.add('border-danger');
        } else {
            toastEl.classList.add('border-warning');
        }

        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
}

// Trigger TTS job submission
function startGeneration(projectId) {
    const scriptEditor = document.getElementById("scriptEditor");
    const speakerSelect = document.getElementById("speakerSelect");
    const generateBtn = document.getElementById("generateBtn");
    
    if (!scriptEditor || !scriptEditor.value.trim()) {
        showToast("Please input some script text before generating.", "danger");
        return;
    }
    
    const text = scriptEditor.value.trim();
    const speaker = speakerSelect ? speakerSelect.value : "p266";
    
    generateBtn.disabled = true;
    generateBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> Enqueuing job...`;

    const formData = new FormData();
    formData.append("script_text", text);
    formData.append("speaker", speaker);
    formData.append("csrfmiddlewaretoken", getCsrfToken());

    fetch(`/engine/generate/${projectId}/`, {
        method: "POST",
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("HTTP error " + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'queued') {
            showToast("Job added to local execution queue!");
            // Reload page or append item to history list
            // Let's reload to fetch new queued row, and begin polling automatically
            location.reload();
        } else {
            resetButton();
            showToast("Failed to queue generation.", "danger");
        }
    })
    .catch(err => {
        resetButton();
        showToast("Communication error with local engine. " + err.message, "danger");
    });
}

function resetButton() {
    const generateBtn = document.getElementById("generateBtn");
    if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.innerHTML = `<i class="bi bi-lightning-charge-fill me-1"></i> Generate Audio ⚡`;
    }
}

// Poll queued/processing audios
function pollJobStatus(audioId) {
    const widget = document.getElementById(`audio-widget-container-${audioId}`);
    
    const interval = setInterval(() => {
        fetch(`/engine/status/${audioId}/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'COMPLETED') {
                clearInterval(interval);
                if (widget) {
                    widget.innerHTML = `
                        <audio src="${data.audio_url}" controls class="w-100" style="height: 32px;"></audio>
                        <span class="text-secondary small ms-2">${data.duration}s</span>
                    `;
                }
                showToast("Voice generation complete!");
                // Optionally reload after a brief delay to refresh full context if needed
                setTimeout(() => location.reload(), 1000);
            } else if (data.status === 'FAILED') {
                clearInterval(interval);
                if (widget) {
                    widget.innerHTML = `
                        <span class="badge bg-danger-subtle text-danger border border-danger-subtle py-1" title="${data.error_message}">
                            Failed
                        </span>
                    `;
                }
                showToast("Voice generation failed: " + data.error_message, "danger");
            } else if (data.status === 'PROCESSING') {
                if (widget) {
                    widget.innerHTML = `
                        <div class="d-flex align-items-center text-warning gap-2 small py-1">
                            <span class="spinner-border spinner-border-sm" role="status"></span>
                            <span>Synthesizing...</span>
                        </div>
                    `;
                }
            }
        })
        .catch(err => {
            clearInterval(interval);
            console.error("Polling error:", err);
        });
    }, 1500);
}

// Scan document on load for any pending/processing rows to keep polling them
document.addEventListener("DOMContentLoaded", () => {
    const historyList = document.getElementById("historyList");
    if (historyList) {
        // Find all rows that are currently NOT completed or failed
        const divs = historyList.querySelectorAll("[id^='audio-row-']");
        divs.forEach(div => {
            const audioId = div.id.replace("audio-row-", "");
            const widget = document.getElementById(`audio-widget-container-${audioId}`);
            if (widget) {
                // If contains 'processing' or 'queued' text/indicator
                if (widget.innerHTML.includes("Queued") || widget.innerHTML.includes("Synthesizing")) {
                    pollJobStatus(audioId);
                }
            }
        });
    }
});

// View logs inside modal
function loadLogs(audioId) {
    const modalTitle = document.getElementById("logsModalLabel");
    const procTime = document.getElementById("logProcTime");
    const sysDetails = document.getElementById("logSysDetails");
    const consoleOutput = document.getElementById("logConsoleOutput");
    
    procTime.textContent = "Loading...";
    sysDetails.textContent = "...";
    consoleOutput.textContent = "> Connecting to history logs...";

    // Trigger modal load
    const myModal = new bootstrap.Modal(document.getElementById('logsModal'));
    myModal.show();

    fetch(`/engine/history/${audioId}/logs/`)
    .then(res => res.json())
    .then(data => {
        procTime.textContent = data.processing_time.toFixed(2) + "s";
        sysDetails.textContent = data.system_details;
        consoleOutput.textContent = data.log_content;
    })
    .catch(err => {
        consoleOutput.textContent = "[Error] Failed to fetch console logs:\n" + err.message;
    });
}

// Delete audio segment
function deleteAudio(audioId) {
    if (confirm("Are you sure you want to delete this generated audio track?")) {
        fetch(`/engine/audio/${audioId}/delete/`, {
            method: "POST",
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
            },
            body: new URLSearchParams({
                'ajax': 'true'
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'deleted') {
                const row = document.getElementById(`audio-row-${audioId}`);
                if (row) {
                    row.remove();
                }
                showToast("Audio track deleted successfully.");
                
                // If list is empty, show empty message
                const historyList = document.getElementById("historyList");
                if (historyList && historyList.children.length === 0) {
                    historyList.innerHTML = `
                        <div class="text-center py-5 text-secondary" id="emptyHistoryMsg">
                            <i class="bi bi-music-note fs-2 mb-2 d-block"></i>
                            <p class="small mb-0">No audio drafts generated for this project.</p>
                        </div>
                    `;
                }
            } else {
                showToast("Delete request failed.", "danger");
            }
        })
        .catch(err => {
            showToast("Failed to communicate with engine for delete.", "danger");
        });
    }
}
