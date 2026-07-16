import { useEffect, useState, useMemo } from 'react'
import axios from 'axios'

const fmt = (n) =>
  `Rs.${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

export default function SpeedForcePage() {
  const [investment, setInvestment] = useState(null)
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    axios
      .get('/api/alt-investments/')
      .then((r) => {
        const sf = r.data.find((i) => i.name.toLowerCase().includes('speedforce'))
        if (!sf) {
          setError('SpeedForce investment not found.')
          return
        }
        setInvestment(sf)
        return axios.get(`/api/alt-investments/${sf.id}/payments`)
      })
      .then((r) => {
        if (r) setPayments(r.data)
      })
      .catch(() => setError('Failed to load SpeedForce data'))
      .finally(() => setLoading(false))
  }, [])

  const totalReceived = useMemo(
    () => payments.reduce((s, p) => s + p.amount_received, 0),
    [payments]
  )

  const expectedToDate = useMemo(() => {
    if (!investment) return 0
    return investment.months_elapsed * (investment.monthly_income_expected || 0)
  }, [investment])

  const receiptPct = useMemo(() => {
    if (!expectedToDate) return 0
    return (totalReceived / expectedToDate) * 100
  }, [totalReceived, expectedToDate])

  const totalExpected = investment
    ? (investment.total_expected_return || 0)
    : 0

  const overallProgressPct = useMemo(() => {
    if (!totalExpected || !investment) return 0
    return ((totalReceived + (investment.salvage_value || 0)) / totalExpected) * 100
  }, [totalReceived, totalExpected, investment])

  if (loading) return <div className="text-gray-500">Loading...</div>
  if (error) return <div className="p-3 bg-red-50 text-red-700 rounded-lg">{error}</div>
  if (!investment) return null

  const startDate = new Date(investment.investment_date)
  const endDate = new Date(startDate)
  endDate.setMonth(endDate.getMonth() + (investment.tenure_months || 48))

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">SpeedForce EV Fleet Rental</h1>
        <p className="text-sm text-gray-500 mt-1">
          {investment.plan_name} — {investment.num_vehicles} vehicles —
          Started {startDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })} —
          Ends {endDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Invested</div>
          <div className="text-xl font-bold text-gray-900">
            {fmt(investment.invested_amount)}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {investment.num_vehicles} vehicles @ Rs.{investment.per_vehicle_rental}/mo
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Monthly Rental</div>
          <div className="text-xl font-bold text-blue-600">
            {fmt(investment.monthly_income_expected)}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {investment.yearly_rental_pct}% annual yield
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Total Expected (48 mo + salvage)</div>
          <div className="text-xl font-bold text-green-600">
            {fmt(totalExpected)}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            Salvage {fmt(investment.salvage_value)} at end
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-xs text-gray-500 mb-1">Tenure</div>
          <div className="text-xl font-bold text-gray-900">
            {investment.months_elapsed} / {investment.tenure_months} mo
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {investment.months_remaining} months remaining
          </div>
        </div>
      </div>

      {/* Progress bars */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Progress</h2>

        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Tenure elapsed</span>
            <span>{investment.months_elapsed} of {investment.tenure_months} months</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${Math.min(100, (investment.months_elapsed / (investment.tenure_months || 48)) * 100)}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Received vs expected to date</span>
            <span>{fmt(totalReceived)} of {fmt(expectedToDate)}</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${receiptPct >= 100 ? 'bg-green-500' : 'bg-orange-400'}`}
              style={{ width: `${Math.min(100, receiptPct)}%` }}
            />
          </div>
          {payments.length === 0 && (
            <div className="text-xs text-gray-400 mt-1">No payments received yet</div>
          )}
        </div>
      </div>

      {/* Plan details */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Plan Summary</h2>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-gray-50">
            <tr>
              <td className="py-2 text-gray-500">Slab</td>
              <td className="py-2 font-medium text-right">{investment.plan_name}</td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">Vehicles</td>
              <td className="py-2 font-medium text-right">{investment.num_vehicles}</td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">Per Vehicle Rental</td>
              <td className="py-2 font-medium text-right">Rs.{investment.per_vehicle_rental}/mo</td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">Monthly Rental</td>
              <td className="py-2 font-medium text-right text-blue-600">{fmt(investment.monthly_income_expected)}</td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">48 Month Total Rental</td>
              <td className="py-2 font-medium text-right">{fmt((investment.monthly_income_expected || 0) * 48)}</td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">Salvage Value (15%) at end</td>
              <td className="py-2 font-medium text-right">{fmt(investment.salvage_value)}</td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">Final Amount</td>
              <td className="py-2 font-bold text-right text-green-600">{fmt(totalExpected)}</td>
            </tr>
            <tr>
              <td className="py-2 text-gray-500">Annual Yield</td>
              <td className="py-2 font-medium text-right">{investment.yearly_rental_pct}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Payments table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">
            Payments Received
            {payments.length > 0 && (
              <span className="ml-2 text-gray-400 font-normal">
                {payments.length} of {investment.tenure_months} months — Total {fmt(totalReceived)}
              </span>
            )}
          </h2>
        </div>

        {payments.length === 0 ? (
          <div className="px-5 py-8 text-center">
            <div className="text-gray-400 text-sm">No payments received yet</div>
            <div className="text-gray-300 text-xs mt-1">
              First payment expected around{' '}
              {new Date(
                new Date(investment.investment_date).setMonth(
                  new Date(investment.investment_date).getMonth() + 1
                )
              ).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}
            </div>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Month</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Payment Date</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">Amount</th>
                <th className="text-right px-4 py-3 text-gray-600 font-medium">vs Expected</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {payments.map((p) => {
                const diff = p.amount_received - (investment.monthly_income_expected || 0)
                return (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-700 font-medium">{p.payment_month}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(p.payment_date).toLocaleDateString('en-GB').replace(/\//g, '-')}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-green-600">
                      {fmt(p.amount_received)}
                    </td>
                    <td className={`px-4 py-3 text-right text-xs font-medium ${diff >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                      {diff >= 0 ? '+' : ''}{fmt(diff)}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{p.notes || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot className="bg-gray-50 border-t-2 border-gray-200">
              <tr>
                <td colSpan={2} className="px-4 py-3 font-bold text-gray-800">Total</td>
                <td className="px-4 py-3 text-right font-bold text-green-600">{fmt(totalReceived)}</td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        )}
      </div>

      {investment.notes && (
        <div className="mt-4 text-xs text-gray-400 px-1">{investment.notes}</div>
      )}
    </div>
  )
}