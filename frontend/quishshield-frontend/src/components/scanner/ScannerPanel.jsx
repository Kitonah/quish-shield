import { useState, useRef } from "react";
import { Link2, QrCode, MessageSquare, Upload, ArrowRight, ShieldCheck } from "lucide-react";
import { scanUrl, scanQR, scanSMS } from "../../services/scanner";

function ScannerPanel(props) {
  // Find any function prop passed by parent (onScan, onScanUrl, handleSubmit, etc.)
  const possibleCallback =
    props.onScan ||
    props.onScanSubmit ||
    props.onScanUrl ||
    props.onSubmit ||
    props.handleScan ||
    Object.values(props).find((val) => typeof val === "function");

  const [activeTab, setActiveTab] = useState("url");
  const [urlInput, setUrlInput] = useState("");
  const [smsInput, setSmsInput] = useState("");
  const [qrFile, setQrFile] = useState(null);
  const [qrPreview, setQrPreview] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [localLoading, setLocalLoading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const isLoading = props.loading || localLoading;

  const dispatchScan = async (url) => {
    if (typeof possibleCallback === "function") {
      possibleCallback(url);
      return;
    }

    // Direct fallback if parent did not wire up a handler
    try {
      setLocalLoading(true);
      await scanUrl(url);
    } catch (err) {
      setError(err.message || "Failed to analyze target URL.");
    } finally {
      setLocalLoading(false);
    }
  };

  const handleUrlSubmit = (e) => {
    e.preventDefault();
    if (!urlInput.trim()) {
      setError("Please enter a valid URL to analyze.");
      return;
    }
    setError("");
    dispatchScan(urlInput.trim());
  };

  const handleSmsSubmit = async (e) => {
    e.preventDefault();
    if (!smsInput.trim()) {
      setError("Please enter SMS body text.");
      return;
    }
    setError("");
    setLocalLoading(true);
    try {
      const res = await scanSMS(smsInput.trim());
      const target = res.payload || (res.extracted_urls && res.extracted_urls[0]);
      if (!target) {
        setError(res.error || "No links detected inside this SMS message.");
        return;
      }
      dispatchScan(target);
    } catch (err) {
      setError(err.message || "Failed to analyze SMS.");
    } finally {
      setLocalLoading(false);
    }
  };

  const handleFileSelect = (file) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file (PNG, JPG, WEBP).");
      return;
    }
    setError("");
    setQrFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setQrPreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleQrSubmit = async () => {
    if (!qrFile) {
      setError("Please upload an image containing a QR code.");
      return;
    }
    setError("");
    setLocalLoading(true);
    try {
      const res = await scanQR(qrFile);
      if (!res.found && !res.success) {
        setError(res.error || "No QR code could be detected in this image.");
        return;
      }

      const targetPayload = res.resolved_url || res.payload || res.raw_data;
      if (!targetPayload) {
        setError("QR code contained no decodable content.");
        return;
      }

      dispatchScan(targetPayload);
    } catch (err) {
      setError(err.message || "Failed to communicate with QR scanning service.");
    } finally {
      setLocalLoading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl shadow-2xl">
      {/* Vector Navigation Tabs */}
      <div className="flex rounded-2xl bg-black/40 p-1.5 border border-white/5 mb-6">
        <button
          onClick={() => { setActiveTab("url"); setError(""); }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all ${
            activeTab === "url"
              ? "bg-white/15 text-white shadow-lg border border-white/10"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Link2 size={18} />
          URL Scan
        </button>

        <button
          onClick={() => { setActiveTab("qr"); setError(""); }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all ${
            activeTab === "qr"
              ? "bg-white/15 text-white shadow-lg border border-white/10"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <QrCode size={18} />
          QR Code
        </button>

        <button
          onClick={() => { setActiveTab("sms"); setError(""); }}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all ${
            activeTab === "sms"
              ? "bg-white/15 text-white shadow-lg border border-white/10"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <MessageSquare size={18} />
          SMS Smishing
        </button>
      </div>

      {/* Vector Form: URL Scan */}
      {activeTab === "url" && (
        <form onSubmit={handleUrlSubmit} className="space-y-4">
          <div className="relative flex items-center">
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="Paste suspicious target URL (e.g. https://...)"
              className="w-full rounded-2xl border border-white/10 bg-black/40 px-5 py-4 pl-12 text-sm text-white placeholder-slate-500 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition"
            />
            <Link2 className="absolute left-4 text-slate-500" size={18} />
            <button
              type="submit"
              disabled={isLoading}
              className="absolute right-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:opacity-90 transition disabled:opacity-50"
            >
              {isLoading ? "Analyzing..." : "Scan URL"}
            </button>
          </div>
        </form>
      )}

      {/* Vector Form: QR Code Scan */}
      {activeTab === "qr" && (
        <div className="space-y-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 cursor-pointer transition ${
              isDragging
                ? "border-purple-500 bg-purple-500/10"
                : "border-white/10 bg-black/20 hover:border-white/20"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />

            {qrPreview ? (
              <div className="flex flex-col items-center gap-3">
                <img
                  src={qrPreview}
                  alt="QR Preview"
                  className="h-44 w-44 rounded-xl object-contain border border-white/10 bg-white p-2"
                />
                <span className="text-xs text-slate-400">Click or drop to replace image</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/5 border border-white/10">
                  <Upload className="text-slate-400" size={20} />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-200">
                    Click to upload or drag & drop QR image
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Supports PNG, JPG, or Screenshots
                  </p>
                </div>
              </div>
            )}
          </div>

          {qrFile && (
            <button
              onClick={handleQrSubmit}
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 py-3.5 text-sm font-semibold text-white shadow-lg hover:opacity-90 transition disabled:opacity-50"
            >
              {isLoading ? "Decoding & Inspecting..." : "Scan Decoded QR Code"}
              <ArrowRight size={16} />
            </button>
          )}
        </div>
      )}

      {/* Vector Form: SMS Smishing */}
      {activeTab === "sms" && (
        <form onSubmit={handleSmsSubmit} className="space-y-4">
          <textarea
            value={smsInput}
            onChange={(e) => setSmsInput(e.target.value)}
            rows={4}
            placeholder="Paste raw SMS message text containing hyperlinks or KYC warnings..."
            className="w-full rounded-2xl border border-white/10 bg-black/40 p-4 text-sm text-white placeholder-slate-500 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition resize-none"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 py-3.5 text-sm font-semibold text-white shadow-lg hover:opacity-90 transition disabled:opacity-50"
          >
            {isLoading ? "Parsing SMS..." : "Extract & Analyze Smishing Link"}
            <ArrowRight size={16} />
          </button>
        </form>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-center text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Feature Indicators */}
      <div className="mt-6 flex items-center justify-center gap-6 border-t border-white/5 pt-4 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-green-400" />
          Multi-Vector Forensics
        </span>
        <span className="flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-purple-400" />
          Stealth Sandbox
        </span>
        <span className="flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-pink-400" />
          Brand Vision AI
        </span>
      </div>
    </div>
  );
}

export default ScannerPanel;