import { useState } from 'react'

import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { InboxPage } from './pages/InboxPage'
import { ThreadPage } from './pages/ThreadPage'
import { CustomersPage } from './pages/CustomersPage'
import { ProductsPage } from './pages/ProductsPage'
import { QuotationsPage } from './pages/QuotationsPage'
import { KnowledgeBasePage } from './pages/KnowledgeBasePage'

import {
  Sidebar,
  type Page,
} from './components/Sidebar'

import './App.css'

function App() {
  const [authenticated, setAuthenticated] =
    useState(
      Boolean(
        localStorage.getItem('access_token'),
      ),
    )

  const [page, setPage] =
    useState<Page>('dashboard')

  const [
    selectedThreadId,
    setSelectedThreadId,
  ] = useState<string | null>(null)

  function logout() {
    localStorage.removeItem('access_token')
    setAuthenticated(false)
    setSelectedThreadId(null)
    setPage('dashboard')
  }

  if (!authenticated) {
    return (
      <LoginPage
        onLogin={() =>
          setAuthenticated(true)
        }
      />
    )
  }

  if (
    page === 'inbox' &&
    selectedThreadId
  ) {
    return (
      <div className="app-shell">
        <Sidebar
          page={page}
          onNavigate={(next) => {
            setSelectedThreadId(null)
            setPage(next)
          }}
          onLogout={logout}
        />

        <main className="app-content">
          <ThreadPage
            threadId={selectedThreadId}
            onBack={() =>
              setSelectedThreadId(null)
            }
          />
        </main>
      </div>
    )
  }

  let content

  switch (page) {
    case 'dashboard':
      content = (
        <DashboardPage
          onNavigate={setPage}
        />
      )
      break

    case 'inbox':
      content = (
        <InboxPage
          onOpenThread={
            setSelectedThreadId
          }
        />
      )
      break

    case 'customers':
      content = <CustomersPage />
      break

    case 'knowledge':
      content = <KnowledgeBasePage />
      break

    case 'products':
      content = <ProductsPage />
      break

    case 'quotations':
      content = <QuotationsPage />
      break

    default:
      content = (
        <DashboardPage
          onNavigate={setPage}
        />
      )
      break
  }

  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        onNavigate={(next) => {
          setSelectedThreadId(null)
          setPage(next)
        }}
        onLogout={logout}
      />

      <main className="app-content">
        {content}
      </main>
    </div>
  )
}

export default App