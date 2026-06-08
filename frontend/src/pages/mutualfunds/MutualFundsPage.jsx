import { useEffect, useState } from 'react'
import { useOwner } from '../../context/OwnerContext'
import axios from 'axios'
import { getAccounts } from '../../api/accounts'

export default function MutualFundsPage() {
  const [holdings, setHoldings] = useState([])
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('holdings')
  const [transactions, setTransactions] = useState([])
  const [txnLoading, setTxnLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [navSummary, setNavSummary] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [selectedAccountId, setSelectedAccountId] = useState('')
  const { owner } = useOwner()


  useEffect(() => {
    fetchHoldings()
    getAccounts().then((r) => {
      const mfAccounts = r.data.filter(a => a.account_type === 'mf_folio' && a.owner === owner)
      setAccounts(mfAccounts)
      if (mfAccounts.length > 0) setSelectedAccountId(mfAccounts[0].id)
    })
  }, [owner])
  
  async function handleRefreshNAV() {
    setRefreshing(true)
    setError(null)
    try {
      const res = await axios.post('/api/mf/nav/refresh')
      setNavSummary(res.data)
      fetchHoldings()
    } catch {
      setError('Failed to refresh NAV')
    } finally {
      setRefreshing(false)
    }
  }

  async function fetchHoldings() {
    setLoading(true)
    try {
      const res = await axios.get('/api/mf/holdings', { params: { owner } })
      setHoldings(res.data)
    } catch {
      setError('Failed to load holdings')
    } finally {
      setLoading(false)
    }
  }

  async function fetchTransactions() {
    setTxnLoading(true)
    try {
      const res = await axios.get('/api/mf/transactions')
      setTransactions(res.data)
    } catch {
      setError('Failed to load transactions')
    } finally {
      setTxnLoading(false)
    }
  }

  async function handleImport(e) {
    const file = e.target.files[0]
    if (!file) return
    if (!selectedAccountId) {
      setError('Please select a portfolio account first')
      return
    }
    setImporting(true)
    setError(null)
    setSummary(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('account_id', selectedAccountId)
      const res = await axios.post('/api/mf/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setSummary(res.data)
      fetchHoldings()
    } catch (e) {
      setError(e.response?.data?.detail || 'Import failed')
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  // Totals
  const totalInvested = holdings.reduce((s, h) => s + h.invested_amount, 0)
  const totalCurrent = holdings.reduce((s, h) => s + h.current_value, 0)
  const totalPnl = totalCurrent - totalInvested
  const totalPnlPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0

  const filteredHoldings = holdings.filter((h) =>
    h.scheme_name.toLowerCase().includes(search.toLowerCase())
  )

  const filteredTxns = transactions.filter((t) =>
    t.scheme_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div className="flex items-center gap-3">
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={selectedAccountId}
          onChange={(e) => setSelectedAccountId(e.target.value)}
        >
          <option value="">-- Select portfolio --</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <button
          onClick={handleRefreshNAV}
          disabled={refreshing}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 text-sm font-medium disabled:opacity-50"
        >
          {refreshing ? 'Refreshing...' : 'Refresh NAV'}
        </button>
        <label className={`cursor-pointer bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium ${importing ? 'opacity-50' : ''}`}>
          {importing ? 'Importing...' : 'Import Kuvera CSV'}
          <input type="file" accept=".csv" onChange={handleImport} className="hidden" disabled={importing} />
        </label>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

      {/* Import summary */}
      {summary && (
        <div className={`mb-6 bg-white rounded-xl border p-4 ${summary.success ? 'border-green-200' : 'border-red-200'}`}>
          <h3 className="font-medium mb-3">{summary.success ? '✅ Import Complete' : '❌ Import Failed'}</h3>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div><div className="text-gray-500">Imported</div><div className="font-bold">{summary.transactions_inserted}</div></div>
            <div><div className="text-gray-500">Skipped</div><div className="font-bold">{summary.transactions_skipped}</div></div>
            <div><div className="text-gray-500">Funds</div><div className="font-bold">{summary.funds_count}</div></div>
            <div><div className="text-gray-500">Period</div><div className="font-bold text-xs">{summary.period_start} – {summary.period_end}</div></div>
          </div>
        </div>
      )}

      {navSummary && (
        <div className="mb-6 bg-white rounded-xl border border-green-200 p-4">
          <h3 className="font-medium mb-3">✅ NAV Refreshed</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div><div className="text-gray-500">Matched</div><div className="font-bold">{navSummary.matched}</div></div>
            <div><div className="text-gray-500">Already Current</div><div className="font-bold">{navSummary.already_current}</div></div>
            <div><div className="text-gray-500">Unmatched</div><div className="font-bold text-red-500">{navSummary.errors.length}</div></div>
          </div>
          {navSummary.errors.length > 0 && (
            <details className="mt-3">
              <summary className="text-xs text-gray-500 cursor-pointer">Show unmatched funds</summary>
              <div className="mt-2 space-y-1">
                {navSummary.errors.map((e, i) => <div key={i} className="text-xs text-red-500">{e}</div>)}
              </div>
            </details>
          )}
        </div>
      )}

      {/* Portfolio summary */}
      {holdings.length > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Total Invested</div>
            <div className="text-xl font-bold text-gray-900">
              ₹{totalInvested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Current Value</div>
            <div className="text-xl font-bold text-gray-900">
              ₹{totalCurrent.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Total P&L</div>
            <div className={`text-xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {totalPnl >= 0 ? '+' : ''}₹{totalPnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Return</div>
            <div className={`text-xl font-bold ${totalPnlPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200 mb-4">
        {['holdings', 'transactions'].map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab)
              if (tab === 'transactions' && transactions.length === 0) fetchTransactions()
            }}
            className={`pb-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-900'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search funds..."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Holdings tab */}
      {activeTab === 'holdings' && (
        loading ? (
          <div className="text-gray-500">Loading...</div>
        ) : filteredHoldings.length === 0 ? (
          <div className="text-gray-500">No holdings yet. Import a Kuvera CSV to get started.</div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Fund</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Folio</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Units</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Avg NAV</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Invested</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Current Value</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">P&L</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">XIRR</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Return</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredHoldings.map((h) => (
                  <tr key={h.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-900 max-w-xs">
                      <div className="font-medium text-sm">{h.scheme_name}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{h.folio_number}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{h.units.toFixed(3)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">₹{h.avg_nav.toFixed(4)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      ₹{h.invested_amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      ₹{h.current_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td className={`px-4 py-3 text-right font-medium ${h.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {h.pnl >= 0 ? '+' : ''}₹{h.pnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td className={`px-4 py-3 text-right font-medium ${(h.xirr || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {h.xirr != null ? `${h.xirr >= 0 ? '+' : ''}${h.xirr.toFixed(2)}%` : '—'}
                    </td>
                    <td className={`px-4 py-3 text-right font-medium ${h.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {/* Transactions tab */}
      {activeTab === 'transactions' && (
        txnLoading ? (
          <div className="text-gray-500">Loading...</div>
        ) : filteredTxns.length === 0 ? (
          <div className="text-gray-500">No transactions found.</div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Fund</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Type</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Units</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">NAV</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredTxns.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {new Date(t.txn_date).toLocaleDateString('en-GB').replace(/\//g, '-')}
                    </td>
                    <td className="px-4 py-3 text-gray-900 max-w-xs">
                      <div className="text-sm">{t.scheme_name}</div>
                      <div className="text-xs text-gray-400">{t.folio_number}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        t.order_type === 'buy'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {t.order_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">{t.units.toFixed(3)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">₹{t.nav.toFixed(4)}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                      ₹{t.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  )
}