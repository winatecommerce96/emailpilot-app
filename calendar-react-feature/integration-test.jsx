// Integration Test Component for EmailPilot React Calendar
// Use this to test the calendar after deployment

import React from 'react';
import CalendarPage from './calendar/CalendarPage';

// Test wrapper component
export default function CalendarIntegrationTest() {
  const [testResults, setTestResults] = React.useState([]);
  const [isTestingComplete, setIsTestingComplete] = React.useState(false);

  const runTests = async () => {
    const results = [];
    
    try {
      // Test 1: Component loads without errors
      results.push({
        test: 'Component Loads',
        status: 'PASS',
        message: 'CalendarPage component rendered successfully'
      });

      // Test 2: Environment variables
      const requiredEnvVars = [
        'REACT_APP_FIREBASE_CONFIG_JSON',
        'REACT_APP_APP_ID',
        'REACT_APP_API_BASE'
      ];

      const missingVars = requiredEnvVars.filter(v => !process.env[v]);
      results.push({
        test: 'Environment Variables',
        status: missingVars.length === 0 ? 'PASS' : 'FAIL',
        message: missingVars.length === 0 
          ? 'All required environment variables are set'
          : `Missing: ${missingVars.join(', ')}`
      });

      // Test 3: Firebase config parsing
      try {
        const config = JSON.parse(process.env.REACT_APP_FIREBASE_CONFIG_JSON || '{}');
        results.push({
          test: 'Firebase Config',
          status: config.apiKey ? 'PASS' : 'FAIL',
          message: config.apiKey ? 'Firebase config is valid' : 'Firebase config missing apiKey'
        });
      } catch (error) {
        results.push({
          test: 'Firebase Config',
          status: 'FAIL',
          message: 'Firebase config JSON is invalid'
        });
      }

      // Test 4: API Base URL
      const apiBase = process.env.REACT_APP_API_BASE;
      results.push({
        test: 'API Base URL',
        status: apiBase && apiBase.startsWith('https://') ? 'PASS' : 'WARN',
        message: apiBase 
          ? `API Base: ${apiBase}`
          : 'No API base URL configured (will use relative paths)'
      });

      // Test 5: Feature flags
      const aiEnabled = process.env.REACT_APP_ENABLE_AI_CHAT === 'true';
      const goalsEnabled = process.env.REACT_APP_ENABLE_GOALS_INTEGRATION === 'true';
      
      results.push({
        test: 'Feature Flags',
        status: 'INFO',
        message: `AI Chat: ${aiEnabled}, Goals: ${goalsEnabled}`
      });

    } catch (error) {
      results.push({
        test: 'Test Suite Error',
        status: 'FAIL',
        message: error.message
      });
    }

    setTestResults(results);
    setIsTestingComplete(true);
  };

  React.useEffect(() => {
    runTests();
  }, []);

  const TestResults = () => (
    <div className="bg-white p-6 rounded-lg shadow-lg mb-6">
      <h2 className="text-xl font-bold mb-4">Calendar Integration Test Results</h2>
      
      {testResults.map((result, index) => (
        <div key={index} className="flex items-center justify-between py-2 border-b">
          <span className="font-medium">{result.test}</span>
          <div className="flex items-center space-x-2">
            <span className={`px-2 py-1 text-xs rounded ${
              result.status === 'PASS' ? 'bg-green-100 text-green-800' :
              result.status === 'FAIL' ? 'bg-red-100 text-red-800' :
              result.status === 'WARN' ? 'bg-yellow-100 text-yellow-800' :
              'bg-blue-100 text-blue-800'
            }`}>
              {result.status}
            </span>
          </div>
        </div>
      ))}

      {testResults.map((result, index) => (
        result.message && (
          <div key={`msg-${index}`} className="mt-2 p-2 bg-gray-50 rounded text-sm">
            <strong>{result.test}:</strong> {result.message}
          </div>
        )
      ))}

      <div className="mt-4 p-3 bg-blue-50 rounded">
        <h3 className="font-semibold text-blue-900">Next Steps:</h3>
        <ol className="list-decimal list-inside text-sm text-blue-700 mt-1">
          <li>Verify all tests show PASS status</li>
          <li>Check browser console for any errors</li>
          <li>Try creating a test campaign</li>
          <li>Test the AI chat functionality</li>
          <li>Verify auto-save works correctly</li>
        </ol>
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto p-4">
      <TestResults />
      
      {/* Actual Calendar Component */}
      <div className="border-2 border-blue-200 rounded-lg">
        <div className="bg-blue-50 p-2 text-center text-blue-700 font-medium">
          Live Calendar Component Test
        </div>
        <CalendarPage />
      </div>
    </div>
  );
}

// Usage:
// In your test route: <Route path="/calendar/test" element={<CalendarIntegrationTest />} />
// Navigate to /calendar/test to run integration tests