const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

// Turn any backend/network problem into a readable sentence.
function readableError(status, detail) {
  if (status === 503) {
    return "All AI providers are unavailable right now. Please try again in a moment.";
  }
  if (status === 422) {
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0];
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "input";
      return `Your message could not be sent (${field}: ${first.msg}).`;
    }
    return "Your message could not be sent. Check that it is 1 to 4000 characters.";
  }
  if (typeof detail === "string") return detail;
  return `Something went wrong (error ${status}). Please try again.`;
}

export async function sendChat({ sessionId, message, systemPrompt, simulateFailure }) {
  const headers = { "Content-Type": "application/json" };
  if (simulateFailure) headers["X-Simulate-Failure"] = simulateFailure;

  const body = { session_id: sessionId, message };
  if (systemPrompt && systemPrompt.trim()) body.system_prompt = systemPrompt.trim();

  let res;
  try {
    res = await fetch(`${API_URL}/chat`, { method: "POST", headers, body: JSON.stringify(body) });
  } catch {
    throw new Error("Cannot reach the server. Check your connection and try again.");
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) throw new Error(readableError(res.status, data && data.detail));
  return data;
}
