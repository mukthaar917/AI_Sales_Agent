export type Page =
  | 'dashboard'
  | 'customers'
  | 'inbox'
  | 'knowledge'
  | 'products'
  | 'quotations'

interface Props {
  page: Page
  onNavigate: (page: Page) => void
  onLogout: () => void
}

export function Sidebar({
  page,
  onNavigate,
  onLogout,
}: Props) {
  const items: Array<{
    page: Page
    icon: string
    label: string
  }> = [
    { page: 'dashboard', icon: '▦', label: 'Dashboard' },
    { page: 'customers', icon: '♙', label: 'Customers' },
    { page: 'inbox', icon: '✉', label: 'AI Inbox' },
    { page: 'knowledge', icon: '◇', label: 'Knowledge Base' },
    { page: 'products', icon: '□', label: 'Products' },
    { page: 'quotations', icon: '▤', label: 'Quotations' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">AI</div>
        <div>
          <strong>AI Sales Agent</strong>
          <span>Sales Intelligence</span>
        </div>
      </div>

      <nav>
        {items.map((item) => (
          <button
            key={item.page}
            className={
              page === item.page
                ? 'nav-item active'
                : 'nav-item'
            }
            onClick={() =>
              onNavigate(item.page)
            }
          >
            <span className="nav-icon">
              {item.icon}
            </span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button
          className="nav-item"
          onClick={onLogout}
        >
          <span className="nav-icon">↪</span>
          Logout
        </button>
      </div>
    </aside>
  )
}
