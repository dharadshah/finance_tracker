import { useEffect, useState } from 'react'
import { getAccounts } from '../../api/accounts'
import axios from 'axios'
import { useOwner } from '../../context/OwnerContext'

export default function DashboardPage() {
  const { owner, setOwner } = useOwner()
  const owners = ['Dhara', 'Yashvi', 'Jisha']
  const [accounts, setAccounts] = useState([])
  const [mfHoldings, setMfHoldings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getAccounts(),
      axios.get('/api/mf/holdings', { params: { owner } }),
    ]).then(([accRes, mfRes]) => {
      setAccounts(accRes.data)
      setMfHoldings(mfRes.data)
    }).finally(() => setLoading(false))
  }, [owner])

  // Bank accounts — only savings/current
  const bankAccounts = accounts.filter(a =>
    ['savings', 'current'].includes(a.account_type) && a.owner === owner
  )

  // MF totals
  const mfInvested = mfHoldings.reduce((s, h) => s + h.invested_amount, 0)
  const mfCurrent = mfHoldings.reduce((s, h) => s + h.current_value, 0)
  const mfPnl = mfCurrent - mfInvested
  const mfPnlPct = mfInvested > 0 ? (mfPnl / mfInvested) * 100 : 0

  // Net worth
  const bankTotal = bankAccounts.reduce((s, a) => s + (a.current_balance || 0), 0)
  const netWorth = bankTotal + mfCurrent

  if (loading) return <div className="text-gray-500">Loading...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        >
          {owners.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </div>

      {/* Net Worth */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 mb-6 text-white">
        <div className="text-sm font-medium opacity-80 mb-1">Total Net Worth</div>
        <div className="text-4xl font-bold">
          ₹{netWorth.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
        </div>
        <div className="text-sm opacity-70 mt-1">
          Bank + Mutual Funds
        </div>
      </div>

      {/* Bank Accounts */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Bank Accounts</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {bankAccounts.map((a) => (
            <div key={a.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="font-semibold text-gray-900">{a.name}</div>
                  <div className="text-xs text-gray-500">{a.institution}</div>
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                  {a.account_type}
                </span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {a.current_balance != null
                  ? `₹${Number(a.current_balance).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
                  : <span className="text-gray-400 text-base">Reimport statement</span>
                }
              </div>
            </div>
          ))}

          {/* Total card */}
          <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="font-semibold text-blue-900">Total Bank Balance</div>
                <div className="text-xs text-blue-500">All accounts</div>
              </div>
            </div>
            <div className="text-2xl font-bold text-blue-700">
              ₹{bankTotal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
        </div>
      </div>

      {/* Mutual Funds */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Mutual Funds</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Invested</div>
            <div className="text-xl font-bold text-gray-900">
              ₹{mfInvested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Current Value</div>
            <div className="text-xl font-bold text-gray-900">
              ₹{mfCurrent.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">P&L</div>
            <div className={`text-xl font-bold ${mfPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {mfPnl >= 0 ? '+' : ''}₹{mfPnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Return</div>
            <div className={`text-xl font-bold ${mfPnlPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {mfPnlPct >= 0 ? '+' : ''}{mfPnlPct.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}