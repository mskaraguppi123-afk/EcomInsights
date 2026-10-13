import { useEffect, useState } from 'react'

function PriceChart({ observations, predictedPrice, candidatePrice }) {
  if (!observations || observations.length === 0) return null
  const prices = observations.map((o) => parseFloat(o.price))
  const allPrices = [...prices]
  if (predictedPrice) allPrices.push(parseFloat(predictedPrice))
  if (candidatePrice) allPrices.push(parseFloat(candidatePrice))

  const minP = Math.min(...allPrices)
  const maxP = Math.max(...allPrices)
  const rawSpread = maxP - minP
  const spread = rawSpread > 0 ? rawSpread : maxP * 0.1 || 10

  const width = 500
  const height = 140
  const paddingX = 45
  const paddingY = 25
  const graphW = width - paddingX * 2
  const graphH = height - paddingY * 2

  const n = observations.length
  let extraPoints = 0
  if (predictedPrice) extraPoints++
  if (candidatePrice) extraPoints++
  const totalPoints = n + extraPoints

  const points = observations.map((o, idx) => {
    const x = paddingX + (idx / Math.max(1, totalPoints - 1)) * graphW
    const normY = rawSpread > 0 ? (parseFloat(o.price) - minP) / spread : 0.5
    const y = height - paddingY - normY * graphH
    return {
      x,
      y,
      price: o.price,
      date: new Date(o.observed_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
    }
  })

  let pathD = `M ${points[0].x} ${points[0].y}`
  for (let i = 1; i < points.length; i++) {
    pathD += ` L ${points[i].x} ${points[i].y}`
  }

  const lastPt = points[points.length - 1]
  const forecastIdx = n
  const fx = paddingX + (forecastIdx / Math.max(1, totalPoints - 1)) * graphW
  const fnormY = rawSpread > 0 ? (parseFloat(predictedPrice || 0) - minP) / spread : 0.5
  const fy = height - paddingY - fnormY * graphH

  let candidateSvg = null
  if (candidatePrice && points.length > 0) {
    const candIdx = totalPoints - 1
    const cx = paddingX + (candIdx / Math.max(1, totalPoints - 1)) * graphW
    const cnormY = rawSpread > 0 ? (parseFloat(candidatePrice) - minP) / spread : 0.5
    const cy = height - paddingY - cnormY * graphH
    candidateSvg = (
      <g>
        <line x1={lastPt.x} y1={lastPt.y} x2={cx} y2={cy} stroke="#6366f1" strokeWidth="2" strokeDasharray="3 3" />
        <circle cx={cx} cy={cy} r="6" fill="#6366f1" stroke="#fff" strokeWidth="2" />
        <text x={cx} y={cy - 8} fontSize="10" fontWeight="800" fill="#4f46e5" textAnchor="middle">₹{parseFloat(candidatePrice).toFixed(0)} (Simulated Check)</text>
      </g>
    )
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e1e7e4', borderRadius: '12px', padding: '14px', marginBottom: '18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', fontWeight: '700', color: '#77827d', textTransform: 'uppercase' }}>Visual Price Trajectory & Forecast</span>
        <div style={{ display: 'flex', gap: '10px', fontSize: '10px', fontWeight: '700' }}>
          <span style={{ color: '#1f7359' }}>● Historical Trend</span>
          {predictedPrice && <span style={{ color: '#f59e0b' }}>--- AI Forecast</span>}
          {candidatePrice && <span style={{ color: '#6366f1' }}>--- Simulated Deal</span>}
        </div>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
        <line x1={paddingX} y1={height - paddingY} x2={width - paddingX} y2={height - paddingY} stroke="#e8ece9" strokeWidth="1" />
        {points.length === 1 && !predictedPrice && (
          <line x1={paddingX} y1={points[0].y} x2={width - paddingX} y2={points[0].y} stroke="#1f7359" strokeWidth="2" strokeDasharray="4 4" opacity="0.6" />
        )}
        <path d={pathD} fill="none" stroke="#1f7359" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {predictedPrice && (
          <>
            <line x1={lastPt.x} y1={lastPt.y} x2={fx} y2={fy} stroke="#f59e0b" strokeWidth="2" strokeDasharray="4 4" />
            <circle cx={fx} cy={fy} r="5" fill="#f59e0b" stroke="#fff" strokeWidth="2" />
            <text x={fx} y={fy - 8} fontSize="10" fontWeight="700" fill="#d97706" textAnchor="middle">₹{predictedPrice} (Forecast)</text>
          </>
        )}
        {candidateSvg}
        {points.map((p, idx) => (
          <g key={idx}>
            <circle cx={p.x} cy={p.y} r="4.5" fill="#1f7359" stroke="#fff" strokeWidth="2" />
            <text x={p.x} y={p.y - 7} fontSize="10" fontWeight="700" fill="#1f7359" textAnchor="middle">₹{p.price}</text>
            <text x={p.x} y={height - 6} fontSize="9" fill="#888" textAnchor="middle">{p.date}</text>
          </g>
        ))}
      </svg>
    </div>
  )
}

export default function App() {
  const [apiStatus, setApiStatus] = useState('Checking API…')
  const [products, setProducts] = useState([])
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('ALL')
  const [isSeeding, setIsSeeding] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  const [toastMsg, setToastMsg] = useState('')
  const [newObsPrice, setNewObsPrice] = useState('')
  const [comparisonResult, setComparisonResult] = useState(null)
  const [isComparing, setIsComparing] = useState(false)
  const [multiStoreData, setMultiStoreData] = useState(null)
  const [universalQuery, setUniversalQuery] = useState('')
  const [isSearchingUniversal, setIsSearchingUniversal] = useState(false)
  const [universalResult, setUniversalResult] = useState(null)


  const fetchHealth = () => {
    fetch('/api/v1/health')
      .then((res) => {
        if (!res.ok) throw new Error('API unavailable')
        return res.json()
      })
      .then((data) => setApiStatus(`${data.app} is ${data.status}`))
      .catch(() => setApiStatus('API not connected yet'))
  }

  const fetchProducts = () => {
    fetch('/api/v1/products')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch products')
        return res.json()
      })
      .then((data) => setProducts(data))
      .catch((err) => console.error(err))
  }

  useEffect(() => {
    fetchHealth()
    fetchProducts()
  }, [])

  const handleSelectProduct = (id) => {
    setComparisonResult(null)
    setNewObsPrice('')
    setMultiStoreData(null)
    fetch(`/api/v1/products/${id}`)
      .then((res) => res.json())
      .then((data) => setSelectedProduct(data))
      .catch((err) => console.error(err))

    fetch(`/api/v1/products/${id}/multi-store-compare`)
      .then((res) => res.json())
      .then((data) => setMultiStoreData(data))
      .catch((err) => console.error(err))
  }


  const handleSeed = () => {
    setIsSeeding(true)
    fetch('/api/v1/seed', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        setToastMsg(`Seeded ${data.products_created} products, ${data.observations_created} observations`)
        fetchProducts()
        setTimeout(() => setToastMsg(''), 4000)
      })
      .catch(() => {
        setToastMsg('Failed to seed database')
        setTimeout(() => setToastMsg(''), 4000)
      })
      .finally(() => setIsSeeding(false))
  }

  const handleResetDatabase = () => {
    if (!window.confirm('Reset database back to pristine original sample data? This will clear all test checkpoints.')) return
    setIsResetting(true)
    fetch('/api/v1/reset', { method: 'POST' })
      .then((res) => res.json())
      .then(() => {
        setToastMsg('Database reset to clean sample data!')
        setSelectedProduct(null)
        setComparisonResult(null)
        fetchProducts()
        setTimeout(() => setToastMsg(''), 4000)
      })
      .catch(() => {
        setToastMsg('Failed to reset database')
        setTimeout(() => setToastMsg(''), 4000)
      })
      .finally(() => setIsResetting(false))
  }

  const handleCompareDeal = (e) => {
    if (e) e.preventDefault()
    const val = parseFloat(newObsPrice)
    if (!val || val <= 0 || !selectedProduct) {
      setToastMsg('Please enter a valid price greater than 0')
      setTimeout(() => setToastMsg(''), 3000)
      return
    }

    setIsComparing(true)
    fetch(`/api/v1/products/${selectedProduct.id}/compare?price=${val}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to compare price')
        return res.json()
      })
      .then((data) => {
        setComparisonResult(data)
      })
      .catch(() => {
        setToastMsg('Error comparing price')
        setTimeout(() => setToastMsg(''), 3000)
      })
      .finally(() => setIsComparing(false))
  }

  const handleSavePermanentCheckpoint = () => {
    const val = parseFloat(newObsPrice)
    if (!val || !selectedProduct) return
    if (!window.confirm(`Permanently record ₹${val.toFixed(2)} as an official historical checkpoint?`)) return

    fetch(`/api/v1/products/${selectedProduct.id}/observations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ price: val, source_label: 'manual_checkpoint' }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to record price')
        return res.json()
      })
      .then((data) => {
        setSelectedProduct(data)
        setComparisonResult(null)
        setNewObsPrice('')
        setToastMsg(`Recorded permanent checkpoint: ₹${val.toFixed(2)}`)
        fetchProducts()
        setTimeout(() => setToastMsg(''), 4000)
      })
      .catch(() => {
        setToastMsg('Error saving checkpoint')
        setTimeout(() => setToastMsg(''), 3000)
      })
  }

  const handleUniversalSearch = (e) => {

    if (e) e.preventDefault()
    const q = universalQuery.trim()
    if (!q) {
      setToastMsg('Please paste a link or type a product name')
      setTimeout(() => setToastMsg(''), 3000)
      return
    }

    setIsSearchingUniversal(true)
    fetch(`/api/v1/search/universal?query=${encodeURIComponent(q)}`)
      .then((res) => {
        if (!res.ok) throw new Error('Search failed')
        return res.json()
      })
      .then((data) => {
        setUniversalResult(data)
        if (data.db_updated) {
          fetchProducts()
          const act = data.db_action === 'created' ? 'Added new product to' : 'Updated price checkpoint in'
          setToastMsg(`✓ Automatically ${act} catalog (Product ID: ${data.tracked_product_id})`)
          setTimeout(() => setToastMsg(''), 4500)
        }
      })
      .catch(() => {
        setToastMsg('Error searching for product across stores')
        setTimeout(() => setToastMsg(''), 3000)
      })
      .finally(() => setIsSearchingUniversal(false))
  }

  const handleTrackUniversalProduct = () => {
    if (!universalResult) return
    fetch('/api/v1/products/quick-add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: universalResult.extracted_title,
        price: parseFloat(universalResult.lowest_price),
        category: 'General',
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to track')
        return res.json()
      })
      .then((newProd) => {
        setToastMsg(`Added "${universalResult.extracted_title}" to catalog!`)
        fetchProducts()
        setSelectedProduct(newProd)
        setTimeout(() => setToastMsg(''), 4000)
      })
      .catch(() => {
        setToastMsg('Error adding product to catalog')
        setTimeout(() => setToastMsg(''), 3000)
      })
  }

  const categories = ['ALL', ...Array.from(new Set(products.map((p) => p.category).filter(Boolean)))]

  const filteredProducts = products.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = selectedCategory === 'ALL' || p.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  return (
    <main className="page-shell">
      <nav className="topbar">
        <a className="brand" href="#home">
          <span className="brand-mark">E</span> EcomInsights
        </a>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span className="prototype-label">COLLEGE PROJECT · PROTOTYPE</span>
          <button
            onClick={handleResetDatabase}
            disabled={isResetting}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid #c9d5cf',
              background: '#f0f4f2',
              color: '#284639',
              fontWeight: '600',
              fontSize: '12px',
              cursor: 'pointer',
            }}
            title="Wipe test observations and restore pristine sample data"
          >
            {isResetting ? 'Resetting…' : '↺ Reset Clean Data'}
          </button>
          <button className="primary-button" onClick={handleSeed} disabled={isSeeding} style={{ opacity: 1, cursor: 'pointer' }}>
            {isSeeding ? 'Seeding…' : '🔄 Re-seed Data'}
          </button>
        </div>

      </nav>

      {toastMsg && (
        <div style={{ background: '#1f7359', color: 'white', padding: '10px 16px', borderRadius: '8px', margin: '16px 0', fontSize: '13px', fontWeight: '600' }}>
          {toastMsg}
        </div>
      )}

      <section className="hero" id="home">
        <div className="eyebrow">
          <span className="eyebrow-dot" /> PRICE RESEARCH, MADE CLEAR
        </div>
        <h1>
          Make smarter<br />
          <span>price decisions.</span>
        </h1>
        <p className="intro">
          A student-built workspace for understanding product prices and exploring historical observations with reproducible synthetic data.
        </p>
      </section>

      {/* Universal Link-Based & Product Search Card */}
      <section
        style={{
          background: '#ffffff',
          border: '1px solid #cce2d6',
          borderRadius: '15px',
          padding: '24px 28px',
          marginBottom: '28px',
          boxShadow: '0 8px 24px rgba(35, 55, 44, 0.05)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '15px', fontWeight: '800', color: '#1f7359' }}>
              🔗 Link-Based & Universal Search
            </span>
            <span style={{ fontSize: '10px', background: '#d4edd9', color: '#155724', padding: '3px 10px', borderRadius: '12px', fontWeight: '700' }}>
              Paste URL or Keyword
            </span>
          </div>
          <span style={{ fontSize: '12px', color: '#77827d' }}>
            Real-time multi-store price comparison across Amazon, Flipkart, Croma & more
          </span>
        </div>

        <form onSubmit={handleUniversalSearch} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Paste Amazon / Flipkart / Croma product link or type product (e.g. iPhone 15, Sony WH-1000XM4)…"
            value={universalQuery}
            onChange={(e) => setUniversalQuery(e.target.value)}
            style={{
              flex: 1,
              minWidth: '280px',
              padding: '12px 16px',
              borderRadius: '8px',
              border: '1px solid #c9d5cf',
              fontSize: '14px',
              outline: 'none',
            }}
          />
          <button
            type="submit"
            className="primary-button"
            disabled={isSearchingUniversal}
            style={{ opacity: 1, cursor: 'pointer', padding: '12px 22px', fontSize: '14px' }}
          >
            {isSearchingUniversal ? '⏳ Searching Stores…' : '🔍 Compare Across Stores'}
          </button>
        </form>

        {universalResult && (
          <div style={{ marginTop: '20px', background: '#f7fbf9', border: '1px solid #cce2d6', borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: '700', color: '#1f7359', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
                  {universalResult.source_platform} Detected
                </span>
                <h3 style={{ fontSize: '18px', fontWeight: '800', margin: '4px 0 3px', color: '#18231f' }}>
                  {universalResult.extracted_title}
                </h3>
                <span style={{ fontSize: '12px', color: '#77827d' }}>
                  {universalResult.is_url ? 'Extracted from submitted product URL' : 'Searched by product keyword'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    padding: '4px 12px',
                    borderRadius: '14px',
                    background: universalResult.is_live_api ? '#d4edd9' : '#e2e8e5',
                    color: universalResult.is_live_api ? '#155724' : '#314e41',
                  }}
                >
                  {universalResult.is_live_api ? '🟢 Live Google Shopping' : '🔌 Multi-Store Adapter'}
                </span>
                {universalResult.db_updated && (
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      padding: '5px 12px',
                      borderRadius: '14px',
                      background: '#d4edd9',
                      color: '#155724',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      border: '1px solid #b8dfc4',
                    }}
                  >
                    ✓ Saved to Database ({universalResult.db_action})
                  </span>
                )}
                {universalResult.tracked_product_id ? (
                  <button
                    type="button"
                    onClick={() => handleSelectProduct(universalResult.tracked_product_id)}
                    className="primary-button"
                    style={{ opacity: 1, cursor: 'pointer', padding: '6px 14px', fontSize: '12px', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    <span>📈</span> View Price Graph & AI Forecast →
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleTrackUniversalProduct}
                    className="primary-button"
                    style={{ opacity: 1, cursor: 'pointer', padding: '8px 16px', fontSize: '12px' }}
                  >
                    ➕ Track in Catalog
                  </button>
                )}
              </div>
            </div>

            <div
              style={{
                fontSize: '13px',
                color: '#18231f',
                marginBottom: '16px',
                background: '#ffffff',
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid #d5e5db',
                lineHeight: '1.5',
              }}
            >
              💡 <strong>{universalResult.recommendation_summary}</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
              {universalResult.stores.map((s) => (
                <div
                  key={s.store_name}
                  style={{
                    border: s.is_lowest ? '2px solid #1f7359' : '1px solid #e0e6e2',
                    background: s.is_lowest ? '#ffffff' : '#fafcfb',
                    borderRadius: '10px',
                    padding: '14px',
                    position: 'relative',
                    boxShadow: s.is_lowest ? '0 4px 12px rgba(31,115,89,0.08)' : 'none',
                  }}
                >
                  {s.is_lowest && (
                    <span
                      style={{
                        position: 'absolute',
                        top: '-9px',
                        right: '10px',
                        background: '#1f7359',
                        color: '#fff',
                        fontSize: '9px',
                        fontWeight: '800',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        textTransform: 'uppercase',
                      }}
                    >
                      Lowest Price
                    </span>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '14px', fontWeight: '700', color: '#18231f' }}>
                      {s.store_badge_emoji} {s.store_name}
                    </span>
                    <span style={{ fontSize: '12px', color: '#77827d' }}>★ {s.rating}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#1f7359', fontWeight: '600', marginTop: '4px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    📦 {s.matched_product_title || universalResult.extracted_title}
                  </div>
                  <div
                    style={{
                      fontSize: '20px',
                      fontWeight: '800',
                      color: s.is_lowest ? '#1f7359' : '#18231f',
                      margin: '8px 0 4px',
                    }}
                  >
                    ₹{parseFloat(s.price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div style={{ fontSize: '11px', color: '#77827d' }}>{s.delivery_info}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid #f0f3f1' }}>
                    {s.is_lowest ? (
                      <span style={{ fontSize: '12px', color: '#1f7359', fontWeight: '700' }}>✓ Best Deal</span>
                    ) : (
                      <span style={{ fontSize: '12px', color: '#dc3545', fontWeight: '600' }}>
                        +₹{parseFloat(s.difference_from_lowest).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    )}
                    <a
                      href={s.store_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: '12px', color: '#1f7359', fontWeight: '700', textDecoration: 'none' }}
                    >
                      Visit Store →
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="preview-card" aria-label="Project status" style={{ paddingBottom: '24px' }}>
        <div className="card-topline">
          <div>
            <div className="section-kicker">YOUR PRICE RESEARCH HUB</div>
            <h2>Live Product Catalogue</h2>
          </div>
          <span className="sample-badge">
            <span /> SAMPLE MODE
          </span>
        </div>

        {/* Filter Bar */}
        <div style={{ display: 'flex', gap: '16px', margin: '20px 0', flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search products by name…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid #dcdfdc', width: '260px', fontSize: '14px' }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '20px',
                  border: '1px solid #c9d5cf',
                  background: selectedCategory === cat ? '#1f7359' : '#fff',
                  color: selectedCategory === cat ? '#fff' : '#495851',
                  fontWeight: '600',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                {cat === 'ALL' ? 'All' : cat}
              </button>
            ))}
          </div>
        </div>

        {/* Products Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
          {filteredProducts.map((p) => (
            <article
              key={p.id}
              onClick={() => handleSelectProduct(p.id)}
              style={{
                border: '1px solid #e1e7e4',
                borderRadius: '12px',
                padding: '18px',
                background: '#fafbfb',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', color: '#1f7359', textTransform: 'uppercase' }}>
                  {p.category || 'General'}
                </span>
                <span style={{ fontSize: '11px', color: '#88948e' }}>#{p.id}</span>
              </div>
              <h3 style={{ fontSize: '17px', margin: '8px 0 6px', fontWeight: '700' }}>{p.name}</h3>
              <div style={{ fontSize: '22px', fontWeight: '800', color: '#192620' }}>
                {p.currency === 'INR' ? '₹' : p.currency} {p.latest_price || 'N/A'}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #ecefe2', fontSize: '12px', color: '#74827b' }}>
                <span>Last observed: {p.last_observed_at ? new Date(p.last_observed_at).toLocaleDateString() : 'N/A'}</span>
                <span style={{ color: '#1f7359', fontWeight: '700' }}>History →</span>
              </div>
            </article>
          ))}
          {filteredProducts.length === 0 && (
            <p style={{ color: '#77827d', padding: '16px 0' }}>No products found matching your search.</p>
          )}
        </div>

        <div className="card-footer" style={{ marginTop: '24px' }}>
          <span className="status-dot" /> <span>{apiStatus}</span>
          <span className="footer-note">Synthetic sample data loaded from PostgreSQL / SQLite</span>
        </div>
      </section>

      {/* Observation History Modal */}
      {selectedProduct && (
        <div
          onClick={() => setSelectedProduct(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.4)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#fff',
              borderRadius: '16px',
              padding: '24px',
              maxWidth: '560px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: '700', color: '#1f7359', textTransform: 'uppercase' }}>
                  {selectedProduct.category}
                </span>
                <h2 style={{ fontSize: '22px', margin: '4px 0 0' }}>{selectedProduct.name}</h2>
              </div>
              <button
                onClick={() => setSelectedProduct(null)}
                style={{ background: 'none', border: 'none', fontSize: '22px', cursor: 'pointer', color: '#666' }}
              >
                ×
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', background: '#f5f8f6', padding: '12px', borderRadius: '10px', margin: '18px 0', textAlign: 'center' }}>
              <div>
                <div style={{ fontSize: '10px', fontWeight: '700', color: '#7a8781', textTransform: 'uppercase' }}>Current Price</div>
                <div style={{ fontSize: '18px', fontWeight: '800' }}>₹{selectedProduct.latest_price}</div>
              </div>
              <div>
                <div style={{ fontSize: '10px', fontWeight: '700', color: '#7a8781', textTransform: 'uppercase' }}>Observations</div>
                <div style={{ fontSize: '18px', fontWeight: '800' }}>{selectedProduct.observations.length}</div>
              </div>
              <div>
                <div style={{ fontSize: '10px', fontWeight: '700', color: '#7a8781', textTransform: 'uppercase' }}>Currency</div>
                <div style={{ fontSize: '18px', fontWeight: '800' }}>{selectedProduct.currency}</div>
              </div>
            </div>

            {selectedProduct.insight && (
              <div
                style={{
                  background: selectedProduct.insight.recommendation === 'WAIT' ? '#fdfaf2' : '#f0f8f4',
                  border: `1px solid ${selectedProduct.insight.recommendation === 'WAIT' ? '#f7e3af' : '#cce8db'}`,
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '18px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: '700', color: '#1f7359' }}>🤖 AI Price Forecast & Advice</span>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      padding: '4px 10px',
                      borderRadius: '14px',
                      background: selectedProduct.insight.recommendation === 'BUY_NOW' ? '#d4edd9' : (selectedProduct.insight.recommendation === 'WAIT' ? '#fff3cd' : '#e2e3e5'),
                      color: selectedProduct.insight.recommendation === 'BUY_NOW' ? '#155724' : (selectedProduct.insight.recommendation === 'WAIT' ? '#856404' : '#383d41'),
                    }}
                  >
                    {selectedProduct.insight.recommendation === 'BUY_NOW' ? '🟢 Good Time to Buy' : (selectedProduct.insight.recommendation === 'WAIT' ? '🟡 Wait for Price Drop' : '⚪ Price is Steady')}
                  </span>
                </div>
                <p style={{ fontSize: '13px', margin: '0 0 10px', color: '#333', lineHeight: '1.4' }}>
                  {selectedProduct.insight.recommendation_reason}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', paddingTop: '10px', borderTop: '1px dashed rgba(0,0,0,0.1)' }}>
                  <div>
                    <div style={{ fontSize: '10px', color: '#7a8781', fontWeight: '700', textTransform: 'uppercase' }}>Estimated Next Price</div>
                    <div style={{ fontSize: '16px', fontWeight: '800', color: '#192620' }}>₹{selectedProduct.insight.predicted_next_price}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', color: '#7a8781', fontWeight: '700', textTransform: 'uppercase' }}>Recent Momentum</div>
                    <div
                      style={{
                        fontSize: '15px',
                        fontWeight: '700',
                        color: selectedProduct.insight.trend_direction === 'UP' ? '#dc3545' : (selectedProduct.insight.trend_direction === 'DOWN' ? '#28a745' : '#192620'),
                      }}
                    >
                      {selectedProduct.insight.trend_direction} ({selectedProduct.insight.change_percentage > 0 ? '+' : ''}{selectedProduct.insight.change_percentage}%)
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Visual SVG Price Chart */}
            <PriceChart
              observations={selectedProduct.observations}
              predictedPrice={selectedProduct.insight?.predicted_next_price}
              candidatePrice={comparisonResult?.target_price}
            />

            {/* Price Deal Checker & Comparator (Simulation Mode) */}
            <div style={{ background: '#f8faf9', border: '1px solid #dde5e1', borderRadius: '12px', padding: '16px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: '#1f7359' }}>🔍 Check & Compare a Price</span>
                  <div style={{ fontSize: '11px', color: '#687771' }}>Compare any price against historical low & average without altering the real timeline.</div>
                </div>
                <span style={{ fontSize: '10px', background: '#e1eae5', color: '#234e3f', padding: '3px 8px', borderRadius: '10px', fontWeight: '700' }}>
                  Safe Simulator
                </span>
              </div>

              <form onSubmit={handleCompareDeal} style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Enter price to check (₹)"
                  value={newObsPrice}
                  onChange={(e) => setNewObsPrice(e.target.value)}
                  required
                  style={{ padding: '8px 12px', border: '1px solid #d5ddd8', borderRadius: '6px', fontSize: '13px', width: '180px', outline: 'none' }}
                />
                <button type="submit" className="primary-button" disabled={isComparing} style={{ opacity: 1, cursor: 'pointer', padding: '8px 16px', fontSize: '12px' }}>
                  {isComparing ? 'Comparing…' : '🔍 Check & Compare Deal'}
                </button>
                {comparisonResult && (
                  <button
                    type="button"
                    onClick={handleSavePermanentCheckpoint}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #c9d5cf',
                      background: '#fff',
                      color: '#284639',
                      fontWeight: '600',
                      fontSize: '12px',
                      cursor: 'pointer',
                    }}
                    title="Permanently append this price to official history"
                  >
                    💾 Save to History
                  </button>
                )}
              </form>

              {comparisonResult && (
                <div style={{ marginTop: '14px', padding: '14px', borderRadius: '10px', background: '#fff', border: '1px solid #cce0d6' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '700', color: '#1f7359' }}>🎯 Deal Assessment Result</span>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        padding: '4px 10px',
                        borderRadius: '12px',
                        background: comparisonResult.simulated_recommendation === 'BUY_NOW' ? '#d4edd9' : (comparisonResult.simulated_recommendation === 'WAIT' ? '#fff3cd' : '#e2e3e5'),
                        color: comparisonResult.simulated_recommendation === 'BUY_NOW' ? '#155724' : (comparisonResult.simulated_recommendation === 'WAIT' ? '#856404' : '#383d41'),
                      }}
                    >
                      {comparisonResult.verdict_badge}
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: '#192620', fontWeight: '600', margin: '0 0 12px', lineHeight: '1.4' }}>
                    {comparisonResult.deal_summary}
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', textAlign: 'center', background: '#f7faf8', padding: '10px', borderRadius: '8px', border: '1px solid #e1e7e4' }}>
                    <div>
                      <div style={{ fontSize: '10px', color: '#7a8781', fontWeight: '700', textTransform: 'uppercase' }}>Candidate Price</div>
                      <div style={{ fontSize: '14px', fontWeight: '800', color: '#1f7359' }}>₹{parseFloat(comparisonResult.target_price).toFixed(2)}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#7a8781', fontWeight: '700', textTransform: 'uppercase' }}>vs All-Time Low</div>
                      <div style={{ fontSize: '12px', fontWeight: '700', color: comparisonResult.diff_from_lowest <= 0 ? '#1f7359' : '#dc3545' }}>
                        {comparisonResult.diff_from_lowest < 0 ? '-' : '+'}₹{Math.abs(comparisonResult.diff_from_lowest).toFixed(2)} ({comparisonResult.diff_lowest_pct}%)
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#7a8781', fontWeight: '700', textTransform: 'uppercase' }}>vs Historical Avg</div>
                      <div style={{ fontSize: '12px', fontWeight: '700', color: comparisonResult.diff_from_average <= 0 ? '#1f7359' : '#dc3545' }}>
                        {comparisonResult.diff_from_average < 0 ? '-' : '+'}₹{Math.abs(comparisonResult.diff_from_average).toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#7a8781', fontWeight: '700', textTransform: 'uppercase' }}>All-Time High</div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: '#333' }}>₹{parseFloat(comparisonResult.historical_highest).toFixed(2)}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '11px', color: '#667770' }}>
                    <span>🛡️ Simulation only. Product timeline is unchanged.</span>
                    <span style={{ fontWeight: '700', color: '#1f7359' }}>
                      AI Advice: {comparisonResult.simulated_recommendation === 'BUY_NOW' ? '🟢 Good Time to Buy' : (comparisonResult.simulated_recommendation === 'WAIT' ? '🟡 Wait for Drop' : '⚪ Price is Steady')}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Cross-Store Live Price Comparison */}

            {multiStoreData && (
              <div style={{ background: '#fff', border: '1px solid #e1e7e4', borderRadius: '12px', padding: '16px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '700', color: '#1f7359', textTransform: 'uppercase' }}>
                      🏬 Multi-Store Price Comparison
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: '700',
                        padding: '2px 8px',
                        borderRadius: '10px',
                        background: multiStoreData.is_live_api ? '#d4edd9' : '#e2e8e5',
                        color: multiStoreData.is_live_api ? '#155724' : '#314e41',
                      }}
                    >
                      {multiStoreData.is_live_api ? '🟢 Live Google Shopping' : '🔌 Multi-Store Adapter Mode'}
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', fontWeight: '700', background: '#d4edd9', color: '#155724', padding: '3px 10px', borderRadius: '12px' }}>
                    🏆 Best: {multiStoreData.cheapest_store}
                  </span>
                </div>

                <div style={{ fontSize: '12px', color: '#192620', marginBottom: '12px', lineHeight: '1.4', background: '#f4f8f5', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d5e5db' }}>
                  💡 <strong>{multiStoreData.recommendation_summary}</strong>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
                  {multiStoreData.stores.map((s) => (
                    <div
                      key={s.store_code}
                      style={{
                        border: s.is_lowest ? '2px solid #1f7359' : '1px solid #e5eae7',
                        background: s.is_lowest ? '#f7fbf9' : '#fff',
                        borderRadius: '8px',
                        padding: '12px',
                        position: 'relative',
                      }}
                    >
                      {s.is_lowest && (
                        <span
                          style={{
                            position: 'absolute',
                            top: '-8px',
                            right: '8px',
                            background: '#1f7359',
                            color: '#fff',
                            fontSize: '9px',
                            fontWeight: '800',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            textTransform: 'uppercase',
                          }}
                        >
                          Lowest Price
                        </span>
                      )}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', fontWeight: '700', color: '#192620' }}>
                          {s.store_badge_emoji} {s.store_name}
                        </span>
                        <span style={{ fontSize: '11px', color: '#888' }}>★ {s.rating}</span>
                      </div>
                      <div style={{ fontSize: '17px', fontWeight: '800', color: s.is_lowest ? '#1f7359' : '#192620', margin: '6px 0 4px' }}>
                        ₹{parseFloat(s.price).toFixed(2)}
                      </div>
                      <div style={{ fontSize: '11px', color: '#7a8781' }}>{s.delivery_info}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid #f0f3f1' }}>
                        {s.is_lowest ? (
                          <span style={{ fontSize: '11px', color: '#1f7359', fontWeight: '700' }}>✓ Best Deal</span>
                        ) : (
                          <span style={{ fontSize: '11px', color: '#dc3545', fontWeight: '600' }}>
                            +₹{parseFloat(s.difference_from_lowest).toFixed(2)}
                          </span>
                        )}
                        <a
                          href={s.store_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: '11px', color: '#1f7359', fontWeight: '700', textDecoration: 'none' }}
                        >
                          Visit Store →
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <h4 style={{ fontSize: '12px', fontWeight: '700', color: '#73817a', textTransform: 'uppercase', marginBottom: '10px' }}>
              Price Observation History
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {selectedProduct.observations.map((obs) => (
                <div
                  key={obs.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    background: '#fcfdfc',
                    border: '1px solid #edf1ee',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: '600' }}>
                      {new Date(obs.observed_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                    <div style={{ fontSize: '11px', color: '#828e88' }}>Source: {obs.source_label}</div>
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: '800', color: '#1f7359' }}>
                    ₹{obs.price}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <footer>Built for learning · React · FastAPI · PostgreSQL · Python ML</footer>
    </main>
  )
}
