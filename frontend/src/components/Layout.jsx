import { NavLink, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { useOwner } from '../context/OwnerContext'


const navGroups = [
  {
    label: null,
    items: [{ path: '/dashboard', label: 'Dashboard' }],
  },
  {
    label: 'Bank',
    items: [
      { path: '/transactions', label: 'Bank Transactions' },
      { path: '/import', label: 'Import' },
      { path: '/categories', label: 'Categories' },
      { path: '/dividends', label: 'Dividends' },
    ],
  },
  {
    label: null,
    items: [{ path: '/mutual-funds', label: 'Mutual Funds' }],
  },
  {
    label: null,
    items: [{ path: '/stocks', label: 'Stocks' }],
  },
  {
    label: 'Utilities',
    items: [
      { path: '/', label: 'Accounts' },
      
      { path: '/rules', label: 'Rules' },
    ],
  },
]

export default function Layout({ children }) {
  const { owner, setOwner } = useOwner()
  const owners = ['Dhara', 'Yashvi', 'Jisha']
  
  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside className="w-56 bg-white border-r border-gray-200 min-h-screen flex flex-col">
        <div className="px-5 py-5 border-b border-gray-100">
          <span className="text-base font-bold text-gray-900">Finance Tracker</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-5">
          {/* existing nav groups */}
          {navGroups.map((group, gi) => (
            <div key={gi}>
              {group.label && (
                <div className="px-2 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  {group.label}
                </div>
              )}
              <div className="space-y-0.5">
                {group.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    className={({ isActive }) =>
                      `block px-3 py-2 rounded-lg text-sm transition-colors ${
                        isActive
                          ? 'bg-blue-50 text-blue-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <main className="flex-1 px-8 py-8 overflow-auto">
        {children}
      </main>
    </div>
  )
}