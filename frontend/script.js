const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const scrollArea = document.getElementById("chat-scroll");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const menuToggle = document.getElementById("menu-toggle");
let isLoading = false;
let activeRequest = null;

function scrollToNewest() {
  scrollArea.scrollTop = scrollArea.scrollHeight;
}

function updateSendButton() {
  sendButton.disabled = isLoading || !input.value.trim();
}

function addMessage(role, text, isError = false) {
  const message = document.createElement("article");
  message.className = `message ${role}${isError ? " error" : ""}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "✧";
  avatar.setAttribute("aria-hidden", "true");
  const content = document.createElement("div");
  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "nexaBot";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  // textContent keeps customer text and model output from becoming executable HTML.
  bubble.textContent = text;
  content.append(label, bubble);
  message.append(avatar, content);
  messages.appendChild(message);
  scrollToNewest();
  return message;
}

function showTypingIndicator() {
  const indicator = addMessage("assistant", "nexaBot is typing");
  indicator.id = "typing-indicator";
  const dots = document.createElement("span");
  dots.className = "typing-dots";
  dots.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 3; i++) dots.appendChild(document.createElement("span"));
  indicator.querySelector(".bubble").appendChild(dots);
}

function removeTypingIndicator() {
  document.getElementById("typing-indicator")?.remove();
}

async function sendMessage(suggestedQuestion) {
  const userMessage = (suggestedQuestion ?? input.value).trim();
  if (!userMessage || isLoading) return;
  welcome.hidden = true;
  input.value = "";
  input.rows = 1;
  isLoading = true;
  updateSendButton();
  setSidebar(false);
  addMessage("user", userMessage);
  showTypingIndicator();
  // A controller prevents a previous answer from appearing after New conversation.
  const controller = new AbortController();
  activeRequest = controller;
  const timeout = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
    if (typeof data.answer !== "string") throw new Error("The server returned an invalid response. Please try again.");
    if (activeRequest !== controller) return;
    removeTypingIndicator();
    addMessage("assistant", data.answer);
  } catch (error) {
    if (activeRequest !== controller) return;
    removeTypingIndicator();
    const text = error.name === "AbortError"
      ? "The request timed out. The model may still be starting. Please try again."
      : error instanceof TypeError || error instanceof SyntaxError
        ? "Couldn't connect to the support service. Check your connection and try again."
        : error.message;
    addMessage("assistant", text, true);
  } finally {
    clearTimeout(timeout);
    if (activeRequest === controller) {
      activeRequest = null;
      isLoading = false;
      updateSendButton();
      input.focus();
    }
  }
}

function clearChat() {
  const previousRequest = activeRequest;
  activeRequest = null;
  previousRequest?.abort();
  isLoading = false;
  messages.replaceChildren();
  welcome.hidden = false;
  input.value = "";
  input.rows = 1;
  updateSendButton();
  setSidebar(false);
  input.focus();
  scrollArea.scrollTop = 0;
}

function setSidebar(open) {
  sidebar.classList.toggle("open", open);
  overlay.hidden = !open;
  menuToggle.setAttribute("aria-expanded", String(open));
  if (open) document.getElementById("new-chat").focus();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage();
});
input.addEventListener("input", () => {
  input.rows = Math.min(4, input.value.split("\n").length);
  updateSendButton();
});
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendMessage();
  }
});
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.question));
});
document.getElementById("new-chat").addEventListener("click", clearChat);
menuToggle.addEventListener("click", () => setSidebar(!sidebar.classList.contains("open")));
overlay.addEventListener("click", () => { setSidebar(false); menuToggle.focus(); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && sidebar.classList.contains("open")) {
    setSidebar(false);
    menuToggle.focus();
  }
});
// Close the mobile drawer when moving back to a desktop layout.
window.matchMedia("(min-width: 761px)").addEventListener("change", (event) => {
  if (event.matches) setSidebar(false);
});
