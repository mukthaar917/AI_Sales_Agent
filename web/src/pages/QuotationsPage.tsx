import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  getCustomers,
  type Customer,
} from '../api/customers'

import {
  getProducts,
  type Product,
} from '../api/products'

import {
  createQuotation,
  downloadQuotationPdf,
  getQuotations,
  type Quotation,
} from '../api/quotations'

interface DraftItem {
  product_id: string
  description: string
  quantity: string
  unit: string
  unit_price: string
  discount_rate: string
  tax_rate: string
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function plusDaysIso(days: number) {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

export function QuotationsPage() {
  const [customers, setCustomers] =
    useState<Customer[]>([])

  const [products, setProducts] =
    useState<Product[]>([])

  const [quotations, setQuotations] =
    useState<Quotation[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [showForm, setShowForm] =
    useState(false)

  const [customerId, setCustomerId] =
    useState('')

  const [issueDate, setIssueDate] =
    useState(todayIso())

  const [expiryDate, setExpiryDate] =
    useState(plusDaysIso(14))

  const [currency, setCurrency] =
    useState('USD')

  const [notes, setNotes] =
    useState('')

  const [terms, setTerms] =
    useState(
      'Payment due within 14 days.',
    )

  const [items, setItems] =
    useState<DraftItem[]>([])

  async function loadData() {
    try {
      setLoading(true)
      setError('')

      const [
        customerResult,
        productResult,
        quotationResult,
      ] = await Promise.all([
        getCustomers(),
        getProducts(),
        getQuotations(),
      ])

      setCustomers(customerResult.items)
      setProducts(productResult.items)
      setQuotations(quotationResult.items)
    } catch (err) {
      console.error(err)
      setError(
        'Unable to load quotation data.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  function addProduct(productId: string) {
    const product =
      products.find(
        (item) => item.id === productId,
      )

    if (!product) {
      return
    }

    setItems((current) => [
      ...current,
      {
        product_id: product.id,
        description:
          product.description ||
          product.name,
        quantity: '1',
        unit: product.unit,
        unit_price: product.unit_price,
        discount_rate: '0',
        tax_rate: product.tax_rate,
      },
    ])
  }

  function updateItem(
    index: number,
    field: keyof DraftItem,
    value: string,
  ) {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              [field]: value,
            }
          : item,
      ),
    )
  }

  function removeItem(index: number) {
    setItems((current) =>
      current.filter(
        (_, itemIndex) =>
          itemIndex !== index,
      ),
    )
  }

  const estimatedTotal = useMemo(() => {
    return items.reduce(
      (total, item) => {
        const quantity =
          Number(item.quantity) || 0

        const price =
          Number(item.unit_price) || 0

        const discount =
          Number(item.discount_rate) || 0

        const tax =
          Number(item.tax_rate) || 0

        const subtotal =
          quantity * price

        const discountAmount =
          subtotal * (discount / 100)

        const afterDiscount =
          subtotal - discountAmount

        const taxAmount =
          afterDiscount * (tax / 100)

        return (
          total +
          afterDiscount +
          taxAmount
        )
      },
      0,
    )
  }, [items])

  async function handleSubmit(
    event: FormEvent,
  ) {
    event.preventDefault()

    if (!customerId) {
      setError(
        'Please select a customer.',
      )
      return
    }

    if (items.length === 0) {
      setError(
        'Please add at least one product.',
      )
      return
    }

    try {
      setError('')

      await createQuotation({
        customer_id: customerId,
        issue_date: issueDate,
        expiry_date: expiryDate,
        currency:
          currency.trim().toUpperCase(),
        notes: notes.trim() || null,
        terms: terms.trim() || null,
        items: items.map(
          (item, index) => ({
            product_id:
              item.product_id || null,
            description:
              item.description.trim(),
            quantity:
              Number(item.quantity),
            unit:
              item.unit.trim(),
            unit_price:
              Number(item.unit_price),
            discount_rate:
              Number(item.discount_rate),
            tax_rate:
              Number(item.tax_rate),
            sort_order: index + 1,
          }),
        ),
      })

      setCustomerId('')
      setIssueDate(todayIso())
      setExpiryDate(plusDaysIso(14))
      setCurrency('USD')
      setNotes('')
      setTerms(
        'Payment due within 14 days.',
      )
      setItems([])
      setShowForm(false)

      await loadData()
    } catch (err: any) {
      console.error(err)

      setError(
        err?.response?.data?.detail ||
          'Unable to create quotation.',
      )
    }
  }

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">
            AI SALES AGENT
          </p>

          <h1>Quotations</h1>

          <p className="subtitle">
            Create quotations from
            customers and products.
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
            : '+ Create Quotation'}
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
          <h2>Create Quotation</h2>

          <div className="form-grid">
            <select
              value={customerId}
              onChange={(e) =>
                setCustomerId(
                  e.target.value,
                )
              }
            >
              <option value="">
                Select customer
              </option>

              {customers.map(
                (customer) => (
                  <option
                    key={customer.id}
                    value={customer.id}
                  >
                    {
                      customer.company_name
                    }
                  </option>
                ),
              )}
            </select>

            <select
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) {
                  addProduct(
                    e.target.value,
                  )
                  e.target.value = ''
                }
              }}
            >
              <option value="">
                + Add product
              </option>

              {products.map(
                (product) => (
                  <option
                    key={product.id}
                    value={product.id}
                  >
                    {product.sku} —{' '}
                    {product.name}
                  </option>
                ),
              )}
            </select>

            <input
              type="date"
              value={issueDate}
              onChange={(e) =>
                setIssueDate(
                  e.target.value,
                )
              }
            />

            <input
              type="date"
              value={expiryDate}
              onChange={(e) =>
                setExpiryDate(
                  e.target.value,
                )
              }
            />

            <input
              maxLength={3}
              value={currency}
              onChange={(e) =>
                setCurrency(
                  e.target.value,
                )
              }
              placeholder="Currency"
            />
          </div>

          {items.length > 0 && (
            <div className="customer-table-wrap">
              <table className="customer-table">
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Price</th>
                    <th>Discount %</th>
                    <th>Tax %</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  {items.map(
                    (item, index) => (
                      <tr key={index}>
                        <td>
                          <input
                            value={
                              item.description
                            }
                            onChange={(e) =>
                              updateItem(
                                index,
                                'description',
                                e.target.value,
                              )
                            }
                          />
                        </td>

                        <td>
                          <input
                            type="number"
                            min="0.01"
                            step="0.01"
                            value={
                              item.quantity
                            }
                            onChange={(e) =>
                              updateItem(
                                index,
                                'quantity',
                                e.target.value,
                              )
                            }
                          />
                        </td>

                        <td>
                          <input
                            value={item.unit}
                            onChange={(e) =>
                              updateItem(
                                index,
                                'unit',
                                e.target.value,
                              )
                            }
                          />
                        </td>

                        <td>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={
                              item.unit_price
                            }
                            onChange={(e) =>
                              updateItem(
                                index,
                                'unit_price',
                                e.target.value,
                              )
                            }
                          />
                        </td>

                        <td>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={
                              item.discount_rate
                            }
                            onChange={(e) =>
                              updateItem(
                                index,
                                'discount_rate',
                                e.target.value,
                              )
                            }
                          />
                        </td>

                        <td>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={
                              item.tax_rate
                            }
                            onChange={(e) =>
                              updateItem(
                                index,
                                'tax_rate',
                                e.target.value,
                              )
                            }
                          />
                        </td>

                        <td>
                          <button
                            type="button"
                            onClick={() =>
                              removeItem(
                                index,
                              )
                            }
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}

          <p>
            <strong>
              Estimated Total:{' '}
              {currency.toUpperCase()}{' '}
              {estimatedTotal.toFixed(2)}
            </strong>
          </p>

          <textarea
            placeholder="Notes"
            value={notes}
            onChange={(e) =>
              setNotes(e.target.value)
            }
          />

          <textarea
            placeholder="Terms"
            value={terms}
            onChange={(e) =>
              setTerms(e.target.value)
            }
          />

          <button
            className="primary-button"
            type="submit"
          >
            Generate Quotation
          </button>
        </form>
      )}

      <div className="customers-card">
        {loading ? (
          <p>
            Loading quotations...
          </p>
        ) : quotations.length === 0 ? (
          <div className="empty-state">
            <h3>
              No quotations yet
            </h3>

            <p>
              Create your first
              customer quotation.
            </p>
          </div>
        ) : (
          <div className="customer-table-wrap">
            <table className="customer-table">
              <thead>
                <tr>
                  <th>Quotation</th>
                  <th>Customer</th>
                  <th>Issue Date</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>PDF</th>
                </tr>
              </thead>

              <tbody>
                {quotations.map(
                  (quotation) => {
                    const customer =
                      customers.find(
                        (item) =>
                          item.id ===
                          quotation.customer_id,
                      )

                    return (
                      <tr
                        key={
                          quotation.id
                        }
                      >
                        <td>
                          <strong>
                            {
                              quotation.quotation_number
                            }
                          </strong>
                        </td>

                        <td>
                          {customer
                            ?.company_name ||
                            quotation.customer_id}
                        </td>

                        <td>
                          {
                            quotation.issue_date
                          }
                        </td>

                        <td>
                          {
                            quotation.status
                          }
                        </td>

                        <td>
                          {
                            quotation.currency
                          }{' '}
                          {Number(
                            quotation.total_amount,
                          ).toFixed(2)}
                        </td>

                        <td>
                          <button
                            type="button"
                            onClick={() =>
                              downloadQuotationPdf(
                                quotation.id,
                                quotation.quotation_number,
                              )
                            }
                          >
                            Download PDF
                          </button>
                        </td>
                      </tr>
                    )
                  },
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}