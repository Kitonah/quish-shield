export async function scanUrl(url) {
  const response = await fetch("/api/v1/scan-url", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    let detail = `Scan failed (${response.status})`;

    try {
      const error = await response.json();
      detail = error.detail || detail;
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }

    throw new Error(detail);
  }

  const result = await response.json();

  return {
    ...result,
    url: result.submitted_url,
    score: result.threat_score,
    status: result.status.toLowerCase(),
  };
}


export async function scanQR(file) {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch("/api/v1/scan-qr", {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw new Error(`QR scan failed (${response.status})`);
  }

  return response.json();
}

export async function scanSMS(message) {
  const response = await fetch("/api/v1/scan-sms", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error(`SMS scan failed (${response.status})`);
  }

  return response.json();
}