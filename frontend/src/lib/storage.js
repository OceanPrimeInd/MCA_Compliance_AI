import { supabase } from "./supabase";

// Server-side conversation storage in Supabase Postgres. Row Level Security
// (set up in supabase/migrations/001_conversations.sql) means these queries
// only ever touch the logged-in user's own rows — userId is passed through
// for clarity, but Supabase enforces the real boundary, not this code.

export async function saveConversation(userId, userEmail, id, title, messages) {
  const { error } = await supabase
    .from("conversations")
    .upsert({
      id,
      user_id: userId,
      user_email: userEmail,
      title: title || "Untitled",
      messages,
      updated_at: new Date().toISOString(),
    });
  if (error) console.error("saveConversation failed:", error.message);
}

export async function loadConversation(userId, id) {
  const { data, error } = await supabase
    .from("conversations")
    .select("messages")
    .eq("id", id)
    .eq("user_id", userId)
    .single();
  if (error) {
    console.error("loadConversation failed:", error.message);
    return [];
  }
  return data?.messages || [];
}

export async function listConversations(userId) {
  const { data, error } = await supabase
    .from("conversations")
    .select("id, title, updated_at")
    .eq("user_id", userId)
    .order("updated_at", { ascending: false });
  if (error) {
    console.error("listConversations failed:", error.message);
    return [];
  }
  return data.map((row) => ({
    id: row.id,
    title: row.title,
    updatedAt: new Date(row.updated_at).getTime(),
  }));
}

export async function deleteConversation(userId, id) {
  const { error } = await supabase
    .from("conversations")
    .delete()
    .eq("id", id)
    .eq("user_id", userId);
  if (error) console.error("deleteConversation failed:", error.message);
}
