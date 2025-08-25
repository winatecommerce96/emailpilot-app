import React from 'react';

export default function ReportsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Reports</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2">Campaign Performance</h3>
          <p className="text-gray-600">View detailed analytics for your campaigns</p>
        </div>
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2">Revenue Metrics</h3>
          <p className="text-gray-600">Track revenue and conversion rates</p>
        </div>
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2">Engagement Stats</h3>
          <p className="text-gray-600">Monitor open rates and click-through rates</p>
        </div>
      </div>
    </div>
  );
}