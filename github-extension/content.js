/**
 * Data Platform Intake Bot - Chrome Extension Content Script
 * Injects chatbot UI into GitHub pages
 */

console.log("✅ Data Platform Intake Bot extension loaded");

// =========================================================
// Create Chatbot UI
// =========================================================
const chatbot = document.createElement("div");
chatbot.id = "dpib-chatbot";

chatbot.innerHTML = `
  <div id="dpib-header">
    <span>Data Platform Intake Bot</span>
    <button id="dpib-minimize">−</button>
  </div>
  <div id="dpib-messages">
    <div class="dpib-bot">
      👋 Hi! I'm the Data Platform Intake Bot.
      <br /><br />
      I can help you create automated <strong>Glue Database Pull Requests</strong>.
      <br /><br />
      Try saying: <em>"I want to create a Glue Database PR"</em>
    </div>
  </div>
  <div id="dpib-input-container">
    <input
      type="text"
      id="dpib-input"
      placeholder="Type your message..."
      autocomplete="off"
    />
    <button id="dpib-send">Send</button>
  </div>
`;

// Append chatbot to page
document.body.appendChild(chatbot);

// =========================================================
// DOM Elements
// =========================================================
const input = document.getElementById("dpib-input");
const sendButton = document.getElementById("dpib-send");
const messagesContainer = document.getElementById("dpib-messages");
const minimizeButton = document.getElementById("dpib-minimize");

// =========================================================
// State Management
// =========================================================
let conversation = [];
let isMinimized = false;

// API endpoint - update this if deploying to production
const API_ENDPOINT = "http://127.0.0.1:8000/chat";

// =========================================================
// UI Functions
// =========================================================

/**
 * Add a message to the chat UI
 */
function addMessage(text, className) {
  const messageDiv = document.createElement("div");
  messageDiv.className = className;

  // Convert newlines to <br> and preserve formatting
  messageDiv.innerHTML = text
    .replace(/\n/g, '<br />')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>');

  messagesContainer.appendChild(messageDiv);

  // Auto-scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "dpib-bot dpib-typing";
  typingDiv.id = "dpib-typing-indicator";
  typingDiv.innerHTML = `
    <span></span>
    <span></span>
    <span></span>
  `;
  messagesContainer.appendChild(typingDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator() {
  const typingDiv = document.getElementById("dpib-typing-indicator");
  if (typingDiv) {
    typingDiv.remove();
  }
}

/**
 * Disable input while processing
 */
function setInputEnabled(enabled) {
  input.disabled = !enabled;
  sendButton.disabled = !enabled;
  sendButton.textContent = enabled ? "Send" : "...";
}

/**
 * Toggle minimize/maximize
 */
function toggleMinimize() {
  isMinimized = !isMinimized;
  const messagesDiv = document.getElementById("dpib-messages");
  const inputContainer = document.getElementById("dpib-input-container");

  if (isMinimized) {
    messagesDiv.style.display = "none";
    inputContainer.style.display = "none";
    minimizeButton.textContent = "+";
    chatbot.style.height = "50px";
  } else {
    messagesDiv.style.display = "flex";
    inputContainer.style.display = "flex";
    minimizeButton.textContent = "−";
    chatbot.style.height = "500px";
  }
}

// =========================================================
// Chat Logic
// =========================================================

/**
 * Send user message and get bot response
 */
async function sendMessage() {
  const userMessage = input.value.trim();

  // Ignore empty messages
  if (!userMessage) return;

  // Add user message to UI
  addMessage(userMessage, "dpib-user");

  // Add to conversation history
  conversation.push({ role: "user", content: userMessage });

  // Clear input
  input.value = "";

  // Disable input while processing
  setInputEnabled(false);

  // Show typing indicator
  showTypingIndicator();

  try {
    // Call backend API
    const response = await fetch(API_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ messages: conversation }),
    });

    // Remove typing indicator
    removeTypingIndicator();

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Add bot response to UI
    addMessage(data.response, "dpib-bot");

    // Add to conversation history
    conversation.push({ role: "assistant", content: data.response });

    // If PR was successfully created, optionally reset conversation
    if (data.tool_used && data.response.includes("✅")) {
      // Optionally clear conversation after successful PR
      // conversation = [];

      // Add success indicator or confetti animation
      console.log("PR created successfully!");
    }

  } catch (error) {
    // Remove typing indicator
    removeTypingIndicator();

    // Show error message
    let errorMessage = "⚠️ Unable to connect to the backend.";

    if (error.message.includes("Failed to fetch")) {
      errorMessage += "\n\nMake sure the server is running on http://127.0.0.1:8000";
    } else {
      errorMessage += `\n\nError: ${error.message}`;
    }

    addMessage(errorMessage, "dpib-bot dpib-error");

    console.error("Chat error:", error);
  } finally {
    // Re-enable input
    setInputEnabled(true);

    // Focus input for next message
    input.focus();
  }
}

// =========================================================
// Event Listeners
// =========================================================

// Send button click
sendButton.addEventListener("click", sendMessage);

// Enter key in input
input.addEventListener("keypress", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});

// Minimize/maximize button
minimizeButton.addEventListener("click", toggleMinimize);

// Focus input on load
input.focus();

// =========================================================
// Keyboard Shortcuts (Optional)
// =========================================================

// Alt+I to focus chatbot input
document.addEventListener("keydown", (event) => {
  if (event.altKey && event.key === "i") {
    event.preventDefault();

    if (isMinimized) {
      toggleMinimize();
    }

    input.focus();
  }
});

console.log("✅ Data Platform Intake Bot ready!");
console.log("💡 Tip: Press Alt+I to focus the chatbot");