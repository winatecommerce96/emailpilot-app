import React from 'react';

export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Settings</h1>
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Account Settings</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email Notifications</label>
            <input type="checkbox" className="mt-1" /> Enable email notifications
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">API Key</label>
            <input type="text" className="mt-1 block w-full px-3 py-2 border rounded-md" placeholder="Enter API key" />
          </div>
        </div>
      </div>
    </div>
  );
}