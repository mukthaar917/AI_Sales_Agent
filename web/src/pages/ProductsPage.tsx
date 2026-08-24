import {
  type FormEvent,
  useEffect,
  useState,
} from 'react'

import {
  createProduct,
  deleteProduct,
  getProducts,
  type Product,
} from '../api/products'

export function ProductsPage() {
  const [products, setProducts] =
    useState<Product[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [search, setSearch] =
    useState('')

  const [showForm, setShowForm] =
    useState(false)

  const [sku, setSku] =
    useState('')

  const [name, setName] =
    useState('')

  const [description, setDescription] =
    useState('')

  const [unit, setUnit] =
    useState('unit')

  const [unitPrice, setUnitPrice] =
    useState('')

  const [currency, setCurrency] =
    useState('USD')

  const [taxRate, setTaxRate] =
    useState('0')

  async function loadProducts(
    searchValue = '',
  ) {
    try {
      setLoading(true)
      setError('')

      const result =
        await getProducts(searchValue)

      setProducts(result.items)
    } catch (err) {
      console.error(err)
      setError('Unable to load products.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadProducts()
  }, [])

  async function handleSubmit(
    event: FormEvent,
  ) {
    event.preventDefault()

    if (!sku.trim()) {
      setError('SKU is required.')
      return
    }

    if (!name.trim()) {
      setError('Product name is required.')
      return
    }

    const price = Number(unitPrice)
    const tax = Number(taxRate)

    if (!Number.isFinite(price) || price <= 0) {
      setError('Unit price must be greater than 0.')
      return
    }

    if (
      !Number.isFinite(tax) ||
      tax < 0 ||
      tax > 100
    ) {
      setError(
        'Tax rate must be between 0 and 100.',
      )
      return
    }

    try {
      setError('')

      await createProduct({
        sku: sku.trim(),
        name: name.trim(),
        description:
          description.trim() || null,
        unit: unit.trim() || 'unit',
        unit_price: price,
        currency:
          currency.trim().toUpperCase(),
        tax_rate: tax,
      })

      setSku('')
      setName('')
      setDescription('')
      setUnit('unit')
      setUnitPrice('')
      setCurrency('USD')
      setTaxRate('0')
      setShowForm(false)

      await loadProducts(search)
    } catch (err: any) {
      console.error(err)

      const detail =
        err?.response?.data?.detail

      setError(
        detail ||
          'Unable to create product.',
      )
    }
  }

  async function handleDelete(
    product: Product,
  ) {
    const confirmed = window.confirm(
      `Deactivate ${product.name}?`,
    )

    if (!confirmed) {
      return
    }

    try {
      setError('')
      await deleteProduct(product.id)
      await loadProducts(search)
    } catch (err) {
      console.error(err)
      setError(
        'Unable to deactivate product.',
      )
    }
  }

  async function handleSearch(
    event: FormEvent,
  ) {
    event.preventDefault()
    await loadProducts(search)
  }

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">
            AI SALES AGENT
          </p>

          <h1>Products & Services</h1>

          <p className="subtitle">
            Manage products, services,
            pricing and tax rates.
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
            : '+ Add Product'}
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
          <h2>Add Product / Service</h2>

          <div className="form-grid">
            <input
              placeholder="SKU *"
              value={sku}
              onChange={(e) =>
                setSku(e.target.value)
              }
            />

            <input
              placeholder="Product name *"
              value={name}
              onChange={(e) =>
                setName(e.target.value)
              }
            />

            <input
              placeholder="Unit"
              value={unit}
              onChange={(e) =>
                setUnit(e.target.value)
              }
            />

            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder="Unit price *"
              value={unitPrice}
              onChange={(e) =>
                setUnitPrice(e.target.value)
              }
            />

            <input
              maxLength={3}
              placeholder="Currency"
              value={currency}
              onChange={(e) =>
                setCurrency(e.target.value)
              }
            />

            <input
              type="number"
              min="0"
              max="100"
              step="0.01"
              placeholder="Tax rate %"
              value={taxRate}
              onChange={(e) =>
                setTaxRate(e.target.value)
              }
            />
          </div>

          <textarea
            placeholder="Description"
            value={description}
            onChange={(e) =>
              setDescription(e.target.value)
            }
          />

          <button
            className="primary-button"
            type="submit"
          >
            Save Product
          </button>
        </form>
      )}

      <form
        className="customer-search"
        onSubmit={handleSearch}
      >
        <input
          placeholder="Search products..."
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
          <p>Loading products...</p>
        ) : products.length === 0 ? (
          <div className="empty-state">
            <h3>No products yet</h3>
            <p>
              Add your first product or
              service to start creating
              quotations.
            </p>
          </div>
        ) : (
          <div className="customer-table-wrap">
            <table className="customer-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Name</th>
                  <th>Unit</th>
                  <th>Price</th>
                  <th>Tax</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {products.map(
                  (product) => (
                    <tr key={product.id}>
                      <td>{product.sku}</td>

                      <td>
                        <strong>
                          {product.name}
                        </strong>
                        {product.description && (
                          <div>
                            {
                              product.description
                            }
                          </div>
                        )}
                      </td>

                      <td>{product.unit}</td>

                      <td>
                        {product.currency}{' '}
                        {Number(
                          product.unit_price,
                        ).toFixed(2)}
                      </td>

                      <td>
                        {Number(
                          product.tax_rate,
                        ).toFixed(2)}
                        %
                      </td>

                      <td>
                        {product.is_active
                          ? 'Active'
                          : 'Inactive'}
                      </td>

                      <td>
                        <button
                          type="button"
                          onClick={() =>
                            handleDelete(
                              product,
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