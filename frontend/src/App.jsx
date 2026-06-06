import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import AccountsPage from './pages/accounts/AccountsPage'
import ImportPage from './pages/import/ImportPage'
import TransactionsPage from './pages/transactions/TransactionsPage'
import CategoriesPage from './pages/categories/CategoriesPage'
import RulesPage from './pages/rules/RulesPage'
import MutualFundsPage from './pages/mutualfunds/MutualFundsPage'
import DashboardPage from './pages/dashboard/DashboardPage'


export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<AccountsPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        <Route path="/mutual-funds" element={<MutualFundsPage />} />
        <Route path="/categories" element={<CategoriesPage />} />
        <Route path="/import" element={<ImportPage />} />
        <Route path="/rules" element={<RulesPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </Layout>
  )
}