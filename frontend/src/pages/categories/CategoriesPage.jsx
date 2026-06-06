import { useEffect, useState } from 'react'
import { getCategories, createCategory, updateCategory, deleteCategory } from '../../api/categories'

const TXN_TYPES = ['expense', 'income', 'transfer', 'investment']

const emptyForm = {
  name: '',
  parent_name: '',
  txn_type: 'expense',
}

export default function CategoriesPage() {
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingCategory, setEditingCategory] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('')

  useEffect(() => {
    fetchCategories()
  }, [])

  async function fetchCategories() {
    try {
      const res = await getCategories()
      setCategories(res.data)
    } catch {
      setError('Failed to load categories')
    } finally {
      setLoading(false)
    }
  }

  function openCreate() {
    setEditingCategory(null)
    setForm(emptyForm)
    setShowForm(true)
    setError(null)
  }

  function openEdit(cat) {
    setEditingCategory(cat)
    setForm({
      name: cat.name,
      parent_name: cat.parent_name || '',
      txn_type: cat.txn_type,
    })
    setShowForm(true)
    setError(null)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    try {
      if (editingCategory) {
        await updateCategory(editingCategory.id, form)
        setSuccess('Category updated')
      } else {
        await createCategory(form)
        setSuccess('Category created')
      }
      setShowForm(false)
      fetchCategories()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to save category')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this category? Transactions using it will become Uncategorised.')) return
    setError(null)
    try {
      await deleteCategory(id)
      setSuccess('Category deleted')
      fetchCategories()
    } catch {
      setError('Failed to delete category')
    }
  }

  // Group by parent
  const filtered = categories.filter((c) => {
    const matchSearch = c.name.toLowerCase().includes(search.toLowerCase()) ||
      (c.parent_name || '').toLowerCase().includes(search.toLowerCase())
    const matchType = filterType ? c.txn_type === filterType : true
    return matchSearch && matchType
  })

  const grouped = filtered.reduce((acc, cat) => {
    const parent = cat.parent_name || 'Uncategorised'
    if (!acc[parent]) acc[parent] = []
    acc[parent].push(cat)
    return acc
  }, {})

  const typeColors = {
    expense: 'bg-red-100 text-red-700',
    income: 'bg-green-100 text-green-700',
    transfer: 'bg-blue-100 text-blue-700',
    investment: 'bg-purple-100 text-purple-700',
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
        <button
          onClick={openCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          Add Category
        </button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm">{success}</div>}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex gap-4">
        <input
          type="text"
          placeholder="Search categories..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="">All types</option>
          {TXN_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {TXN_TYPES.map((type) => {
          const count = categories.filter((c) => c.txn_type === type).length
          return (
            <div key={type} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs text-gray-500 mb-1 capitalize">{type}</div>
              <div className="text-2xl font-bold text-gray-900">{count}</div>
            </div>
          )
        })}
      </div>

      {/* Grouped table */}
      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([parent, cats]) => (
            <div key={parent} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                <span className="font-medium text-gray-700">{parent}</span>
                <span className="ml-2 text-xs text-gray-400">{cats.length} categories</span>
              </div>
              <table className="w-full text-sm">
                <tbody className="divide-y divide-gray-100">
                  {cats.map((cat) => (
                    <tr key={cat.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-900">{cat.name}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${typeColors[cat.txn_type] || 'bg-gray-100 text-gray-600'}`}>
                          {cat.txn_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <button
                          onClick={() => openEdit(cat)}
                          className="text-blue-600 hover:underline text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(cat.id)}
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
          ))}
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold mb-4">
              {editingCategory ? 'Edit Category' : 'Add Category'}
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Parent Category</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.parent_name}
                  onChange={(e) => setForm({ ...form, parent_name: e.target.value })}
                  placeholder="e.g. Food, Transport"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.txn_type}
                  onChange={(e) => setForm({ ...form, txn_type: e.target.value })}
                >
                  {TXN_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
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
                  {editingCategory ? 'Save Changes' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}