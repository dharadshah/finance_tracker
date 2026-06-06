import { useEffect, useState } from 'react'
import { getAccounts, createAccount, updateAccount, deleteAccount, getInstitutions } from '../../api/accounts'



const ACCOUNT_TYPES = ['savings', 'current', 'credit_card', 'demat', 'mf_folio', 'wallet']

const emptyForm = {
  name: '',
  account_type: 'savings',
  institution: '',
  account_number_last4: '',
  currency: 'INR',
  notes: '',
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingAccount, setEditingAccount] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState(null)
  const [institutions, setInstitutions] = useState([])


  useEffect(() => {
    fetchAccounts()
    getInstitutions().then((r) => {
        console.log('institutions:', r.data)
        setInstitutions(r.data)
    })
  }, [])

  async function fetchAccounts() {
    try {
      const res = await getAccounts()
      setAccounts(res.data)
    } catch (e) {
      setError('Failed to load accounts')
    } finally {
      setLoading(false)
    }
  }

  function openCreate() {
    setEditingAccount(null)
    setForm(emptyForm)
    setShowForm(true)
  }

  function openEdit(account) {
    setEditingAccount(account)
    setForm({
      name: account.name,
      account_type: account.account_type,
      institution: account.institution,
      account_number_last4: account.account_number_last4 || '',
      currency: account.currency,
      notes: account.notes || '',
    })
    setShowForm(true)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    try {
      if (editingAccount) {
        await updateAccount(editingAccount.id, form)
      } else {
        await createAccount(form)
      }
      setShowForm(false)
      fetchAccounts()
    } catch (e) {
      setError('Failed to save account')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this account? All its transactions will also be deleted.')) return
    try {
      await deleteAccount(id)
      fetchAccounts()
    } catch (e) {
      setError('Failed to delete account')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
        <button
          onClick={openCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          Add Account
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg">{error}</div>
      )}

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : accounts.length === 0 ? (
        <div className="text-gray-500">No accounts yet. Add one to get started.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Name</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Institution</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Type</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Currency</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {accounts.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.name}</td>
                  <td className="px-4 py-3 text-gray-600">{a.institution}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{a.account_type}</td>
                  <td className="px-4 py-3 text-gray-600">{a.currency}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      a.is_active
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-500'
                    }`}>
                      {a.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      onClick={() => openEdit(a)}
                      className="text-blue-600 hover:underline text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(a.id)}
                      className="text-red-500 hover:underline text-sm"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold mb-4">
              {editingAccount ? 'Edit Account' : 'Add Account'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Institution</label>
                <select
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    value={form.institution}
                    onChange={(e) => setForm({ ...form, institution: e.target.value })}
                    required
                >
                    <option value="">-- Select institution --</option>
                    {institutions.map((inst) => (
                    <option key={inst} value={inst}>{inst}</option>
                    ))}
                </select>
                </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Account Type</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.account_type}
                  onChange={(e) => setForm({ ...form, account_type: e.target.value })}
                >
                  {ACCOUNT_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Last 4 digits</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.account_number_last4}
                  onChange={(e) => setForm({ ...form, account_number_last4: e.target.value })}
                  maxLength={4}
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="Optional"
                />
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
                  {editingAccount ? 'Save Changes' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}