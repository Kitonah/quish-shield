/**
 * QuishShield Frontend Scanning Client Service
 */

export async function scanUrl(url) {
  const response = await fetch("/api/v1/scan-url", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url: url.trim() }),
  });

  if (!response.ok) {
    let detail = `Scan failed with status ${response.status}`;
    try {
      const error = await response.json();
      detail = error.detail || detail;
    } catch {
      // Retain fallback text if backend did not return JSON
    }
    throw new Error(detail);
  }

  const result = await response.json();

  // Normalize shape so ScanResult.jsx renders reliably
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
    let detail = `QR Scan failed (${response.status})`;
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {
      // Use fallback
    }
    throw new Error(detail);
  }

  return await response.json();
}

export async function scanSMS(message) {
  const response = await fetch("/api/v1/scan-sms", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: message.trim() }),
  });

  if (!response.ok) {
    let detail = `SMS Analysis failed (${response.status})`;
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {
      // Use fallback
    }
    throw new Error(detail);
  }

  const data = await response.json();

  // Map primary_url to .payload so ScannerPanel.jsx can pass it to onScan()
  return {
    ...data,
    payload: data.primary_url || (data.extracted_urls && data.extracted_urls[0]) || null,
  };
}