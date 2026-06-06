import { useEffect, useState } from 'react'
import { getParsers, importStatement } from '../../api/import_'
import { getAccounts } from '../../api/accounts'

export default function ImportPage() {
  const [parsers, setParsers] = useState([])
  const [accounts, setAccounts] = useState([])
  const [file, setFile] = useState(null)
  const [parserKey, setParserKey] = useState('')
  const [accountId, setAccountId] = useState('')
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getParsers().then((r) => {
      setParsers(r.data)
      if (r.data.length > 0) setParserKey(r.data[0].key)
    })
    getAccounts().then((r) => setAccounts(r.data))
  }, [])

  async function handleImport() {
    if (!file) { setError('Please select a file'); return }
    if (!accountId) { setError('Please select an account'); return }

    setError(null)
    setSummary(null)
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('parser_key', parserKey)
      formData.append('account_id', accountId)

      const res = await importStatement(formData)
      setSummary(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Import Statement</h1>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">

        {/* File upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Statement File
          </label>
          <input
            type="file"
            accept=".csv,.pdf,.xls,.xlsx"
            onChange={(e) => setFile(e.target.files[0])}
            className="w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-600 hover:file:bg-blue-100"
          />
        </div>

        {/* Parser */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bank / Parser
          </label>
          <select
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={parserKey}
            onChange={(e) => setParserKey(e.target.value)}
          >
            {parsers.map((p) => (
              <option key={p.key} value={p.key}>{p.institution}</option>
            ))}
          </select>
        </div>

        {/* Account */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Account
          </label>
          <select
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
          >
            <option value="">-- Select an account --</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name} — {a.institution}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
        )}

        <button
          onClick={handleImport}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
        >
          {loading ? 'Importing...' : 'Import Statement'}
        </button>
      </div>

      {/* Summary */}
      {summary && (
        <div className={`mt-6 bg-white rounded-xl border p-6 ${
          summary.success ? 'border-green-200' : 'border-red-200'
        }`}>
          <h2 className="text-lg font-bold mb-4">
            {summary.success ? 'Import Complete' : 'Import Failed'}
          </h2>
          <table className="w-full text-sm">
            <tbody className="divide-y divide-gray-100">
              {[
                ['Account', summary.account_name],
                ['Institution', summary.institution],
                ['Account Number', summary.account_number_masked || '—'],
                ['Period', summary.statement_period || '—'],
                ['Transactions Imported', summary.transactions_inserted],
                ['Duplicates Skipped', summary.transactions_skipped],
                ['Total in File', summary.total_processed],
              ].map(([label, value]) => (
                <tr key={label}>
                  <td className="py-2 text-gray-500">{label}</td>
                  <td className="py-2 font-medium text-gray-900">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {summary.errors.length > 0 && (
            <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              {summary.errors.map((e, i) => <div key={i}>{e}</div>)}
            </div>
          )}

          {summary.warnings.length > 0 && (
            <details className="mt-4">
              <summary className="text-sm text-gray-500 cursor-pointer">
                {summary.warnings.length} warning(s)
              </summary>
              <div className="mt-2 text-xs text-gray-500 space-y-1">
                {summary.warnings.slice(0, 10).map((w, i) => <div key={i}>{w}</div>)}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}