console.log("✅ Data Platform Intake Bot injected");

// ---- Create chatbot container ----
const chatbot = document.createElement("div");
chatbot.id = "dpib-chatbot";

chatbot.innerHTML = `
  <div id="dpib-header">
    <div id="dpib-header-title">Data Platform Intake Bot</div>
    <button id="dpib-minimize" title="Minimize">−</button>
  </div>

  <div id="dpib-messages">
    <div class="dpib-bot">
      👋 Hi! I can help you create automated Glue Database PRs.
      <br /><br />
      Try saying: <strong>I want to create a Glue Database PR</strong>
    </div>
  </div>

  <div id="dpib-input-container">
    <input
      id="dpib-input"
      type="text"
      placeholder="Type your message..."
      autocomplete="off"
    />
    <button id="dpib-send">Send</button>
  </div>
`;

// ---- Append to page ----
document.body.appendChild(chatbot);

// ---- Get elements ----
const input = chatbot.querySelector("#dpib-input");
const button = chatbot.querySelector("#dpib-send");
const messages = chatbot.querySelector("#dpib-messages");
const minimizeBtn = chatbot.querySelector("#dpib-minimize");

// ---- Minimize functionality ----
let isMinimized = false;

minimizeBtn.addEventListener("click", () => {
  isMinimized = !isMinimized;

  if (isMinimized) {
    chatbot.classList.add("minimized");
    minimizeBtn.textContent = "□";
    minimizeBtn.title = "Maximize";
  } else {
    chatbot.classList.remove("minimized");
    minimizeBtn.textContent = "−";
    minimizeBtn.title = "Minimize";
  }
});

// ---- Chat logic ----
let conversation = [];

function addMessage(text, className) {
  const div = document.createElement("div");
  div.className = className;
  div.innerHTML = text.replace(/\n/g, "<br />");
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage() {
  const userMessage = input.value.trim();
  if (!userMessage) return;

  addMessage(userMessage, "dpib-user");
  conversation.push({ role: "user", content: userMessage });
  input.value = "";

  // Typing indicator
  const typingDiv = document.createElement("div");
  typingDiv.className = "dpib-bot dpib-typing";
  typingDiv.innerHTML = "<span></span><span></span><span></span>";
  messages.appendChild(typingDiv);
  messages.scrollTop = messages.scrollHeight;

  try {
    const response = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: conversation }),
    });

    typingDiv.remove();

    const data = await response.json();
    addMessage(data.response, "dpib-bot");
    conversation.push({ role: "assistant", content: data.response });

  } catch (err) {
    typingDiv.remove();
    addMessage(
      "⚠️ Backend not reachable. Make sure the server is running on port 8000.",
      "dpib-bot dpib-error"
    );
  }
}

button.addEventListener("click", sendMessage);

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    sendMessage();
  }
});