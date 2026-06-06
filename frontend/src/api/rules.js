import client from './client'

export const getRules = () => client.get('/rules/')
export const createRule = (data) => client.post('/rules/', data)
export const deleteRule = (id) => client.delete(`/rules/${id}`)
export const getCorrections = () => client.get('/rules/corrections')
