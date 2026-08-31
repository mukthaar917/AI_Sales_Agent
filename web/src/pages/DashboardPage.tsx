import type { Page } from '../components/Sidebar'

interface Props {
  onNavigate: (page: Page) => void
}

export function DashboardPage({
  onNavigate,
}: Props) {
  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">AI SALES AGENT</p>
          <h1>Sales Dashboard</h1>
          <p className="subtitle">
            Manage customers, conversations,
            opportunities and quotations.
          </p>
        </div>

        <span className="system-online">
          ● System Online
        </span>
      </header>

      <section className="metrics-grid">
        <div className="metric-card">
          <span>Customers</span>
          <strong>Customer CRM</strong>
          <p>Manage leads and sales contacts</p>
        </div>

        <div className="metric-card">
          <span>AI Inbox</span>
          <strong>Email Agent</strong>
          <p>Analyze and respond to inquiries</p>
        </div>

        <div className="metric-card">
          <span>Products</span>
          <strong>Product Catalog</strong>
          <p>Products, pricing and tax rates</p>
        </div>

        <div className="metric-card">
          <span>Quotes</span>
          <strong>Quote Agent</strong>
          <p>Create AI-assisted quotations</p>
        </div>
      </section>

      <h2 className="section-title">
        AI Agent Workflows
      </h2>

      <section className="agent-grid">
        <article className="agent-card">
          <div className="agent-number">01</div>
          <h2>Sales Agent</h2>
          <p>
            Analyze customer inquiries, generate
            intelligent replies, search knowledge
            and detect sales opportunities.
          </p>

          <div className="workflow">
            Inquiry → AI Analysis → Reply
            → Opportunity
          </div>

          <button
            className="primary-button"
            onClick={() =>
              onNavigate('customers')
            }
          >
            Open Sales Agent
          </button>
        </article>

        <article className="agent-card">
          <div className="agent-number">02</div>
          <h2>Quote Agent</h2>
          <p>
            Select customers and products,
            prepare quotations and generate
            professional PDF documents.
          </p>

          <div className="workflow">
            Customer → Products → Quote → PDF
          </div>

          <button
            className="primary-button"
            onClick={() =>
              onNavigate('quotations')
            }
          >
            Open Quote Agent
          </button>
        </article>

        <article className="agent-card">
          <div className="agent-number">03</div>
          <h2>Email Agent</h2>
          <p>
            Synchronize Gmail conversations,
            summarize messages and generate
            AI-assisted responses.
          </p>

          <div className="workflow">
            Inbox → Summary → AI Reply → Draft
          </div>

          <button
            className="primary-button"
            onClick={() =>
              onNavigate('inbox')
            }
          >
            Open Email Agent
          </button>
        </article>
      </section>
    </div>
  )
}
