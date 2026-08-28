const mockScanResult = {
  url: "https://secure-login-example.com",
  status: "dangerous",
  score: 55,

  checks: [
    {
      name: "Domain intelligence",
      status: "dangerous",
      label: "High Risk",
    },
    {
      name: "Sandbox analysis",
      status: "suspicious",
      label: "Suspicious",
    },
    {
      name: "Visual analysis",
      status: "dangerous",
      label: "High Risk",
    },
  ],

  recommendation: "Do not visit this website. It shows multiple signs of phishing.",
};

export default mockScanResult;