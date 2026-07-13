import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccounts } from '../../api/accounts'
import { useOwner } from '../../context/OwnerContext'

export default function StocksPage() {
  const { owner } = useOwner()
  const [holdings, setHoldings] = useState([])
  const [transactions, setTransactions] = useState([])
  const [accounts, setAccounts] = useState([])
  const [selectedAccountId, setSelectedAccountId] = useState('')
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('holdings')
  const [search, setSearch] = useState('')
  const [prices, setPrices] = useState({})
  const [editingPrices, setEditingPrices] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [priceSummary, setPriceSummary] = useState(null)

  useEffect(() => {
    fetchHoldings()
    getAccounts().then((r) => {
      const stockAccounts = r.data.filter(a =>
        a.account_type === 'demat' && a.owner === owner
      )
      setAccounts(stockAccounts)
      if (stockAccounts.length > 0) setSelectedAccountId(stockAccounts[0].id)
    })
  }, [owner])

  async function handleRefreshPrices() {
    setRefreshing(true)
    setError(null)
    try {
        const res = await axios.post('/api/stocks/prices/refresh')
        setPriceSummary(res.data)
        fetchHoldings()
    } catch {
        setError('Failed to refresh prices')
    } finally {
        setRefreshing(false)
    }
    }

  async function fetchHoldings() {
    setLoading(true)
    try {
      const res = await axios.get('/api/stocks/holdings', { params: { owner } })
      setHoldings(res.data)
      // Init prices from current values
      const priceMap = {}
      res.data.forEach(h => {
        if (h.current_price) priceMap[h.symbol] = h.current_price
      })
      setPrices(priceMap)
    } catch {
      setError('Failed to load holdings')
    } finally {
      setLoading(false)
    }
  }

  async function fetchTransactions() {
    try {
      const res = await axios.get('/api/stocks/transactions', { params: { owner } })
      setTransactions(res.data)
    } catch {
      setError('Failed to load transactions')
    }
  }

  async function handleImport(e) {
    const file = e.target.files[0]
    if (!file) return
    if (!selectedAccountId) { setError('Please select an account'); return }
    setImporting(true)
    setError(null)
    setSummary(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('account_id', selectedAccountId)
      const res = await axios.post('/api/stocks/import', formData, {
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

  async function handleUpdatePrices() {
    try {
      await axios.post('/api/stocks/prices', { prices })
      setEditingPrices(false)
      fetchHoldings()
    } catch {
      setError('Failed to update prices')
    }
  }

  // Totals
  const totalInvested = holdings.reduce((s, h) => s + h.invested_value, 0)
  const totalCurrent = holdings.reduce((s, h) => s + (h.current_value || h.invested_value), 0)
  const totalPnl = totalCurrent - totalInvested
  const totalPnlPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0

  const filteredHoldings = holdings.filter(h =>
    h.symbol.toLowerCase().includes(search.toLowerCase()) ||
    (h.company_name || '').toLowerCase().includes(search.toLowerCase())
  )

  const filteredTxns = transactions.filter(t =>
    t.symbol.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Stocks</h1>
        <div className="flex items-center gap-3">
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
          >
            <option value="">-- Select account --</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <label className={`cursor-pointer bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium ${importing ? 'opacity-50' : ''}`}>
            {importing ? 'Importing...' : 'Import Tradebook'}
            <input type="file" accept=".csv" onChange={handleImport} className="hidden" disabled={importing} />
          </label>
          <button
            onClick={handleRefreshPrices}
            disabled={refreshing}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 text-sm font-medium disabled:opacity-50"
            >
            {refreshing ? 'Refreshing...' : 'Refresh Prices'}
          </button>
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
      
      {priceSummary && (
        <div className="mb-6 bg-white rounded-xl border border-green-200 p-4">
            <h3 className="font-medium mb-3">✅ Prices Refreshed</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
            <div><div className="text-gray-500">Updated</div><div className="font-bold">{priceSummary.fetched}</div></div>
            <div><div className="text-gray-500">Already Current</div><div className="font-bold">{priceSummary.already_current}</div></div>
            <div><div className="text-gray-500">Failed</div><div className="font-bold text-red-500">{priceSummary.failed}</div></div>
            </div>
            {priceSummary.errors.length > 0 && (
            <details className="mt-3">
                <summary className="text-xs text-gray-500 cursor-pointer">Show errors</summary>
                <div className="mt-2 space-y-1">
                {priceSummary.errors.map((e, i) => <div key={i} className="text-xs text-red-500">{e}</div>)}
                </div>
            </details>
            )}
        </div>
        )}
      {/* Import summary */}
      {summary && (
        <div className={`mb-6 bg-white rounded-xl border p-4 ${summary.success ? 'border-green-200' : 'border-red-200'}`}>
          <h3 className="font-medium mb-3">{summary.success ? '✅ Import Complete' : '❌ Import Failed'}</h3>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div><div className="text-gray-500">Imported</div><div className="font-bold">{summary.transactions_inserted}</div></div>
            <div><div className="text-gray-500">Skipped</div><div className="font-bold">{summary.transactions_skipped}</div></div>
            <div><div className="text-gray-500">Symbols</div><div className="font-bold">{summary.symbols_count}</div></div>
            <div><div className="text-gray-500">Period</div><div className="font-bold text-xs">{summary.period_start} – {summary.period_end}</div></div>
          </div>
        </div>
      )}

      {/* Portfolio summary */}
      {holdings.length > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs text-gray-500 mb-1">Invested</div>
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
            <div className="text-xs text-gray-500 mb-1">P&L</div>
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
          placeholder="Search symbol..."
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
          <div className="text-gray-500">No holdings yet. Import a Zerodha tradebook CSV.</div>
        ) : (
          <>
            <div className="flex justify-end mb-2">
              {editingPrices ? (
                <div className="flex gap-2">
                  <button onClick={handleUpdatePrices} className="bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm">Save Prices</button>
                  <button onClick={() => setEditingPrices(false)} className="bg-gray-100 text-gray-600 px-3 py-1.5 rounded-lg text-sm">Cancel</button>
                </div>
              ) : (
                <button onClick={() => setEditingPrices(true)} className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-200">
                  Update Prices
                </button>
              )}
            </div>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Symbol</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Exchange</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">Qty</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">Avg Price</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">Current Price</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">Invested</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">Current Value</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">P&L</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">Return</th>
                    <th className="text-right px-4 py-3 text-gray-600 font-medium">XIRR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredHoldings.map((h) => (
                    <tr key={h.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{h.symbol}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{h.exchange}</td>
                      <td className="px-4 py-3 text-right text-gray-700">{h.quantity.toFixed(0)}</td>
                      <td className="px-4 py-3 text-right text-gray-700">₹{h.avg_buy_price.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">
                        {editingPrices ? (
                          <input
                            type="number"
                            className="w-24 border border-gray-300 rounded px-2 py-1 text-sm text-right"
                            value={prices[h.symbol] || ''}
                            onChange={(e) => setPrices({ ...prices, [h.symbol]: parseFloat(e.target.value) })}
                          />
                        ) : (
                          <span className="text-gray-700">
                            {h.current_price ? `₹${h.current_price.toFixed(2)}` : '—'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-700">
                        ₹{h.invested_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-700">
                        {h.current_value ? `₹${h.current_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'}
                      </td>
                      <td className={`px-4 py-3 text-right font-medium ${(h.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {h.pnl != null ? `${h.pnl >= 0 ? '+' : ''}₹${h.pnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'}
                      </td>
                      <td className={`px-4 py-3 text-right font-medium ${(h.pnl_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {h.pnl_pct != null ? `${h.pnl_pct >= 0 ? '+' : ''}${h.pnl_pct.toFixed(2)}%` : '—'}
                      </td>
                      <td className={`px-4 py-3 text-right font-medium ${(h.xirr || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {h.xirr != null ? `${h.xirr >= 0 ? '+' : ''}${h.xirr.toFixed(2)}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )
      )}

      {/* Transactions tab */}
      {activeTab === 'transactions' && (
        filteredTxns.length === 0 ? (
          <div className="text-gray-500">No transactions found.</div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Symbol</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Exchange</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Type</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Qty</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Price</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredTxns.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {new Date(t.trade_date).toLocaleDateString('en-GB').replace(/\//g, '-')}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">{t.symbol}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{t.exchange}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        t.trade_type === 'buy'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {t.trade_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">{t.quantity.toFixed(0)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">₹{t.price.toFixed(2)}</td>
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