import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import ScannerPanel from "../components/scanner/ScannerPanel";
import ScanResult from "../components/scanner/ScanResult";
import { scanUrl } from "../services/scanner";

function Home() {
  const [loading, setLoading] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState("");

  const handleScan = async (targetUrl) => {
    setLoading(true);
    setScanError("");
    try {
      const result = await scanUrl(targetUrl);
      setScanResult(result);
    } catch (err) {
      setScanError(err.message || "Failed to complete security scan.");
    } finally {
      setLoading(false);
    }
  };

  const handleScanAgain = () => {
    setScanResult(null);
    setScanError("");
  };

  return (
    <main className="relative overflow-hidden">
      {/* Background glow */}
      <div className="pointer-events-none absolute left-1/2 top-0 -z-10 h-125 w-125 -translate-x-1/2 rounded-full bg-purple-600/10 blur-3xl" />

      <section className="mx-auto flex min-h-[calc(100vh-73px)] max-w-5xl flex-col items-center justify-center px-6 py-20 text-center">
        {/* Small badge */}
        <div className="mb-6 flex items-center gap-2 rounded-full border border-purple-400/20 bg-purple-500/10 px-4 py-2 text-sm text-purple-300">
          <ShieldCheck size={16} />
          <span>Real-time threat detection</span>
        </div>

        {/* Heading */}
        <h1 className="text-5xl font-bold tracking-tight sm:text-7xl lg:text-8xl">
          Quish
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Shield
          </span>
        </h1>

        {/* Description */}
        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">
          Detect phishing threats before they reach you. Analyze suspicious URLs with domain
          intelligence, sandbox inspection, and visual threat detection.
        </p>

        {/* Main Content: Scanner or Scan Result */}
        <div className="mt-8 w-full max-w-3xl">
          {scanResult ? (
            <ScanResult result={scanResult} onScanAgain={handleScanAgain} />
          ) : (
            <ScannerPanel onScan={handleScan} loading={loading} />
          )}

          {scanError && (
            <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-center text-sm text-red-400">
              {scanError}
            </div>
          )}
        </div>

        {/* Trust indicators (hidden while viewing results to keep viewport clean) */}
        {!scanResult && (
          <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm text-slate-500">
            <span>✓ Domain intelligence</span>
            <span>✓ Sandbox analysis</span>
            <span>✓ Visual detection</span>
          </div>
        )}
      </section>
    </main>
  );
}

export default Home;