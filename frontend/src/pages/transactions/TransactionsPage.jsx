import { useEffect, useState } from 'react'
import { getTransactions, bulkDelete, bulkCorrectCategory, correctCategory, deleteFiltered } from '../../api/transactions'
import { getAccounts } from '../../api/accounts'
import { getCategories } from '../../api/categories'
import PieCharts from './PieCharts'
import { useOwner } from '../../context/OwnerContext'



const today = new Date().toISOString().split('T')[0]
const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
  .toISOString().split('T')[0]

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([])
  const [accounts, setAccounts] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { owner, setOwner } = useOwner()
  const owners = ['Dhara', 'Yashvi', 'Jisha']


  // Filters
  const [accountId, setAccountId] = useState('')
  const [fromDate, setFromDate] = useState(firstOfMonth)
  const [toDate, setToDate] = useState(today)
  const [drCr, setDrCr] = useState('')
  const [search, setSearch] = useState('')

  // Selection
  const [selected, setSelected] = useState(new Set())

  // Category correction
  const [newCategory, setNewCategory] = useState('')
  const [actionError, setActionError] = useState(null)
  const [actionSuccess, setActionSuccess] = useState(null)

  const [sortKey, setSortKey] = useState('txn_date')
  const [sortDir, setSortDir] = useState('desc')
  const [showDeleteAll, setShowDeleteAll] = useState(false)

  useEffect(() => {
    setAccountId('')  // reset account selection when owner changes
    getAccounts().then((r) => {
      const filtered = r.data.filter(a => a.owner === owner)
      setAccounts(filtered)
    })
    getCategories().then((r) => {
      setCategories(r.data)
      if (r.data.length > 0) setNewCategory(r.data[0].name)
    })
    fetchTransactions()
  }, [owner])

  async function fetchTransactions() {
    setLoading(true)
    setError(null)
    setSelected(new Set())
    try {
      const params = {}
      if (accountId) params.account_id = accountId
      if (fromDate) params.from_date = fromDate
      if (toDate) params.to_date = toDate
      if (drCr) params.dr_cr = drCr
      if (search) params.search = search
      params.owner = owner  // add this
      const res = await getTransactions(params)
      setTransactions(res.data)
    } catch (e) {
      setError('Failed to load transactions')
    } finally {
      setLoading(false)
    }
  }

  function toggleSelect(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleSelectAll() {
    if (selected.size === transactions.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(sortedTransactions.map((t) => t.id)))
    }
  }

  async function handleBulkDelete() {
    if (!confirm(`Delete ${selected.size} transaction(s)? This cannot be undone.`)) return
    setActionError(null)
    try {
      await bulkDelete([...selected])
      setActionSuccess(`Deleted ${selected.size} transaction(s)`)
      fetchTransactions()
    } catch (e) {
      setActionError('Delete failed')
    }
  }

  async function handleBulkCorrect() {
    if (!newCategory) return
    setActionError(null)
    try {
      await bulkCorrectCategory([...selected], newCategory)
      setActionSuccess(`Updated ${selected.size} transaction(s) to "${newCategory}"`)
      fetchTransactions()
    } catch (e) {
      setActionError('Category update failed')
    }
  }

  // Metrics
  const totalDr = transactions
    .filter((t) => t.dr_cr === 'DR')
    .reduce((sum, t) => sum + t.amount, 0)
  const totalCr = transactions
    .filter((t) => t.dr_cr === 'CR')
    .reduce((sum, t) => sum + t.amount, 0)

  function handleSort(key) {
    if (sortKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
        setSortKey(key)
        setSortDir('asc')
    }
    }

    const sortedTransactions = [...transactions].sort((a, b) => {
    let aVal = a[sortKey]
    let bVal = b[sortKey]
    if (typeof aVal === 'string') aVal = aVal.toLowerCase()
    if (typeof bVal === 'string') bVal = bVal.toLowerCase()
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
    return 0
    })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Transactions</h1>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6"> 
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Owner</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
            >
              {owners.map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Account</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
            >
              <option value="">All accounts</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
            <input
              type="date"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Type</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={drCr}
              onChange={(e) => setDrCr(e.target.value)}
            >
              <option value="">All</option>
              <option value="DR">Debit</option>
              <option value="CR">Credit</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
            <input
              type="text"
              placeholder="Swiggy, Salary..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchTransactions()}
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={fetchTransactions}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            Apply Filters
          </button>
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg">{error}</div>}

      {/* Metrics */}
      {transactions.length > 0 && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1">Transactions</div>
              <div className="text-2xl font-bold text-gray-900">{transactions.length}</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1">Total Debits</div>
              <div className="text-2xl font-bold text-red-600">
                {totalDr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1">Total Credits</div>
              <div className="text-2xl font-bold text-green-600">
                {totalCr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </div>
            </div>
          </div>

          {/* Pie Charts */}
          <PieCharts transactions={transactions} />
        </>
      )}

      {/* Delete all matching */}
        <div className="flex justify-end mb-2">
        <button
            onClick={() => setShowDeleteAll(true)}
            className="text-sm text-red-500 hover:text-red-700 hover:underline"
        >
            Delete all {transactions.length} matching transactions
        </button>
        </div>

        {showDeleteAll && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Delete All Matching</h2>
            <p className="text-sm text-gray-600 mb-6">
                This will permanently delete all <strong>{transactions.length}</strong> transactions
                matching the current filters. This cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
                <button
                onClick={() => setShowDeleteAll(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
                >
                Cancel
                </button>
                <button
                onClick={async () => {
                    try {
                    const params = {}
                    if (accountId) params.account_id = accountId
                    if (fromDate) params.from_date = fromDate
                    if (toDate) params.to_date = toDate
                    if (drCr) params.dr_cr = drCr
                    if (search) params.search = search
                    const res = await deleteFiltered(params)
                    setShowDeleteAll(false)
                    setActionSuccess(res.data.message)
                    fetchTransactions()
                    } catch {
                    setActionError('Delete failed')
                    setShowDeleteAll(false)
                    }
                }}
                className="px-4 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600"
                >
                Yes, Delete All
                </button>
            </div>
            </div>
        </div>
        )}

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 flex flex-wrap items-center gap-4">
          <span className="text-sm font-medium text-blue-800">
            {selected.size} selected
          </span>
          <div className="flex items-center gap-2">
            <select
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
            >
              {categories.map((c) => (
                <option key={c.id} value={c.name}>{c.parent_name ? `${c.parent_name} > ` : ''}{c.name}</option>
              ))}
            </select>
            <button
              onClick={handleBulkCorrect}
              className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-blue-700"
            >
              Update Category
            </button>
          </div>
          <button
            onClick={handleBulkDelete}
            className="bg-red-500 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-red-600 ml-auto"
          >
            Delete Selected
          </button>
        </div>
      )}

      {actionSuccess && (
        <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm">{actionSuccess}</div>
      )}
      {actionError && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{actionError}</div>
      )}

      {/* Table */}
      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : transactions.length === 0 ? (
        <div className="text-gray-500">No transactions found.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                    <th className="px-4 py-3">
                    <input
                        type="checkbox"
                        checked={selected.size === transactions.length && transactions.length > 0}
                        onChange={toggleSelectAll}
                    />
                    </th>
                    {[
                    { key: 'txn_date', label: 'Date' },
                    { key: 'description', label: 'Description' },
                    { key: 'category', label: 'Category' },
                    { key: 'dr_cr', label: 'Type' },
                    { key: 'amount', label: 'Amount' },
                    ].map(({ key, label }) => (
                    <th
                        key={key}
                        onClick={() => handleSort(key)}
                        className={`px-4 py-3 text-gray-600 font-medium cursor-pointer hover:bg-gray-100 select-none ${
                        key === 'amount' ? 'text-right' : 'text-left'
                        }`}
                    >
                        {label}
                        {sortKey === key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ' ↕'}
                    </th>
                    ))}
                </tr>
                </thead>
            <tbody className="divide-y divide-gray-100">
              {sortedTransactions.map((t) => (
                <tr
                  key={t.id}
                  className={`hover:bg-gray-50 cursor-pointer ${selected.has(t.id) ? 'bg-blue-50' : ''}`}
                  onClick={() => toggleSelect(t.id)}
                >
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.has(t.id)}
                      onChange={() => toggleSelect(t.id)}
                    />
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(t.txn_date).toLocaleDateString('en-GB').replace(/\//g, '-')}
                  </td>
                  <td className="px-4 py-3 text-gray-900 max-w-xs truncate">{t.description}</td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <select
                        className="text-xs bg-gray-100 text-gray-700 rounded-full px-2 py-1 border-none outline-none cursor-pointer hover:bg-gray-200"
                        value={t.category || 'Uncategorised'}
                        onChange={async (e) => {
                            const selectedCat = e.target.value
                            try {
                                await correctCategory(t.id, selectedCat)
                                await fetchTransactions()
                                setActionSuccess(`Updated to "${selectedCat}"`)
                            } catch (err) {
                                console.error('Error:', err)
                                setActionError('Failed to update category')
                            }
                            }}
                    >
                        {categories.map((c) => (
                        <option key={c.id} value={c.name}>
                            {c.parent_name ? `${c.parent_name} > ` : ''}{c.name}
                        </option>
                        ))}
                    </select>
                    </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      t.dr_cr === 'DR'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-green-100 text-green-700'
                    }`}>
                      {t.dr_cr === 'DR' ? 'Debit' : 'Credit'}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-right font-medium ${
                    t.dr_cr === 'DR' ? 'text-red-600' : 'text-green-600'
                  }`}>
                    {t.amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
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