import React from 'react';

export default function IncidentLog({ logs = [] }) {
  const defaultLogs = [
    { id: 1, time: "10:42 AM", type: "SMS", threat: "CRITICAL", target: "State Bank of India" },
    { id: 2, time: "10:45 AM", type: "QR Code", threat: "SAFE", target: "Unknown" }
  ];

  const displayLogs = logs.length > 0 ? logs : defaultLogs;

  return (
    <div className="mt-8 bg-white p-4 rounded shadow-sm border">
      <h2 className="text-xl font-bold mb-4">Cyber Cell Incident Log</h2>
      <table className="min-w-full table-auto border-collapse text-left">
        <thead>
          <tr className="bg-gray-100 border-b">
            <th className="p-2">Timestamp</th>
            <th className="p-2">Source Type</th>
            <th className="p-2">Detected Target</th>
            <th className="p-2">Threat Score</th>
          </tr>
        </thead>
        <tbody>
          {displayLogs.map((log) => (
            <tr key={log.id} className="border-b hover:bg-gray-50">
              <td className="p-2 text-sm text-gray-600">{log.time}</td>
              <td className="p-2 font-medium">{log.type}</td>
              <td className="p-2">{log.target}</td>
              <td className={`p-2 font-bold ${log.threat === 'CRITICAL' ? 'text-red-600' : 'text-green-600'}`}>
                {log.threat}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}