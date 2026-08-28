import mockScanResult from "../data/mockScan";


export async function scanUrl(url) {
  // Temporary mock.
  // Later this will call Member 1's central analysis API.

  await new Promise((resolve) => setTimeout(resolve, 500));

  return {
    ...mockScanResult,
    url,
  };
}


export async function scanQR(file) {
  // Temporary mock.
  // Later this will send the image to Member 6's FastAPI backend.

  await new Promise((resolve) => setTimeout(resolve, 1000));

  return {
    success: true,
    type: "url",
    payload: "https://secure-login-example.com",
  };
}

export async function scanSMS(message) {
  // Temporary mock.
  // Later this will send the SMS text to Member 6's FastAPI backend.

  await new Promise((resolve) => setTimeout(resolve, 1000));

  return {
    success: true,
    type: "url",
    payload: "https://secure-login-example.com",
  };
}