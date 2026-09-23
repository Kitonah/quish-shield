import { AlertTriangle, CheckCircle, ShieldAlert } from "lucide-react";

function ScanResult({ result, onScanAgain }) {
  const isSafe = result.status === "safe";
  const isDangerous =
    result.status === "dangerous" || result.status === "critical_phishing";

  let riskLabel;
  let riskColor;
  let riskBg;

  if (result.score < 30) {
    riskLabel = "LOW RISK";
    riskColor = "text-green-400";
    riskBg = "bg-green-500/10";
  } else if (result.score < 70) {
    riskLabel = "MEDIUM RISK";
    riskColor = "text-yellow-400";
    riskBg = "bg-yellow-500/10";
  } else {
    riskLabel = "HIGH RISK";
    riskColor = "text-red-400";
    riskBg = "bg-red-500/10";
  }

  // Extract nested forensic objects from the upgraded backend schemas
  const heuristics = result.heuristics || {};
  const snapshot = result.snapshot || {};
  const visual = result.visual_match || {};

  return (
    <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-8 backdrop-blur-sm">

      {/* Result Header */}
      <div className="flex flex-col items-center text-center">
        <div className={`flex h-16 w-16 items-center justify-center rounded-2xl ${riskBg} ${riskColor}`}>
          {isSafe ? (
            <CheckCircle size={32} />
          ) : isDangerous ? (
            <ShieldAlert size={32} />
          ) : (
            <AlertTriangle size={32} />
          )}
        </div>

        <h2 className="mt-5 text-2xl font-semibold text-white">
          {result.score < 30
            ? "URL appears safe"
            : result.score < 70
            ? "Suspicious URL detected"
            : "Dangerous URL detected"}
        </h2>

        <p className="mt-2 max-w-lg break-all text-sm text-slate-400">
          {result.url}
        </p>

        {result.detected_brand && (
          <span className="mt-2 inline-flex items-center rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs font-medium text-purple-300">
            Detected Target: {result.detected_brand}
          </span>
        )}
      </div>

      {/* Threat Score Card */}
      <div className="mx-auto mt-8 max-w-md rounded-2xl border border-white/10 bg-black/20 p-6">
        <div className="text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Composite Threat Score
          </p>

          <div className="mt-3">
            <span className="text-6xl font-bold text-white">
              {result.score}
            </span>
            <span className="ml-1 text-xl text-slate-500">
              /100
            </span>
          </div>

          <p className={`mt-2 text-sm font-semibold ${riskColor}`}>
            {riskLabel}
          </p>
        </div>

        {/* Dynamic Risk Bar */}
        <div className="mt-6">
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500 transition-all duration-1000"
              style={{
                width: `${Math.max(result.score, 4)}%`,
              }}
            />
          </div>

          <div className="mt-2 flex justify-between text-xs text-slate-600">
            <span>Safe (0)</span>
            <span>Suspicious (30)</span>
            <span>Dangerous (70+)</span>
          </div>
        </div>
      </div>

      {/* Multi-Pillar Forensic Telemetry */}
      <div className="mx-auto mt-6 max-w-md space-y-3">
        {/* Pillar 1: Domain Intelligence */}
        <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
          <div className="flex flex-col text-left">
            <span className="text-sm text-slate-300">Domain & RDAP Intelligence</span>
            <span className="text-xs text-slate-500">
              Entropy: {heuristics.entropy || 0.0} | Age: {heuristics.domain_age_days ? `${heuristics.domain_age_days}d` : "Unknown"}
            </span>
          </div>

          <span
            className={`text-xs font-medium ${
              (heuristics.heuristic_score || 0) < 20
                ? "text-green-400"
                : (heuristics.heuristic_score || 0) < 45
                ? "text-yellow-400"
                : "text-red-400"
            }`}
          >
            {(heuristics.heuristic_score || 0) < 20
              ? "Safe"
              : (heuristics.heuristic_score || 0) < 45
              ? "Suspicious"
              : "High Risk"}
          </span>
        </div>

        {/* Pillar 2: Headless Sandbox */}
        <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
          <div className="flex flex-col text-left">
            <span className="text-sm text-slate-300">Sandbox DOM Analysis</span>
            <span className="text-xs text-slate-500">
              Latency: {snapshot.load_time_ms ? `${snapshot.load_time_ms}ms` : "N/A"}
            </span>
          </div>

          <span
            className={`text-xs font-medium ${
              snapshot.has_credential_inputs || snapshot.is_security_interstitial
                ? "text-red-400"
                : "text-green-400"
            }`}
          >
            {snapshot.is_security_interstitial
              ? "Interstitial Detected"
              : snapshot.has_credential_inputs
              ? "Credential Harvester"
              : "Safe Form DOM"}
          </span>
        </div>

        {/* Pillar 3: Visual Classification */}
        <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
          <div className="flex flex-col text-left">
            <span className="text-sm text-slate-300">Visual CNN Analysis</span>
            <span className="text-xs text-slate-500">
              Method: {visual.detection_method || "none"}
            </span>
          </div>

          <span
            className={`text-xs font-medium ${
              visual.is_visual_spoof ? "text-red-400" : "text-green-400"
            }`}
          >
            {visual.is_visual_spoof ? "Brand Spoof" : "Authentic Visuals"}
          </span>
        </div>
      </div>

      {/* Triggered Heuristics Flags */}
      {heuristics.flags && heuristics.flags.length > 0 && (
        <div className="mx-auto mt-4 max-w-md rounded-xl border border-white/10 bg-black/30 p-4 text-left">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Detected Security Flags
          </p>
          <ul className="mt-2 space-y-1 text-xs text-slate-300">
            {heuristics.flags.map((flag, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-red-400">•</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      <div
        className={`mx-auto mt-6 max-w-md rounded-xl border p-4 text-left ${
          result.score < 30
            ? "border-green-400/10 bg-green-400/5"
            : result.score < 70
            ? "border-yellow-400/10 bg-yellow-400/5"
            : "border-red-400/10 bg-red-400/5"
        }`}
      >
        <p
          className={`text-sm font-medium ${
            result.score < 30
              ? "text-green-300"
              : result.score < 70
              ? "text-yellow-300"
              : "text-red-300"
          }`}
        >
          Recommended Action
        </p>

        <p className="mt-1 text-sm text-slate-400">
          {result.score < 30
            ? "This URL appears authentic with verified domain registration. Always verify the address bar before entering credentials."
            : result.score < 70
            ? "Proceed with caution. Anomalous domain age or suspicious keywords were detected in the URL structure."
            : "Do not visit this site or provide any personal details. The page demonstrates clear signs of brand impersonation or credential harvesting."}
        </p>
      </div>

      {/* Scan Again Button */}
      <div className="mt-8 flex justify-center">
        <button
          onClick={onScanAgain}
          className="rounded-xl border border-white/10 bg-white/5 px-6 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
        >
          Scan Another URL
        </button>
      </div>

    </div>
  );
}

export default ScanResult;