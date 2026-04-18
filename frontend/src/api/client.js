const BASE = import.meta.env.VITE_API_BASE_URL;

export async function investigateByAPI(crn) {
  const res = await fetch(`${BASE}/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "api", crn })
  });
  if (!res.ok) {
    let detail = `API error: ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail?.error) detail = body.detail.error;
      else if (typeof body?.detail === "string") detail = body.detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export async function investigateByDocument(pdfFile) {
  const form = new FormData();
  form.append("file", pdfFile);
  form.append("mode", "document");
  const res = await fetch(`${BASE}/investigate`, {
    method: "POST",
    body: form  // NO Content-Type header — browser sets multipart automatically
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function resumeInvestigation(threadId, pdfFile) {
  const form = new FormData();
  form.append("file", pdfFile);
  const res = await fetch(`${BASE}/approve/${threadId}`, {
    method: "POST",
    body: form
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${BASE}/health`);
  return res.json();
}
