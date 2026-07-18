const KEY = "mca_conversations_v1";

function readAll() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeAll(data) {
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    // storage full or unavailable — fail silently, conversation still works in-session
  }
}

export function saveConversation(id, title, messages) {
  const all = readAll();
  all[id] = {
    id,
    title: title || "Untitled",
    messages,
    updatedAt: Date.now(),
  };
  writeAll(all);
}

export function loadConversation(id) {
  const all = readAll();
  return all[id]?.messages || [];
}

export function listConversations() {
  const all = readAll();
  return Object.values(all).sort((a, b) => b.updatedAt - a.updatedAt);
}

export function deleteConversation(id) {
  const all = readAll();
  delete all[id];
  writeAll(all);
}
