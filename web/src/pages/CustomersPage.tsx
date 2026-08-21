import {
  type FormEvent,
  useEffect,
  useState,
} from 'react'

import {
  createCustomer,
  deleteCustomer,
  getCustomers,
  type Customer,
} from '../api/customers'

export function CustomersPage() {
  const [customers, setCustomers] =
    useState<Customer[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [search, setSearch] =
    useState('')

  const [showForm, setShowForm] =
    useState(false)

  const [companyName, setCompanyName] =
    useState('')

  const [contactName, setContactName] =
    useState('')

  const [email, setEmail] =
    useState('')

  const [phone, setPhone] =
    useState('')

  const [city, setCity] =
    useState('')

  const [country, setCountry] =
    useState('')

  const [notes, setNotes] =
    useState('')

  async function loadCustomers(
    searchValue = '',
  ) {
    try {
      setLoading(true)
      setError('')

      const result =
        await getCustomers(searchValue)

      setCustomers(result.items)
    } catch (err) {
      console.error(err)
      setError('Unable to load customers.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadCustomers()
  }, [])

  async function handleSubmit(
    event: FormEvent,
  ) {
    event.preventDefault()

    if (!companyName.trim()) {
      setError('Company name is required.')
      return
    }

    try {
      setError('')

      await createCustomer({
        company_name: companyName.trim(),
        contact_name:
          contactName.trim() || null,
        email: email.trim() || null,
        phone: phone.trim() || null,
        city: city.trim() || null,
        country: country.trim() || null,
        notes: notes.trim() || null,
      })

      setCompanyName('')
      setContactName('')
      setEmail('')
      setPhone('')
      setCity('')
      setCountry('')
      setNotes('')
      setShowForm(false)

      await loadCustomers(search)
    } catch (err) {
      console.error(err)
      setError('Unable to create customer.')
    }
  }

  async function handleDelete(
    customer: Customer,
  ) {
    const confirmed = window.confirm(
      `Deactivate ${customer.company_name}?`,
    )

    if (!confirmed) {
      return
    }

    try {
      await deleteCustomer(customer.id)
      await loadCustomers(search)
    } catch (err) {
      console.error(err)
      setError('Unable to remove customer.')
    }
  }

  async function handleSearch(
    event: FormEvent,
  ) {
    event.preventDefault()
    await loadCustomers(search)
  }

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">
            AI SALES AGENT
          </p>

          <h1>Customers</h1>

          <p className="subtitle">
            Manage leads, customers and
            sales contacts.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() =>
            setShowForm(!showForm)
          }
        >
          {showForm
            ? 'Cancel'
            : '+ Add Customer'}
        </button>
      </header>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {showForm && (
        <form
          className="customer-form"
          onSubmit={handleSubmit}
        >
          <h2>Add Customer</h2>

          <div className="form-grid">
            <input
              placeholder="Company name *"
              value={companyName}
              onChange={(e) =>
                setCompanyName(e.target.value)
              }
            />

            <input
              placeholder="Contact name"
              value={contactName}
              onChange={(e) =>
                setContactName(e.target.value)
              }
            />

            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) =>
                setEmail(e.target.value)
              }
            />

            <input
              placeholder="Phone"
              value={phone}
              onChange={(e) =>
                setPhone(e.target.value)
              }
            />

            <input
              placeholder="City"
              value={city}
              onChange={(e) =>
                setCity(e.target.value)
              }
            />

            <input
              placeholder="Country"
              value={country}
              onChange={(e) =>
                setCountry(e.target.value)
              }
            />
          </div>

          <textarea
            placeholder="Notes"
            value={notes}
            onChange={(e) =>
              setNotes(e.target.value)
            }
          />

          <button
            className="primary-button"
            type="submit"
          >
            Save Customer
          </button>
        </form>
      )}

      <form
        className="customer-search"
        onSubmit={handleSearch}
      >
        <input
          placeholder="Search customers..."
          value={search}
          onChange={(e) =>
            setSearch(e.target.value)
          }
        />

        <button type="submit">
          Search
        </button>
      </form>

      <div className="customers-card">
        {loading ? (
          <p>Loading customers...</p>
        ) : customers.length === 0 ? (
          <div className="empty-state">
            <h3>No customers yet</h3>
            <p>
              Add your first customer to
              start the sales workflow.
            </p>
          </div>
        ) : (
          <div className="customer-table-wrap">
            <table className="customer-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Contact</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {customers.map(
                  (customer) => (
                    <tr key={customer.id}>
                      <td>
                        <strong>
                          {
                            customer.company_name
                          }
                        </strong>
                      </td>

                      <td>
                        {customer.contact_name ||
                          '—'}
                      </td>

                      <td>
                        {customer.email || '—'}
                      </td>

                      <td>
                        {customer.phone || '—'}
                      </td>

                      <td>
                        {[
                          customer.city,
                          customer.country,
                        ]
                          .filter(Boolean)
                          .join(', ') || '—'}
                      </td>

                      <td>
                        {customer.is_active
                          ? 'Active'
                          : 'Inactive'}
                      </td>

                      <td>
                        <button
                          type="button"
                          onClick={() =>
                            handleDelete(
                              customer,
                            )
                          }
                        >
                          Deactivate
                        </button>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}