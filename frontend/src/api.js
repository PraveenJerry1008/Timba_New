const BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export async function sendChat({ message, language, childName, childAge, history }) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      language,
      child_name: childName,
      child_age: childAge,
      history,
    }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}
