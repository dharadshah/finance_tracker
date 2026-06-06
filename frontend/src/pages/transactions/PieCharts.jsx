import { useMemo } from 'react'

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#6b7280',
]

function PieChart({ title, data, totalLabel }) {
  const total = data.reduce((sum, d) => sum + d.value, 0)

  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-1">{title}</h3>
        <p className="text-gray-400 text-sm mt-6">No data</p>
      </div>
    )
  }

  let angle = -Math.PI / 2
  const cx = 80, cy = 80, r = 70

  const slices = data.map((d, i) => {
    const sweep = (d.value / total) * 2 * Math.PI
    const x1 = cx + r * Math.cos(angle)
    const y1 = cy + r * Math.sin(angle)
    angle += sweep
    const x2 = cx + r * Math.cos(angle)
    const y2 = cy + r * Math.sin(angle)
    const large = sweep > Math.PI ? 1 : 0
    return {
      path: `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`,
      color: COLORS[i % COLORS.length],
      label: d.label,
      value: d.value,
      pct: ((d.value / total) * 100).toFixed(1),
    }
  })

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-1">{title}</h3>
      <p className="text-xs text-gray-400 mb-3">
        Total: ₹{total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
      </p>
      <div className="flex gap-4 items-start">
        <svg width="160" height="160" viewBox="0 0 160 160">
          {slices.map((s, i) => (
            <path key={i} d={s.path} fill={s.color} stroke="white" strokeWidth="1" />
          ))}
        </svg>
        <div className="flex-1 space-y-1.5 min-w-0">
            {slices.map((s, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                <div
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5"
                    style={{ backgroundColor: s.color }}
                />
                <div className="flex-1 min-w-0">
                    <div className="text-gray-600 break-words leading-tight">{s.label}</div>
                    <div className="text-gray-400">
                        {s.pct}% · ₹{s.value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </div>
                    </div>
                </div>
            ))}
            </div>
      </div>
    </div>
  )
}

export default function PieCharts({ transactions }) {
  const { expenseData, incomeData, investmentData, transferData } = useMemo(() => {
    const expenseMap = {}
    const incomeMap = {}
    const investmentMap = {}
    const transferMap = {}

    transactions.forEach((t) => {
        const label = t.category || 'Uncategorised'
        if (t.txn_type === 'expense') {
            expenseMap[label] = (expenseMap[label] || 0) + t.amount
        } else if (t.txn_type === 'income') {
            incomeMap[label] = (incomeMap[label] || 0) + t.amount
        } else if (t.txn_type === 'investment') {
            investmentMap[label] = (investmentMap[label] || 0) + t.amount
        } else if (t.txn_type === 'transfer') {
            transferMap[label] = (transferMap[label] || 0) + t.amount
        }
    })

    const toData = (map) =>
      Object.entries(map)
        .map(([label, value]) => ({ label, value }))
        .sort((a, b) => b.value - a.value)

    return {
      expenseData: toData(expenseMap),
      incomeData: toData(incomeMap),
      investmentData: toData(investmentMap),
      transferData: toData(transferMap),
    }
  }, [transactions])

  const hasData = expenseData.length > 0 || incomeData.length > 0 || 
                  investmentData.length > 0 || transferData.length > 0
  if (!hasData) return null

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <PieChart title="Expenses" data={expenseData} />
      <PieChart title="Income" data={incomeData} />
      <PieChart title="Investments" data={investmentData} />
      <PieChart title="Transfers" data={transferData} />
    </div>
  )
}