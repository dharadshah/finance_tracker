import client from './client'

export const getAccounts = () => client.get('/accounts/')
export const getAccount = (id) => client.get(`/accounts/${id}`)
export const createAccount = (data) => client.post('/accounts/', data)
export const updateAccount = (id, data) => client.patch(`/accounts/${id}`, data)
export const deleteAccount = (id) => client.delete(`/accounts/${id}`)
export const getInstitutions = () => client.get('/accounts/institutions')
export const getOwners = () => client.get('/accounts/owners')