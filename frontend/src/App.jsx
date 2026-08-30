import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import AccountsPage from './pages/accounts/AccountsPage'
import ImportPage from './pages/import/ImportPage'
import TransactionsPage from './pages/transactions/TransactionsPage'
import CategoriesPage from './pages/categories/CategoriesPage'
import RulesPage from './pages/rules/RulesPage'
import MutualFundsPage from './pages/mutualfunds/MutualFundsPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import DividendsPage from './pages/dividends/DividendsPage'
import StocksPage from './pages/stocks/StocksPage'
import MFInvestmentTrackerPage from './pages/mutualfunds/MFInvestmentTrackerPage'
import SpeedForcePage from './pages/alternative/SpeedForcePage'
import RebalancePage from './pages/mutualfunds/RebalancePage'

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
        <Route path="/dividends" element={<DividendsPage />} />
        <Route path="/stocks" element={<StocksPage />} />
        <Route path="/mf-investment" element={<MFInvestmentTrackerPage />} />
        <Route path="/speedforce" element={<SpeedForcePage />} />
        <Route path="/rebalance" element={<RebalancePage />} />
      </Routes>
    </Layout>
  )
}