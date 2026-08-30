import { useState } from 'react'
import { useOwner } from '../../context/OwnerContext'
import axios from 'axios'

const fmt = (n) =>
  `Rs.${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

const urgencyColor = {
  high:   'bg-red-100 text-red-700',
  medium: 'bg-orange-100 text-orange-700',
  low:    'bg-yellow-100 text-yellow-700',
}

const actionColor = {
  EXIT:   'bg-red-100 text-red-700',
  SWITCH: 'bg-orange-100 text-orange-700',
  REDUCE: 'bg-yellow-100 text-yellow-700',
  HOLD:   'bg-gray-100 text-gray-600',
  ADD:    'bg-green-100 text-green-700',
}

const allocationActionColor = {
  INCREASE: 'text-green-600',
  DECREASE: 'text-red-600',
  MAINTAIN: 'text-gray-600',
}

export default function RebalancePage() {
  const { owner } = useOwner()
  const [report, setReport]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [activeTab, setActiveTab] = useState('summary')

  async function runAnalysis() {
    setLoading(true)
    setError(null)
    setReport(null)
    try {
      const res = await axios.post(`/api/mf/rebalance?owner=${owner}`)
      setReport(res.data)
      setActiveTab('summary')
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio Rebalancing</h1>
          <p className="text-sm text-gray-500 mt-1">
            AI-powered analysis using your holdings, risk profile and fund metadata
          </p>
        </div>
        <button
          onClick={runAnalysis}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
        >
          {loading ? 'Analysing...' : 'Run Analysis'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="text-gray-500 text-sm mb-2">Running portfolio analysis...</div>
          <div className="text-gray-400 text-xs">This takes 10-15 seconds. The AI advisor is reviewing your funds.</div>
        </div>
      )}

      {report && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1">Portfolio Value</div>
              <div className="text-xl font-bold text-gray-900">{fmt(report.total_value)}</div>
              <div className="text-xs text-gray-400 mt-1">P&L: {fmt(report.total_pnl)}</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1">Confidence Score</div>
              <div className={`text-xl font-bold ${report.confidence_score >= 70 ? 'text-green-600' : 'text-orange-600'}`}>
                {report.confidence_score}/100
              </div>
              <div className="text-xs text-gray-400 mt-1">Analysis quality</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1">Funds to Exit</div>
              <div className="text-xl font-bold text-red-600">
                {report.fund_recommendations.filter(r => r.action === 'EXIT').length}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {report.fund_recommendations.filter(r => r.action === 'SWITCH').length} to switch
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1">Report Date</div>
              <div className="text-xl font-bold text-gray-900">
                {new Date(report.report_date).toLocaleDateString('en-GB', {
                  day: '2-digit', month: 'short', year: 'numeric'
                })}
              </div>
              <div className="text-xs text-gray-400 mt-1">{report.owner}</div>
            </div>
          </div>

          <div className="flex gap-4 border-b border-gray-200 mb-6">
            {['summary', 'funds', 'allocation', 'advisor'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-2 text-sm font-medium capitalize border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-900'
                }`}
              >
                {tab === 'funds' ? 'Fund Actions' :
                 tab === 'allocation' ? 'Allocation Plan' :
                 tab === 'advisor' ? 'Advisor Note' : 'Summary'}
              </button>
            ))}
          </div>

          {activeTab === 'summary' && (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-blue-200 p-5">
                <h2 className="font-semibold text-gray-800 mb-2">Executive Summary</h2>
                <p className="text-sm text-gray-700 leading-relaxed">{report.executive_summary}</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-800 mb-3">Key Issues</h2>
                <ol className="space-y-2">
                  {report.key_issues.map((issue, i) => (
                    <li key={i} className="flex gap-3 text-sm text-gray-700">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-100 text-red-700 text-xs flex items-center justify-center font-bold">
                        {i + 1}
                      </span>
                      {issue}
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          )}

          {activeTab === 'funds' && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Action</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Fund</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Reason</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Switch To</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Tax Note</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Urgency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {report.fund_recommendations.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${actionColor[r.action] || 'bg-gray-100 text-gray-600'}`}>
                          {r.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-900 max-w-xs">
                        <div className="text-sm font-medium">{r.fund_name}</div>
                        {r.folio && <div className="text-xs text-gray-400">{r.folio}</div>}
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs max-w-sm">{r.reason}</td>
                      <td className="px-4 py-3 text-xs text-blue-600">{r.switch_to || '—'}</td>
                      <td className="px-4 py-3 text-xs text-orange-600">{r.tax_note || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${urgencyColor[r.urgency] || ''}`}>
                          {r.urgency}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'allocation' && (
            <div className="space-y-3">
              {report.allocation_actions.map((a, i) => (
                <div key={i} className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className={`text-sm font-bold ${allocationActionColor[a.action] || 'text-gray-600'}`}>
                        {a.action}
                      </span>
                      <span className="font-semibold text-gray-800">{a.asset_class}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {a.current_pct.toFixed(1)}% to {a.target_pct.toFixed(1)}%
                      <span className={`ml-2 font-medium ${a.gap_pct > 0 ? 'text-red-500' : 'text-green-600'}`}>
                        ({a.gap_pct > 0 ? '+' : ''}{a.gap_pct.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                  <div className="relative h-2 bg-gray-100 rounded-full mb-3">
                    <div
                      className="absolute h-2 bg-blue-200 rounded-full"
                      style={{ width: `${Math.min(100, a.target_pct)}%` }}
                    />
                    <div
                      className={`absolute h-2 rounded-full ${a.action === 'DECREASE' ? 'bg-red-400' : 'bg-blue-500'}`}
                      style={{ width: `${Math.min(100, a.current_pct)}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-600">{a.how}</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'advisor' && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-800 mb-4">Advisor Explanation</h2>
              {report.advisor_explanation.split('\n\n').map((para, i) => (
                <p key={i} className="text-sm text-gray-700 leading-relaxed mb-4">{para}</p>
              ))}
            </div>
          )}
        </>
      )}

      {!report && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="text-gray-400 text-sm mb-2">No analysis run yet</div>
          <div className="text-gray-300 text-xs">
            Click "Run Analysis" to get AI-powered rebalancing recommendations
          </div>
        </div>
      )}
    </div>
  )
}