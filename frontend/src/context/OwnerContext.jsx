import { createContext, useContext, useState } from 'react'

const OwnerContext = createContext()

export function OwnerProvider({ children }) {
  const [owner, setOwner] = useState('Dhara')
  return (
    <OwnerContext.Provider value={{ owner, setOwner }}>
      {children}
    </OwnerContext.Provider>
  )
}

export function useOwner() {
  return useContext(OwnerContext)
}