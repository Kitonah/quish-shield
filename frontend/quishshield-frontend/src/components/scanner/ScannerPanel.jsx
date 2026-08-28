import { Image, Link, MessageSquare, Upload } from "lucide-react";
import { useState } from "react";
import InspectionProgress from "./InspectionProgress";
import ScanResult from "./ScanResult";
import { scanQR, scanUrl, scanSMS } from "../../services/scanner";

function ScannerPanel() {
  const [activeMode, setActiveMode] = useState("url");
  const [isScanning, setIsScanning] = useState(false);
  const [scannedUrl, setScannedUrl] = useState("");
  const [scanResult, setScanResult] = useState(null);

  const modes = [
    {
      id: "url",
      label: "URL",
      icon: Link,
    },
    {
      id: "qr",
      label: "QR Code",
      icon: Image,
    },
    {
      id: "sms",
      label: "SMS",
      icon: MessageSquare,
    },
  ];

  return (
    <div className="mt-10 w-full max-w-3xl">

      {/* Scanner modes */}
      <div className="flex rounded-xl border border-white/10 bg-white/5 p-1">
        {modes.map((mode) => {
          const Icon = mode.icon;
          const isActive = activeMode === mode.id;

          return (
            <button
              key={mode.id}
              onClick={() => setActiveMode(mode.id)}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-medium transition ${
                isActive
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Icon size={17} />
              {mode.label}
            </button>
          );
        })}
      </div>

    {/* Scanner content */}
{scanResult ? (
  <ScanResult
    result={scanResult}
    onScanAgain={() => {
      setScanResult(null);
      setScannedUrl("");
      setIsScanning(false);
    }}
  />
) : isScanning ? (
  <InspectionProgress
    url={scannedUrl}
    onComplete={async () => {
      const result = await scanUrl(scannedUrl);

      setIsScanning(false);
      setScanResult(result);
    }}
  />
) : (
  <>
    {activeMode === "url" && (
      <UrlScanner
        onScan={(url) => {
          setScannedUrl(url);
          setIsScanning(true);
        }}
      />
    )}

    {activeMode === "qr" && (
      <QRScanner
        onScan={(url) => {
          setScannedUrl(url);
          setIsScanning(true);
          setScanResult(null);
        }}
      />
    )}

    {activeMode === "sms" && (
  <SMSScanner
    onScan={(url) => {
      setScannedUrl(url);
      setIsScanning(true);
      setScanResult(null);
    }}
  />
)}
  </>
)}
      {/* Supported formats */}
      <p className="mt-4 text-center text-xs text-slate-600">
        Analyze URLs, QR codes, and suspicious SMS messages
      </p>
    </div>
  );
}


/* -------------------------------- */
/* URL Scanner                      */
/* -------------------------------- */

function UrlScanner({ onScan }) {
    const [url, setUrl] = useState("");

  function handleScan() {
    if (!url.trim()) {
      return;
    }

    onScan(url);
  }
  return (
    <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-2 shadow-2xl shadow-purple-950/20 backdrop-blur-sm">
      <div className="flex flex-col gap-3 sm:flex-row">

        <div className="flex flex-1 items-center gap-3 px-4">
          <Link size={20} className="shrink-0 text-slate-500" />

          <input
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleScan();
              }
            }}
            placeholder="Paste a suspicious URL..."
            className="w-full bg-transparent py-3 text-white outline-none placeholder:text-slate-600"
          />
        </div>

        <button onClick={handleScan}className="rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-3 font-medium text-white transition hover:scale-[1.02] hover:shadow-lg hover:shadow-purple-500/20">
          Scan URL
        </button>

      </div>
    </div>
  );
}


/* -------------------------------- */
/* QR Scanner                       */
/* -------------------------------- */

