import { useEffect, useState } from 'react'
import { getRules, createRule, deleteRule, getCorrections } from '../../api/rules'
import { getCategories } from '../../api/categories'

export default function RulesPage() {
  const [rules, setRules] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState({
    institution: 'ICICI Bank',
    description_pattern: '',
    category_name: '',
  })
  const [corrections, setCorrections] = useState([])
  const [showLog, setShowLog] = useState(false)
  const [logFilter, setLogFilter] = useState('')


  useEffect(() => {
    fetchRules()
    getCorrections().then((r) => setCorrections(r.data))
    getCategories().then((r) => {
      setCategories(r.data)
      if (r.data.length > 0) setForm((f) => ({ ...f, category_name: r.data[0].name }))
    })
  }, [])

  async function fetchRules() {
    try {
      const res = await getRules()
      setRules(res.data)
    } catch {
      setError('Failed to load rules')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setError(null)
    try {
      await createRule(form)
      setSuccess('Rule created')
      setShowForm(false)
      setForm({ institution: 'ICICI Bank', description_pattern: '', category_name: categories[0]?.name || '' })
      fetchRules()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create rule')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this rule? Future imports will no longer auto-categorise this pattern.')) return
    setError(null)
    try {
      await deleteRule(id)
      setSuccess('Rule deleted')
      fetchRules()
    } catch {
      setError('Failed to delete rule')
    }
  }

  const filtered = rules.filter((r) =>
    r.description_pattern.toLowerCase().includes(search.toLowerCase()) ||
    r.category_name.toLowerCase().includes(search.toLowerCase()) ||
    r.institution.toLowerCase().includes(search.toLowerCase())
  )

  // Group by institution
  const grouped = filtered.reduce((acc, rule) => {
    if (!acc[rule.institution]) acc[rule.institution] = []
    acc[rule.institution].push(rule)
    return acc
  }, {})

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Categorisation Rules</h1>
          <p className="text-sm text-gray-500 mt-1">
            Rules map transaction descriptions to categories automatically on import.
          </p>
        </div>
        <button
          onClick={() => { setShowForm(true); setError(null) }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          Add Rule
        </button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm">{success}</div>}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Total Rules</div>
          <div className="text-2xl font-bold text-gray-900">{rules.length}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Institutions</div>
          <div className="text-2xl font-bold text-gray-900">{Object.keys(grouped).length}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Most Matched</div>
          <div className="text-sm font-bold text-gray-900 truncate">
            {rules.length > 0
              ? [...rules].sort((a, b) => b.match_count - a.match_count)[0].description_pattern
              : '—'}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <input
          type="text"
          placeholder="Search by pattern, category or institution..."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Rules grouped by institution */}
      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : rules.length === 0 ? (
        <div className="text-gray-500">No rules yet. Add one or make manual category corrections — they become rules automatically.</div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([institution, instRules]) => (
            <div key={institution} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                <span className="font-medium text-gray-700">{institution}</span>
                <span className="text-xs text-gray-400">{instRules.length} rules</span>
              </div>
              <table className="w-full text-sm">
                <thead className="border-b border-gray-100">
                  <tr>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Description Pattern</th>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Category</th>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Matched</th>
                    <th className="text-left px-4 py-2 text-gray-500 font-medium">Last Seen</th>
                    <th className="text-right px-4 py-2 text-gray-500 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {instRules.map((rule) => (
                    <tr key={rule.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-800">
                        {rule.description_pattern}
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs">
                          {rule.category_name}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {rule.match_count}x
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {new Date(rule.last_seen_at).toLocaleDateString('en-GB').replace(/\//g, '-')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(rule.id)}
                          className="text-red-500 hover:underline text-xs"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

        {/* Correction Log */}
        <div className="mt-8">
        <div
            className="flex items-center justify-between cursor-pointer"
            onClick={() => setShowLog((v) => !v)}
        >
            <div>
            <h2 className="text-lg font-bold text-gray-900">Correction Log</h2>
            <p className="text-xs text-gray-500">
                {corrections.length} manual correction(s) — review these to identify new rules
            </p>
            </div>
            <span className="text-gray-400 text-sm">{showLog ? '▲ Hide' : '▼ Show'}</span>
        </div>

        {showLog && (
            <div className="mt-4">
                {/* Filter + Download bar */}
                <div className="flex gap-3 mb-3">
                <select
                    className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1"
                    value={logFilter}
                    onChange={(e) => setLogFilter(e.target.value)}
                >
                    <option value="">All categories</option>
                    {[...new Set(corrections.map((c) => c.category_name))].sort().map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                    ))}
                </select>
                <button
                    onClick={() => {
                    const filtered = logFilter
                        ? corrections.filter((c) => c.category_name === logFilter)
                        : corrections
                    const csv = [
                        'Date,Description,Raw Description,From,To',
                        ...filtered.map((c) =>
                        [
                            new Date(c.assigned_at).toLocaleDateString('en-GB').replace(/\//g, '-'),
                            `"${c.description}"`,
                            `"${c.raw_description || ''}"`,
                            `"${c.previous_category || ''}"`,
                            `"${c.category_name}"`,
                        ].join(',')
                        ),
                    ].join('\n')
                    const blob = new Blob([csv], { type: 'text/csv' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `corrections${logFilter ? '_' + logFilter : ''}.csv`
                    a.click()
                    URL.revokeObjectURL(url)
                    }}
                    className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-200 whitespace-nowrap"
                >
                    Download CSV
                </button>
                </div>

                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {corrections.length === 0 ? (
                    <div className="p-4 text-gray-500 text-sm">
                    No manual corrections yet.
                    </div>
                ) : (
                    <>
                    {/* Count */}
                    <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 text-xs text-gray-500">
                        {logFilter
                        ? `${corrections.filter((c) => c.category_name === logFilter).length} of ${corrections.length} corrections`
                        : `${corrections.length} corrections`}
                    </div>
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="text-left px-4 py-2 text-gray-500 font-medium">Date</th>
                            <th className="text-left px-4 py-2 text-gray-500 font-medium">Description</th>
                            <th className="text-left px-4 py-2 text-gray-500 font-medium">Raw Description</th>
                            <th className="text-left px-4 py-2 text-gray-500 font-medium">From</th>
                            <th className="text-left px-4 py-2 text-gray-500 font-medium">To</th>
                        </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                        {(logFilter
                            ? corrections.filter((c) => c.category_name === logFilter)
                            : corrections
                        ).map((c) => (
                            <tr key={c.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                                {new Date(c.assigned_at).toLocaleDateString('en-GB').replace(/\//g, '-')}
                            </td>
                            <td className="px-4 py-3 text-gray-800 text-xs font-mono">
                                {c.description}
                            </td>
                            <td className="px-4 py-3 text-gray-400 text-xs font-mono max-w-xs truncate">
                                {c.raw_description || '—'}
                            </td>
                            <td className="px-4 py-3">
                                <span className="px-2 py-1 bg-red-50 text-red-600 rounded-full text-xs">
                                {c.previous_category || '—'}
                                </span>
                            </td>
                            <td className="px-4 py-3">
                                <span className="px-2 py-1 bg-green-50 text-green-700 rounded-full text-xs">
                                {c.category_name}
                                </span>
                            </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    </>
                )}
                </div>
            </div>
            )}
        </div>



      {/* Add Rule Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold mb-1">Add Rule</h2>
            <p className="text-xs text-gray-500 mb-4">
              The description pattern must match the cleaned description exactly as it appears in the transactions table.
            </p>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Institution</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.institution}
                  onChange={(e) => setForm({ ...form, institution: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description Pattern</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
                  value={form.description_pattern}
                  onChange={(e) => setForm({ ...form, description_pattern: e.target.value })}
                  placeholder="e.g. UPI / Swiggy"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.category_name}
                  onChange={(e) => setForm({ ...form, category_name: e.target.value })}
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.name}>
                      {c.parent_name ? `${c.parent_name} > ` : ''}{c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Create Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
