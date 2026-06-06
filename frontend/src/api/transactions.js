import client from './client'

export const getTransactions = (params) => client.get('/transactions/', { params })
export const correctCategory = (id, categoryName) =>
  client.patch(`/transactions/${id}/category`, { category_name: categoryName })
export const bulkCorrectCategory = (transactionIds, categoryName) =>
  client.post('/transactions/bulk-correct', {
    transaction_ids: transactionIds,
    category_name: categoryName,
  })
export const bulkDelete = (transactionIds) =>
  client.post('/transactions/bulk-delete', { transaction_ids: transactionIds })
export const deleteTransaction = (id) => client.delete(`/transactions/${id}`)