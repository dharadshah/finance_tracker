import { NavLink } from 'react-router-dom'

const navItems = [
  { path: '/', label: 'Accounts' },
  { path: '/import', label: 'Import' },
  { path: '/transactions', label: 'Transactions' },
  { path: '/categories', label: 'Categories' },
  { path: '/rules', label: 'Rules' },
]

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-8">
        <span className="text-lg font-bold text-gray-900">Finance Tracker</span>
        <div className="flex gap-6">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                isActive
                  ? 'text-blue-600 font-medium border-b-2 border-blue-600 pb-1'
                  : 'text-gray-500 hover:text-gray-900'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Page content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  )
}