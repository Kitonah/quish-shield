import React, { useState } from 'react';

export default function QrSmishingTab() {
  const [smsText, setSmsText] = useState('');
  const [qrFile, setQrFile] = useState(null);

  const handleSmsSubmit = (e) => {
    e.preventDefault();
    console.log("Submitting SMS for inspection:", smsText);
  };

  return (
    <div className="p-4 border rounded shadow-sm bg-white">
      <h2 className="text-xl font-bold mb-4">Scanner Input (Member 6)</h2>
      <div className="mb-6">
        <label className="block font-semibold mb-2">Paste Suspicious SMS:</label>
        <textarea 
          className="w-full p-2 border rounded" 
          rows="4" 
          value={smsText}
          onChange={(e) => setSmsText(e.target.value)}
          placeholder="Paste SMS content here..."
        />
        <button 
          onClick={handleSmsSubmit}
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Inspect SMS
        </button>
      </div>
      <hr className="my-4" />
      <div>
        <label className="block font-semibold mb-2">Upload QR Code (Quishing):</label>
        <input 
          type="file" 
          accept="image/*"
          onChange={(e) => setQrFile(e.target.files[0])}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
      </div>
    </div>
  );
}