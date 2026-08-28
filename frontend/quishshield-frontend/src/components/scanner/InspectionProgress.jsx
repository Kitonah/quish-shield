import { Check, LoaderCircle, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

const steps = [
  "Checking WHOIS...",
  "Spinning Sandbox...",
  "Analyzing Visuals...",
];

function InspectionProgress({ url, onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep((step) => {
        if (step === steps.length - 1) {
          clearInterval(timer);

          setTimeout(() => {
            onComplete();
          }, 800);

          return step;
        }

        return step + 1;
      });
    }, 1500);

    return () => clearInterval(timer);
  }, [onComplete]);

  return (
    <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-8 backdrop-blur-sm">
      
      {/* Header */}
      <div className="flex flex-col items-center text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-purple-500/10 text-purple-400">
          <ShieldCheck size={28} />
        </div>

        <h2 className="mt-5 text-lg font-semibold text-white">
          Inspecting URL
        </h2>

        <p className="mt-2 max-w-md truncate text-sm text-slate-500">
          {url}
        </p>
      </div>

      {/* Steps */}
      <div className="mx-auto mt-8 max-w-md space-y-3">
        {steps.map((step, index) => {
          const completed = index < currentStep;
          const active = index === currentStep;

          return (
            <div
              key={step}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition ${
                active
                  ? "border-purple-400/20 bg-purple-500/10"
                  : "border-white/5 bg-white/[0.02]"
              }`}
            >
              <div className="flex h-7 w-7 items-center justify-center">
                {completed ? (
                  <Check size={18} className="text-green-400" />
                ) : active ? (
                  <LoaderCircle
                    size={18}
                    className="animate-spin text-purple-400"
                  />
                ) : (
                  <div className="h-2 w-2 rounded-full bg-slate-700" />
                )}
              </div>

              <span
                className={`text-sm ${
                  active || completed
                    ? "text-slate-200"
                    : "text-slate-600"
                }`}
              >
                {step}
              </span>

              {completed && (
                <span className="ml-auto text-xs text-green-400">
                  Complete
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Progress indicator */}
      <div className="mx-auto mt-8 h-1 max-w-md overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-700"
          style={{
            width: `${((currentStep + 1) / steps.length) * 100}%`,
          }}
        />
      </div>

    </div>
  );
}

export default InspectionProgress;