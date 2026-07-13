import { useEffect, useState, useMemo } from 'react'
import axios from 'axios'
import { useOwner } from '../../context/OwnerContext'

export default function DividendsPage() {
  const { owner } = useOwner()
  const [dividends, setDividends] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [view, setView] = useState('monthly') // monthly | all

  useEffect(() => {
    setLoading(true)
    axios.get('/api/transactions/dividends', { params: { owner } })
      .then((r) => setDividends(r.data))
      .catch(() => setError('Failed to load dividends'))
      .finally(() => setLoading(false))
  }, [owner])

  // Group by month
  const monthlyData = useMemo(() => {
    const map = {}
    dividends.forEach((d) => {
      const key = `${d.year}-${String(d.month_num).padStart(2, '0')}`
      if (!map[key]) {
        map[key] = { month: d.month, key, total: 0, entries: [] }
      }
      map[key].total += d.amount
      map[key].entries.push(d)
    })
    return Object.values(map).sort((a, b) => b.key.localeCompare(a.key))
  }, [dividends])

  const totalDividends = dividends.reduce((s, d) => s + d.amount, 0)
  const avgMonthly = monthlyData.length > 0 ? totalDividends / monthlyData.length : 0

  if (loading) return <div className="text-gray-500">Loading...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dividends</h1>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Total Received</div>
          <div className="text-2xl font-bold text-green-600">
            ₹{totalDividends.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Avg per Month</div>
          <div className="text-2xl font-bold text-gray-900">
            ₹{avgMonthly.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Months with Dividends</div>
          <div className="text-2xl font-bold text-gray-900">{monthlyData.length}</div>
        </div>
      </div>

      {/* View toggle */}
      <div className="flex gap-3 mb-4">
        {['monthly', 'all'].map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              view === v
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {v === 'monthly' ? 'Monthly Summary' : 'All Entries'}
          </button>
        ))}
      </div>

      {dividends.length === 0 ? (
        <div className="text-gray-500">No dividend transactions found. Categorise transactions as "Dividends" to see them here.</div>
      ) : view === 'monthly' ? (
        <div className="space-y-3">
          {monthlyData.map((m) => (
            <div key={m.key} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div
                className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                onClick={() => {
                  const el = document.getElementById(`div-${m.key}`)
                  el.classList.toggle('hidden')
                }}
              >
                <span className="font-medium text-gray-800">{m.month}</span>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-gray-400">{m.entries.length} entries</span>
                  <span className="font-bold text-green-600">
                    ₹{m.total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>
              </div>
              <div id={`div-${m.key}`} className="hidden border-t border-gray-100">
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-gray-50">
                    {m.entries.map((e) => (
                      <tr key={e.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">
                          {new Date(e.txn_date).toLocaleDateString('en-GB').replace(/\//g, '-')}
                        </td>
                        <td className="px-4 py-2 text-gray-800">{e.description}</td>
                        <td className="px-4 py-2 text-gray-400 text-xs">{e.account_name}</td>
                        <td className="px-4 py-2 text-right font-medium text-green-600">
                          ₹{e.amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Date</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Description</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Account</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {dividends.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(d.txn_date).toLocaleDateString('en-GB').replace(/\//g, '-')}
                  </td>
                  <td className="px-4 py-3 text-gray-900">{d.description}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{d.account_name}</td>
                  <td className="px-4 py-3 text-right font-medium text-green-600">
                    ₹{d.amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}