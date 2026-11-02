import { useState } from 'react'
import { InboxPage } from './pages/InboxPage'
import { ThreadPage } from './pages/ThreadPage'
import './App.css'

function App() {
  const [selectedThreadId, setSelectedThreadId] =
    useState<string | null>(null)

  if (selectedThreadId) {
    return (
      <ThreadPage
        threadId={selectedThreadId}
        onBack={() => setSelectedThreadId(null)}
      />
    )
  }

  return (
    <InboxPage
      onOpenThread={setSelectedThreadId}
    />
  )
}

export default App