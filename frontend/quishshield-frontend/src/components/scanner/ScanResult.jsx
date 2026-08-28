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

  return (
    <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-8 backdrop-blur-sm">

      {/* Result header */}
      <div className="flex flex-col items-center text-center">

        <div
  className={`flex h-16 w-16 items-center justify-center rounded-2xl ${riskBg} ${riskColor}`}
>
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

        <p className="mt-2 max-w-lg break-all text-sm text-slate-500">
          {result.url}
        </p>

      </div>

      {/* Threat score */}
      {/* Threat score */}
<div className="mx-auto mt-8 max-w-md rounded-2xl border border-white/10 bg-black/20 p-6">

  <div className="text-center">

    <p className="text-sm font-medium uppercase tracking-wider text-slate-500">
      Threat Score
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

  {/* Score bar */}
  <div className="mt-6">

    <div className="h-2 overflow-hidden rounded-full bg-white/10">
      <div
        className="h-full rounded-full bg-gradient-to-r from-yellow-400 to-red-500 transition-all duration-1000"
        style={{
          width: `${result.score}%`,
        }}
      />
    </div>

    <div className="mt-2 flex justify-between text-xs text-slate-600">
      <span>Safe</span>
      <span>Dangerous</span>
    </div>

  </div>

</div>

      {/* Scan details */}
      {/* Scan details */}
<div className="mx-auto mt-6 max-w-md space-y-3">

  <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
    <span className="text-sm text-slate-300">
      Domain intelligence
    </span>

    <span
      className={`text-xs font-medium ${
        result.score < 30
          ? "text-green-400"
          : result.score < 70
            ? "text-yellow-400"
            : "text-red-400"
      }`}
    >
      {result.score < 30
        ? "Safe"
        : result.score < 70
          ? "Suspicious"
          : "High Risk"}
    </span>
  </div>

  <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
    <span className="text-sm text-slate-300">
      Sandbox analysis
    </span>

    <span
      className={`text-xs font-medium ${
        result.score < 30
          ? "text-green-400"
          : result.score < 70
            ? "text-yellow-400"
            : "text-red-400"
      }`}
    >
      {result.score < 30
        ? "Safe"
        : result.score < 70
          ? "Suspicious"
          : "High Risk"}
    </span>
  </div>

  <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
    <span className="text-sm text-slate-300">
      Visual analysis
    </span>

    <span
      className={`text-xs font-medium ${
        result.score < 30
          ? "text-green-400"
          : result.score < 70
            ? "text-yellow-400"
            : "text-red-400"
      }`}
    >
      {result.score < 30
        ? "Safe"
        : result.score < 70
          ? "Suspicious"
          : "High Risk"}
    </span>
  </div>

</div>

      {/* Recommendation */}
<div
  className={`mx-auto mt-6 max-w-md rounded-xl border p-4 ${
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
    Recommended action
  </p>

  <p className="mt-1 text-sm text-slate-400">
    {result.score < 30
      ? "This URL appears safe, but always verify the website before entering sensitive information."
      : result.score < 70
        ? "Proceed with caution. Avoid entering personal or financial information unless you can verify the website."
        : "Do not visit this website or enter any personal information. The URL shows strong signs of phishing."}
  </p>
</div>

      {/* Scan again */}
      <div className="mt-8 flex justify-center">
        <button
          onClick={onScanAgain}
          className="rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
        >
          Scan another URL
        </button>
      </div>

    </div>
  );
}

export default ScanResult;