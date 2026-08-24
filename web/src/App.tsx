import { useState } from 'react'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { InboxPage } from './pages/InboxPage'
import { ThreadPage } from './pages/ThreadPage'
import {
  Sidebar,
  type Page,
} from './components/Sidebar'
import './App.css'
import { ProductsPage } from './pages/ProductsPage'
import { CustomersPage } from './pages/CustomersPage'

function Placeholder({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">
            AI SALES AGENT
          </p>
          <h1>{title}</h1>
          <p className="subtitle">
            {description}
          </p>
        </div>
      </header>

      <div className="placeholder-card">
        <h2>{title}</h2>
        <p>
          This module is connected to the
          AI Sales Agent backend.
        </p>
      </div>
    </div>
  )
}

function App() {
  const [authenticated, setAuthenticated] =
    useState(
      Boolean(
        localStorage.getItem('access_token'),
      ),
    )

  const [page, setPage] =
    useState<Page>('dashboard')

  const [selectedThreadId, setSelectedThreadId] =
    useState<string | null>(null)

  function logout() {
    localStorage.removeItem('access_token')
    setAuthenticated(false)
    setSelectedThreadId(null)
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
      content = (
        <Placeholder
          title="Knowledge Base"
          description="Manage documents used by the AI RAG engine."
        />
      )
      break

    case 'products':
      content = <ProductsPage />
      break

    case 'quotations':
      content = (
        <Placeholder
          title="Quotations"
          description="Create, manage and download customer quotations."
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