function QRScanner({onScan}) {
  const [selectedImage, setSelectedImage] = useState(null);
  const [qrResult, setQrResult] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [qrError, setQrError] = useState("");

  function handleImageChange(event) {
    const file = event.target.files[0];

    if (!file) {
      return;
    }
    if (selectedImage) {
  URL.revokeObjectURL(selectedImage.preview);
}

    setSelectedImage({
      file,
      preview: URL.createObjectURL(file),
    });

    setQrResult(null);
    setQrError("");
  }

  function handleReset() {
  if (selectedImage) {
    URL.revokeObjectURL(selectedImage.preview);
  }

  setSelectedImage(null);
  setQrResult(null);
  setQrError("");
  setIsScanning(false);
}

  async function handleQRScan() {
  if (!selectedImage) {
    return;
  }

  setIsScanning(true);
  setQrError("");

  try {
    const result = await scanQR(selectedImage.file);

    if (!result.success) {
      setQrError("No QR code could be detected in this image.");
      return;
    }

    setQrResult(result);
  } catch (error) {
    setQrError("Something went wrong while scanning the QR code.");
  } finally {
    setIsScanning(false);
  }
}

  return (
    <div className="mt-3 rounded-2xl border border-dashed border-white/15 bg-white/5 p-8 text-center backdrop-blur-sm">

      {!selectedImage ? (
        <>
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400">
            <Upload size={22} />
          </div>

          <h3 className="font-medium text-white">
            Upload a QR code
          </h3>

          <p className="mt-2 text-sm text-slate-500">
            Choose an image containing a QR code
          </p>

          <label className="mt-5 inline-block cursor-pointer rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white">
            Choose Image

            <input
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              className="hidden"
            />
          </label>
        </>
      ) : (
        <>
          <h3 className="font-medium text-white">
            QR image selected
          </h3>

          <div className="mt-5 flex justify-center">
            <img
              src={selectedImage.preview}
              alt="Selected QR code"
              className="max-h-64 max-w-full rounded-xl border border-white/10 object-contain"
            />
          </div>
        {qrError && (
  <p className="mt-4 text-sm text-red-400">
    {qrError}
  </p>
)}
          {!qrResult && (
            
            <button
              onClick={handleQRScan}
              disabled={isScanning}
              className="mt-5 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 px-5 py-2.5 text-sm font-medium text-white transition hover:scale-[1.02] hover:shadow-lg hover:shadow-purple-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isScanning ? "Scanning QR..." : "Scan QR Code"}
            </button>
          )}

          {qrResult && (
            <div className="mt-6 rounded-xl border border-green-400/10 bg-green-400/5 p-4 text-left">

              {qrResult.type === "url" ? (
  <>
    <p className="text-sm font-medium text-green-300">
      URL detected
    </p>

    <p className="mt-2 break-all text-sm text-slate-400">
      {qrResult.payload}
    </p>

    <button
      onClick={() => onScan(qrResult.payload)}
      className="mt-4 w-full rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 px-5 py-2.5 text-sm font-medium text-white transition hover:scale-[1.02]"
    >
      Analyze URL
    </button>
  </>
) : qrResult.type === "upi" ? (
  <>
    <p className="text-sm font-medium text-yellow-300">
      UPI payment code detected
    </p>

    <p className="mt-2 break-all text-sm text-slate-400">
      {qrResult.payload}
    </p>

    <p className="mt-3 text-xs text-slate-500">
      This QR code contains a UPI payment request rather than a website URL.
    </p>
  </>
) : (
  <p className="text-sm text-red-400">
    Unsupported QR payload detected.
  </p>
)}

<button
  onClick={handleReset}
  className="mt-4 w-full rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
>
  Choose another image
</button>

            </div>
          )}
        </>
      )}

    </div>
  );
}


/* -------------------------------- */
/* SMS Scanner                      */
/* -------------------------------- */

function SMSScanner({ onScan }) {
    const [message, setMessage] = useState("");
const [isScanning, setIsScanning] = useState(false);
const [smsResult, setSmsResult] = useState(null);
const [smsError, setSmsError] = useState("");

async function handleSMSScan() {
  if (!message.trim()) {
    setSmsError("Please enter an SMS message.");
    return;
  }

  setIsScanning(true);
  setSmsError("");

  try {
    const result = await scanSMS(message);

    if (!result.success) {
      setSmsError("No suspicious link could be detected in this message.");
      return;
    }

    setSmsResult(result);
    onScan(result.payload);
  } catch (error) {
    setSmsError("Something went wrong while analyzing the SMS.");
  } finally {
    setIsScanning(false);
  }
}
  return (
    <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-3 backdrop-blur-sm">

      <textarea
  value={message}
  onChange={(event) => setMessage(event.target.value)}
  placeholder="Paste the suspicious SMS message here..."
  rows={5}
  className="w-full resize-none bg-transparent p-3 text-sm text-white outline-none placeholder:text-slate-600"
/>

      <div className="flex justify-end border-t border-white/10 pt-3">
        <button
  onClick={handleSMSScan}
  disabled={isScanning}
  className="rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 px-5 py-2.5 text-sm font-medium text-white transition hover:scale-[1.02] hover:shadow-lg hover:shadow-purple-500/20 disabled:cursor-not-allowed disabled:opacity-50"
>
  {isScanning ? "Scanning SMS..." : "Inspect SMS"}
</button>
      </div>

    </div>
  );
}

export default ScannerPanel;