'use client';

import { useState, useEffect } from 'react';
import CometDial from '@/components/CometDial';
import { apiClient, type Customer, type DamageScenario, type ScenarioResult } from '@/lib/api';

export default function Home() {
  // State
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<string>('');
  const [stormSeverity, setStormSeverity] = useState<'low' | 'medium' | 'high'>('medium');
  const [availableCrews, setAvailableCrews] = useState<number>(4);
  const [accessBlocked, setAccessBlocked] = useState<boolean>(false);
  const [damageScenarios, setDamageScenarios] = useState<DamageScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load customers on mount
  useEffect(() => {
    loadCustomers();
  }, []);

  // Load damage scenarios when customer changes
  useEffect(() => {
    if (selectedCustomer) {
      loadDamageScenarios(selectedCustomer);
    }
  }, [selectedCustomer]);

  // Evaluate scenario when inputs change (debounced)
  useEffect(() => {
    if (selectedCustomer) {
      const timeout = setTimeout(() => {
        evaluateScenario();
      }, 300); // 300ms debounce
      return () => clearTimeout(timeout);
    }
  }, [selectedCustomer, stormSeverity, availableCrews, accessBlocked, selectedScenario]);

  const loadCustomers = async () => {
    try {
      const data = await apiClient.getCustomers();
      setCustomers(data);
      if (data.length > 0) {
        setSelectedCustomer(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load customers:', err);
      setError('Failed to load customers. Using demo mode.');
      // Demo fallback
      setCustomers([
        { id: 'demo1', label: 'Demo Household 1' },
        { id: 'demo2', label: 'Demo Household 2' },
      ]);
      setSelectedCustomer('demo1');
    }
  };

  const loadDamageScenarios = async (customerId: string) => {
    try {
      const data = await apiClient.getDamageScenarios(customerId);
      setDamageScenarios(data);
      if (data.length > 0) {
        setSelectedScenario(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load damage scenarios:', err);
    }
  };

  const evaluateScenario = async () => {
    if (!selectedCustomer) return;

    setLoading(true);
    try {
      const data = await apiClient.evaluateScenario({
        customer_id: selectedCustomer,
        storm_severity: stormSeverity,
        available_crews: availableCrews,
        access_blocked: accessBlocked,
        damage_scenario: selectedScenario,
      });
      setResult(data);
      setError(null);
    } catch (err) {
      console.error('Failed to evaluate scenario:', err);
      setError('Failed to connect to backend. Please ensure the Python API is running on port 8000.');
      // Demo fallback result
      setResult({
        risk_band: 'Moderate',
        evidence_quality: 'Low',
        risk_factors: ['Demo mode - Backend not available', 'Using simulated data'],
        restoration_low_hours: 4.5,
        restoration_high_hours: 8.5,
        restoration_factors: ['Demo estimate', 'Simulated crew availability'],
        preparation_actions: ['Check emergency supplies', 'Charge mobile devices'],
        alert_eligible: true,
        assumptions: ['This is demo data', 'Backend API not connected'],
        source_label: 'DEMO MODE - Backend not connected',
      });
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (band: string) => {
    switch (band) {
      case 'Low':
        return 'text-green-700 bg-green-100 border-green-500';
      case 'Moderate':
        return 'text-yellow-700 bg-yellow-100 border-yellow-500';
      case 'High':
        return 'text-red-700 bg-red-100 border-red-600';
      case 'Critical':
        return 'text-ohio-scarlet bg-red-50 border-ohio-scarlet';
      default:
        return 'text-ohio-grey bg-gray-100 border-ohio-grey';
    }
  };

  const formatWindow = (low: number | null, high: number | null): string => {
    if (low === null || high === null) return 'Unknown';
    if (low === 0 && high === 0) return 'No repairs modeled';
    return `${low.toFixed(1)}–${high.toFixed(1)} hours`;
  };

  return (
    <div className="min-h-screen bg-ohio-light">
      {/* Header */}
      <header className="bg-ohio-scarlet text-white shadow-lg">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold">StormReady</h1>
              <p className="text-red-100 mt-1">AEP AI Outage Concierge — HackOHIO 2026</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="badge bg-white text-ohio-scarlet font-semibold">PROTOTYPE</span>
            </div>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <div className="container mx-auto px-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700">{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Sidebar Controls */}
          <aside className="lg:col-span-4">
            <div className="card-scarlet">
              <h2 className="text-2xl font-bold text-ohio-scarlet mb-6">Scenario Controls</h2>

              {/* Customer Selection */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-ohio-grey mb-2">
                  Household
                </label>
                <select
                  value={selectedCustomer}
                  onChange={(e) => setSelectedCustomer(e.target.value)}
                  className="input-field w-full"
                >
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Storm Severity */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-ohio-grey mb-4">
                  Storm Severity
                </label>
                <div className="flex gap-2">
                  {(['low', 'medium', 'high'] as const).map((severity) => (
                    <button
                      key={severity}
                      onClick={() => setStormSeverity(severity)}
                      className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-all ${
                        stormSeverity === severity
                          ? 'bg-ohio-scarlet text-white shadow-lg'
                          : 'bg-gray-200 text-ohio-grey hover:bg-gray-300'
                      }`}
                    >
                      {severity.charAt(0).toUpperCase() + severity.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Damage Scenario */}
              {damageScenarios.length > 0 && (
                <div className="mb-6">
                  <label className="block text-sm font-semibold text-ohio-grey mb-2">
                    Damage Scenario
                  </label>
                  <select
                    value={selectedScenario || ''}
                    onChange={(e) => setSelectedScenario(e.target.value)}
                    className="input-field w-full"
                  >
                    {damageScenarios.map((scenario) => (
                      <option key={scenario.id} value={scenario.id}>
                        {scenario.label}
                      </option>
                    ))}
                  </select>
                  {damageScenarios.find((s) => s.id === selectedScenario)?.description && (
                    <p className="text-xs text-ohio-grey mt-2">
                      {damageScenarios.find((s) => s.id === selectedScenario)?.description}
                    </p>
                  )}
                </div>
              )}

              {/* Crew Availability - CometDial */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-ohio-grey mb-4 text-center">
                  Available Repair Crews
                </label>
                <div className="flex justify-center">
                  <CometDial
                    value={availableCrews}
                    min={1}
                    max={10}
                    step={1}
                    unit=" crews"
                    label="Available Crews"
                    accent="#BB0000"
                    ink="#666666"
                    size={200}
                    onChange={(value) => setAvailableCrews(value)}
                  />
                </div>
                <p className="text-xs text-ohio-grey text-center mt-2">
                  1 = constrained, 10 = full staffing
                </p>
              </div>

              {/* Access Blocked */}
              <div className="mb-6">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={accessBlocked}
                    onChange={(e) => setAccessBlocked(e.target.checked)}
                    className="w-5 h-5 text-ohio-scarlet border-gray-300 rounded focus:ring-ohio-scarlet"
                  />
                  <span className="ml-3 text-sm font-semibold text-ohio-grey">
                    Access Route Blocked
                  </span>
                </label>
                <p className="text-xs text-ohio-grey ml-8 mt-1">
                  Road damage, flooding, or debris
                </p>
              </div>

              {/* Scenario Summary */}
              <div className="mt-6 p-4 bg-ohio-light rounded-lg">
                <h3 className="font-semibold text-ohio-dark mb-2">Current Scenario</h3>
                <div className="space-y-1 text-sm text-ohio-grey">
                  <div className="flex justify-between">
                    <span>Severity:</span>
                    <span className="font-semibold text-ohio-dark">
                      {stormSeverity.charAt(0).toUpperCase() + stormSeverity.slice(1)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Crews:</span>
                    <span className="font-semibold text-ohio-dark">{availableCrews}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Access:</span>
                    <span className="font-semibold text-ohio-dark">
                      {accessBlocked ? 'Blocked' : 'Clear'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="lg:col-span-8">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ohio-scarlet"></div>
              </div>
            )}

            {result && !loading && (
              <div className="space-y-6">
                {/* Source Label */}
                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
                  <div className="flex items-start">
                    <svg className="h-6 w-6 text-yellow-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="ml-3 text-sm text-yellow-800">{result.source_label}</p>
                  </div>
                </div>

                {/* Top Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="card text-center">
                    <div className="text-sm font-semibold text-ohio-grey mb-2">Outage Risk</div>
                    <div className={`text-3xl font-bold ${getRiskColor(result.risk_band).split(' ')[0]}`}>
                      {result.risk_band}
                    </div>
                  </div>
                  <div className="card text-center">
                    <div className="text-sm font-semibold text-ohio-grey mb-2">Restoration Window</div>
                    <div className="text-2xl font-bold text-ohio-dark">
                      {formatWindow(result.restoration_low_hours, result.restoration_high_hours)}
                    </div>
                  </div>
                  <div className="card text-center">
                    <div className="text-sm font-semibold text-ohio-grey mb-2">Evidence Quality</div>
                    <div className="text-3xl font-bold text-ohio-grey">
                      {result.evidence_quality}
                    </div>
                  </div>
                </div>

                {/* Risk Details */}
                <div className={`card border-2 ${getRiskColor(result.risk_band).split(' ').slice(2).join(' ')}`}>
                  <h3 className="text-xl font-bold text-ohio-dark mb-4">Outage Risk Assessment</h3>
                  <div className={`inline-flex items-center px-4 py-2 rounded-full text-lg font-bold mb-4 ${getRiskColor(result.risk_band)}`}>
                    {result.risk_band} Risk
                  </div>
                  <div className="mt-4">
                    <h4 className="font-semibold text-ohio-grey mb-2">Contributing Factors:</h4>
                    <ul className="space-y-2">
                      {result.risk_factors.map((factor, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="text-ohio-scarlet mr-2">•</span>
                          <span className="text-ohio-dark">{factor}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Restoration Estimate */}
                <div className="card">
                  <h3 className="text-xl font-bold text-ohio-dark mb-4">Restoration Estimate</h3>
                  <div className="text-4xl font-bold text-ohio-scarlet mb-4">
                    {formatWindow(result.restoration_low_hours, result.restoration_high_hours)}
                  </div>
                  <div className="mt-4">
                    <h4 className="font-semibold text-ohio-grey mb-2">Key Factors:</h4>
                    <ul className="space-y-2">
                      {result.restoration_factors.map((factor, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="text-ohio-scarlet mr-2">•</span>
                          <span className="text-ohio-dark">{factor}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                    <p className="text-sm text-yellow-800">
                      ⚠️ <strong>Scenario estimate only.</strong> Actual restoration depends on post-storm
                      damage assessment, crew routing, and conditions not modeled here.
                    </p>
                  </div>
                </div>

                {/* Alert Eligibility */}
                <div className={`card ${result.alert_eligible ? 'border-2 border-green-500' : ''}`}>
                  <h3 className="text-xl font-bold text-ohio-dark mb-4">Alert Eligibility</h3>
                  <div className="flex items-center">
                    <div className={`w-4 h-4 rounded-full mr-3 ${result.alert_eligible ? 'bg-green-500' : 'bg-gray-400'}`}></div>
                    <span className="text-lg font-semibold">
                      {result.alert_eligible ? 'Eligible for prototype alerts' : 'Not eligible for prototype alerts'}
                    </span>
                  </div>
                  <p className="text-sm text-ohio-grey mt-3">
                    {result.alert_eligible
                      ? 'This scenario meets StormReady\'s documented notification criteria. This is not AEP enrollment, program qualification, or guaranteed restoration priority.'
                      : 'This scenario does not meet StormReady\'s prototype notification criteria. Prototype rules only — not an AEP program decision.'}
                  </p>
                </div>

                {/* Preparation Actions */}
                <div className="card-scarlet">
                  <h3 className="text-xl font-bold text-ohio-scarlet mb-4">📋 Preparation Checklist</h3>
                  <div className="space-y-3">
                    {result.preparation_actions.map((action, idx) => (
                      <label key={idx} className="flex items-start cursor-pointer hover:bg-red-50 p-2 rounded-lg transition-colors">
                        <input
                          type="checkbox"
                          className="w-5 h-5 text-ohio-scarlet border-gray-300 rounded focus:ring-ohio-scarlet mt-0.5"
                        />
                        <span className="ml-3 text-ohio-dark">{action}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Assumptions */}
                <details className="card">
                  <summary className="font-bold text-ohio-dark cursor-pointer hover:text-ohio-scarlet">
                    📝 Assumptions & Caveats
                  </summary>
                  <ul className="mt-4 space-y-2">
                    {result.assumptions.map((assumption, idx) => (
                      <li key={idx} className="flex items-start">
                        <span className="text-ohio-grey mr-2">•</span>
                        <span className="text-ohio-dark text-sm">{assumption}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              </div>
            )}
          </main>
        </div>

        {/* Confirmed Information Footer */}
        <footer className="mt-12 border-t border-gray-300 pt-8">
          <div className="card">
            <h2 className="text-2xl font-bold text-ohio-dark mb-4">✅ Confirmed Information</h2>
            <p className="text-sm text-ohio-grey mb-4">Verified facts (not scenario estimates), with sources.</p>
            <ul className="space-y-2 text-ohio-dark">
              <li>
                <strong>Report an AEP Ohio outage:</strong> call{' '}
                <a href="tel:1-800-672-2231" className="text-ohio-scarlet hover:underline font-semibold">
                  1-800-672-2231
                </a>
                {' '}(
                <a
                  href="https://www.aepohio.com/outages/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ohio-scarlet hover:underline"
                >
                  AEP Ohio outages
                </a>
                )
              </li>
              <li>
                <strong>Live outage map:</strong>{' '}
                <a
                  href="https://outagemap.aepohio.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ohio-scarlet hover:underline"
                >
                  AEP Ohio outage map
                </a>
              </li>
            </ul>
            <p className="text-xs text-ohio-grey mt-4">
              StormReady is a student prototype and is not affiliated with AEP. Built for HackOHIO 2026.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
