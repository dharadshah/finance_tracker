import client from './client'

export const getParsers = () => client.get('/import/parsers')
export const importStatement = (formData) =>
  client.post('/import/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })