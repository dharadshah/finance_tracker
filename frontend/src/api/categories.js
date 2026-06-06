import client from './client'

export const getCategories = () => client.get('/categories/')
export const createCategory = (data) => client.post('/categories/', data)
export const updateCategory = (id, data) => client.patch(`/categories/${id}`, data)
export const deleteCategory = (id) => client.delete(`/categories/${id}`)