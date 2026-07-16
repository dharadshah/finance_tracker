import { useEffect, useState, useMemo } from 'react'
import axios from 'axios'

export default function MFInvestmentTrackerPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    axios.get('/api/mf/investment-summary')
      .then((r) => setRows(r.data))
      .catch(() => setError('Failed to load investment summary'))
      .finally(() => setLoading(false))
  }, [])

  const totalInvestment = useMemo(() => rows.reduce((s, r) => s + r.investment, 0), [rows])
  const totalRedemption = useMemo(() => rows.reduce((s, r) => s + r.redemption, 0), [rows])
  const totalNet        = totalRedemption - totalInvestment

  const fmt = (n) => `Rs.${Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

  if (loading) return <div className="text-gray-500">Loading...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">MF Investment Tracker</h1>
      <p className="text-sm text-gray-500 mb-6">
        Tracks lumpsum investments (above Rs.10,000) vs redemptions by month.
        Positive net means redemption proceeds not yet reinvested.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Total Invested (Lumpsum)</div>
          <div className="text-2xl font-bold text-blue-600">{fmt(totalInvestment)}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Total Redeemed</div>
          <div className="text-2xl font-bold text-orange-600">{fmt(totalRedemption)}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Net Pending Reinvestment</div>
          <div className={`text-2xl font-bold ${totalNet > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {totalNet > 0 ? '+' : '-'}{fmt(totalNet)}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {totalNet > 0 ? 'Redemption proceeds not fully reinvested' : 'Fully reinvested'}
          </div>
        </div>
      </div>

      {/* Monthly table */}
      {rows.length === 0 ? (
        <div className="text-gray-500">
          No data yet. Import Kuvera CSV for investments and NJ India XLS for redemptions.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Month</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">Investment</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">Redemption</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">Net</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((r) => (
                <tr key={r.month_key} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{r.month_label}</td>
                  <td className="px-4 py-3 text-right text-blue-600 font-medium">
                    {r.investment > 0 ? fmt(r.investment) : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-orange-600 font-medium">
                    {r.redemption > 0 ? fmt(r.redemption) : '—'}
                  </td>
                  <td className={`px-4 py-3 text-right font-bold ${r.net > 0 ? 'text-red-600' : r.net < 0 ? 'text-green-600' : 'text-gray-400'}`}>
                    {r.net === 0 ? '—' : `${r.net > 0 ? '+' : '-'}${fmt(r.net)}`}
                  </td>
                  <td className="px-4 py-3">
                    {r.redemption === 0 && r.investment === 0 ? (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500">No activity</span>
                    ) : r.net <= 0 ? (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">Fully reinvested</span>
                    ) : r.investment === 0 ? (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">Not reinvested</span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-700">Partially reinvested</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            {/* Totals row */}
            <tfoot className="bg-gray-50 border-t-2 border-gray-200">
              <tr>
                <td className="px-4 py-3 font-bold text-gray-800">Total</td>
                <td className="px-4 py-3 text-right font-bold text-blue-600">
                  {totalInvestment > 0 ? fmt(totalInvestment) : '—'}
                </td>
                <td className="px-4 py-3 text-right font-bold text-orange-600">
                  {totalRedemption > 0 ? fmt(totalRedemption) : '—'}
                </td>
                <td className={`px-4 py-3 text-right font-bold ${totalNet > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {totalNet === 0 ? '—' : `${totalNet > 0 ? '+' : '-'}${fmt(totalNet)}`}
                </td>
                <td className="px-4 py-3"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}