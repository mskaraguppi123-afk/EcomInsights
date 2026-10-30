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

function extractModelIdentifiers(text) {
  if (!text) return { normalized: '', tokens: [], numbers: new Set(), modelCodes: new Set(), families: {}, variants: new Set() }
  const norm = text.toLowerCase().replace(/[\-_/+,|:;*#()\[\]{}'"`~!?@$%^&=<>]/g, ' ').replace(/\s+/g, ' ').trim()
  const tokens = norm.split(' ').filter(Boolean)
  const numbers = new Set(norm.match(/\b\d+\b/g) || [])
  const modelCodes = new Set(norm.match(/\b(?:[a-z]+\d+|\d+[a-z]+[a-z0-9]*)\b/g) || [])

  const families = {}
  const iphoneM = norm.match(/\biphone\s+(\d+|se|x|xs|xr)\b/)
  if (iphoneM) families.iphone = iphoneM[1]
  const galaxySM = norm.match(/\b(?:galaxy\s+)?s\s*(\d+)\b/)
  if (galaxySM) families.galaxy_s = galaxySM[1]
  const ipadM = norm.match(/\bipad\s+(mini|air|pro|\d+)\b/)
  if (ipadM) families.ipad = ipadM[1]
  const sonyWhM = norm.match(/\bwh\s*(\d+[a-z0-9]+)\b/)
  if (sonyWhM) families.sony_wh = sonyWhM[1]

  const variants = new Set()
  ;['pro max', 'pro', 'plus', 'mini', 'ultra', 'fe', 'air'].forEach((v) => {
    if (new RegExp(`\\b${v}\\b`).test(norm)) variants.add(v)
  })

  return { normalized: norm, tokens, numbers, modelCodes, families, variants }
}

function matchProduct(query, candidateName) {
  if (!query || !query.trim()) return { matched: true, score: 50 }
  const q = extractModelIdentifiers(query)
  const c = extractModelIdentifiers(candidateName)

  // 1. Model family conflict: iPhone 16 must not match iPhone 18
  for (const [fam, qVal] of Object.entries(q.families)) {
    if (c.families[fam] && qVal !== c.families[fam]) {
      return { matched: false, score: 0 }
    }
  }

  // 2. Standalone number conflict
  if (q.numbers.size > 0) {
    for (const num of q.numbers) {
      if (!c.numbers.has(num)) {
        return { matched: false, score: 0 }
      }
    }
  }

  // 3. Model code conflict
  if (q.modelCodes.size > 0 && c.modelCodes.size > 0) {
    for (const code of q.modelCodes) {
      if (!c.modelCodes.has(code)) return { matched: false, score: 0 }
    }
  }

  // 4. Variant conflict: if query requested pro but candidate has no pro
  if (q.variants.size > 0) {
    let hasVariant = false
    for (const v of q.variants) {
      if (c.variants.has(v)) hasVariant = true
    }
    if (!hasVariant) return { matched: false, score: 0 }
  }

  const fillers = new Set(['the', 'and', 'with', 'for', 'in', 'by', 'apple'])
  const sigQ = q.tokens.filter((t) => !fillers.has(t))
  const sigC = new Set(c.tokens.filter((t) => !fillers.has(t)))

  if (q.normalized === c.normalized) return { matched: true, score: 100 }
  if (sigQ.length > 0 && sigQ.every((t) => sigC.has(t))) {
    let extraVariants = 0
    c.variants.forEach((v) => { if (!q.variants.has(v)) extraVariants++ })
    return { matched: true, score: extraVariants > 0 ? 70 : 90 }
  }

  const overlap = sigQ.filter((t) => sigC.has(t))
  const ratio = sigQ.length > 0 ? overlap.length / sigQ.length : 0
  if (ratio >= 0.75) return { matched: true, score: Math.round(ratio * 75) }
  return { matched: false, score: 0 }
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

  const filteredProducts = products
    .filter((p) => {
      const match = matchProduct(searchTerm, p.name)
      const matchesCategory = selectedCategory === 'ALL' || p.category === selectedCategory
      return match.matched && matchesCategory
    })
    .sort((a, b) => {
      if (!searchTerm) return 0
      const scoreA = matchProduct(searchTerm, a.name).score
      const scoreB = matchProduct(searchTerm, b.name).score
      return scoreB - scoreA
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
            id="universalSearchInput"
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
                marginBottom: '12px',
                background: '#ffffff',
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid #d5e5db',
                lineHeight: '1.5',
              }}
            >
              💡 <strong>{universalResult.recommendation_summary}</strong>
            </div>

            {universalResult.ai_insight && (
              <div
                style={{
                  marginBottom: '14px',
                  background: 'linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)',
                  border: '1px solid #bbf7d0',
                  borderRadius: '10px',
                  padding: '14px',
                  boxShadow: '0 2px 6px rgba(31,115,89,0.04)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '6px' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#166534', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <span>🤖</span> AI Price Intelligence &amp; ML Forecaster
                  </span>
                  <span style={{ fontSize: '10px', fontWeight: '700', color: '#15803d', background: '#dcfce7', padding: '2px 8px', borderRadius: '12px', border: '1px solid #86efac' }}>
                    Ensemble EMA + OLS Regression
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                  <div style={{ background: '#ffffff', padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', fontWeight: '700', textTransform: 'uppercase' }}>Predicted Next Price</div>
                    <div style={{ fontSize: '18px', fontWeight: '800', color: '#0f172a', margin: '2px 0' }}>
                      ₹{parseFloat(universalResult.ai_insight.predicted_next_price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div
                      style={{
                        fontSize: '10px',
                        color: universalResult.ai_insight.trend_direction === 'DOWN' ? '#16a34a' : (universalResult.ai_insight.trend_direction === 'UP' ? '#d97706' : '#64748b'),
                        fontWeight: '700',
                      }}
                    >
                      {universalResult.ai_insight.trend_direction === 'DOWN' ? '📉 Projected Drop' : (universalResult.ai_insight.trend_direction === 'UP' ? '📈 Projected Rise' : '➡️ Stable Trend')} ({universalResult.ai_insight.change_percentage > 0 ? '+' : ''}{universalResult.ai_insight.change_percentage}%)
                    </div>
                  </div>
                  <div style={{ background: '#ffffff', padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', fontWeight: '700', textTransform: 'uppercase' }}>AI Buying Recommendation</div>
                    <div
                      style={{
                        fontSize: '12px',
                        fontWeight: '800',
                        color: universalResult.ai_insight.recommendation === 'BUY_NOW' ? '#166534' : (universalResult.ai_insight.recommendation === 'WAIT' ? '#9a3412' : '#0369a1'),
                        background: universalResult.ai_insight.recommendation === 'BUY_NOW' ? '#dcfce7' : (universalResult.ai_insight.recommendation === 'WAIT' ? '#ffedd5' : '#e0f2fe'),
                        border: `1px solid ${universalResult.ai_insight.recommendation === 'BUY_NOW' ? '#86efac' : (universalResult.ai_insight.recommendation === 'WAIT' ? '#fed7aa' : '#bae6fd')}`,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        display: 'inline-block',
                        margin: '3px 0',
                      }}
                    >
                      {universalResult.ai_insight.recommendation === 'BUY_NOW' ? '🟢 BUY NOW' : (universalResult.ai_insight.recommendation === 'WAIT' ? '⏳ WAIT FOR DROP' : '⚖️ NEUTRAL')}
                    </div>
                    <div style={{ fontSize: '10px', color: '#475569', marginTop: '3px', lineHeight: '1.3' }}>
                      {universalResult.ai_insight.recommendation_reason}
                    </div>
                  </div>
                  <div style={{ background: '#ffffff', padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', fontWeight: '700', textTransform: 'uppercase' }}>Market Arbitrage &amp; Spread</div>
                    <div style={{ fontSize: '18px', fontWeight: '800', color: '#1f7359', margin: '2px 0' }}>
                      {universalResult.max_savings
                        ? `₹${parseFloat(universalResult.max_savings).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : 'Single Store Quote'}
                    </div>
                    <div style={{ fontSize: '10px', color: '#64748b' }}>
                      {universalResult.savings_percentage > 0
                        ? `${universalResult.savings_percentage}% instant cross-store savings`
                        : 'Compared across verified retailers'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '14px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  background: universalResult.amazon_found ? '#e8f5e9' : '#fff3e0',
                  color: universalResult.amazon_found ? '#1b5e20' : '#b78103',
                  border: `1px solid ${universalResult.amazon_found ? '#c8e6c9' : '#ffe0b2'}`,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                🛒 Amazon India: {universalResult.amazon_found
                  ? '✓ Verified Listing'
                  : (() => {
                      const note = universalResult.retailer_status_notes?.find(n => n.toLowerCase().includes('amazon'));
                      if (note && note.includes(':')) return `✕ ${note.split(':')[1].trim()}`;
                      return '✕ Not found in search results';
                    })()}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  background: universalResult.flipkart_found ? '#e8f5e9' : '#fff3e0',
                  color: universalResult.flipkart_found ? '#1b5e20' : '#b78103',
                  border: `1px solid ${universalResult.flipkart_found ? '#c8e6c9' : '#ffe0b2'}`,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                🛍️ Flipkart: {universalResult.flipkart_found
                  ? '✓ Verified Listing'
                  : (() => {
                      const note = universalResult.retailer_status_notes?.find(n => n.toLowerCase().includes('flipkart'));
                      if (note && note.includes(':')) return `✕ ${note.split(':')[1].trim()}`;
                      return '✕ Not found in search results';
                    })()}
              </span>
              {universalResult.comparable_spec && (
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    background: '#e3f2fd',
                    color: '#0d47a1',
                    border: '1px solid #bbdefb',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  🎯 Specification Tier: {universalResult.comparable_spec}
                </span>
              )}
              {universalResult.comparable_condition && (
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    background: universalResult.comparable_condition.toLowerCase().includes('refurb') ? '#fff3e0' : '#f3e5f5',
                    color: universalResult.comparable_condition.toLowerCase().includes('refurb') ? '#e65100' : '#6a1b9a',
                    border: `1px solid ${universalResult.comparable_condition.toLowerCase().includes('refurb') ? '#ffe0b2' : '#e1bee7'}`,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  🏷️ Condition: {universalResult.comparable_condition}
                </span>
              )}
            </div>

            {universalResult.direct_retailer_links && Object.keys(universalResult.direct_retailer_links).length > 0 && (
              <div
                style={{
                  marginBottom: '14px',
                  padding: '10px 14px',
                  background: '#f9fbf9',
                  border: '1px solid #d5e5db',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: '#34453c',
                }}
              >
                <div style={{ fontWeight: '700', marginBottom: '6px' }}>
                  ℹ️ Store Discovery &amp; Direct Retailer Links:
                </div>
                <div style={{ fontSize: '11px', color: '#66776e', marginBottom: '8px' }}>
                  Live Google Shopping discovery may omit direct merchant listings. You can check live availability directly:
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {universalResult.direct_retailer_links.amazon && (
                    <a
                      href={universalResult.direct_retailer_links.amazon}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px',
                        fontWeight: '700',
                        color: '#1f7359',
                        textDecoration: 'none',
                        background: '#ffffff',
                        border: '1px solid #1f7359',
                        padding: '4px 10px',
                        borderRadius: '6px',
                      }}
                    >
                      🛒 Amazon.in ↗
                    </a>
                  )}
                  {universalResult.direct_retailer_links.flipkart && (
                    <a
                      href={universalResult.direct_retailer_links.flipkart}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px',
                        fontWeight: '700',
                        color: '#1f7359',
                        textDecoration: 'none',
                        background: '#ffffff',
                        border: '1px solid #1f7359',
                        padding: '4px 10px',
                        borderRadius: '6px',
                      }}
                    >
                      🛍️ Flipkart ↗
                    </a>
                  )}
                  {universalResult.direct_retailer_links.croma && (
                    <a
                      href={universalResult.direct_retailer_links.croma}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px',
                        fontWeight: '700',
                        color: '#1f7359',
                        textDecoration: 'none',
                        background: '#ffffff',
                        border: '1px solid #1f7359',
                        padding: '4px 10px',
                        borderRadius: '6px',
                      }}
                    >
                      🏬 Croma ↗
                    </a>
                  )}
                  {universalResult.direct_retailer_links.reliance && (
                    <a
                      href={universalResult.direct_retailer_links.reliance}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px',
                        fontWeight: '700',
                        color: '#1f7359',
                        textDecoration: 'none',
                        background: '#ffffff',
                        border: '1px solid #1f7359',
                        padding: '4px 10px',
                        borderRadius: '6px',
                      }}
                    >
                      📱 Reliance Digital ↗
                    </a>
                  )}
                  {universalResult.direct_retailer_links.vijaysales && (
                    <a
                      href={universalResult.direct_retailer_links.vijaysales}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px',
                        fontWeight: '700',
                        color: '#1f7359',
                        textDecoration: 'none',
                        background: '#ffffff',
                        border: '1px solid #1f7359',
                        padding: '4px 10px',
                        borderRadius: '6px',
                      }}
                    >
                      📺 Vijay Sales ↗
                    </a>
                  )}
                  {universalResult.direct_retailer_links.tatacliq && (
                    <a
                      href={universalResult.direct_retailer_links.tatacliq}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11px',
                        fontWeight: '700',
                        color: '#1f7359',
                        textDecoration: 'none',
                        background: '#ffffff',
                        border: '1px solid #1f7359',
                        padding: '4px 10px',
                        borderRadius: '6px',
                      }}
                    >
                      🏷️ Tata CLiQ ↗
                    </a>
                  )}
                </div>
              </div>
            )}

            {(universalResult.resolution_error || universalResult.extracted_title === 'Unresolved Product Link') ? (
              <div style={{ textAlign: 'center', padding: '28px 16px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '10px' }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔗⚠️</div>
                <div style={{ fontSize: '16px', fontWeight: '800', color: '#9a3412' }}>
                  Unable to Resolve Shortened Product Link
                </div>
                <p style={{ fontSize: '13px', color: '#7c2d12', margin: '8px 0 16px', maxWidth: '620px', marginLeft: 'auto', marginRight: 'auto', lineHeight: '1.5' }}>
                  {universalResult.recommendation_summary || 'The shortened retailer link could not be resolved or did not provide a verifiable product name. Please search by product name instead.'}
                </p>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setUniversalQuery('');
                      const el = document.getElementById('universalSearchInput');
                      if (el) el.focus();
                    }}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '12px',
                      fontWeight: '700',
                      color: '#ffffff',
                      background: '#1f7359',
                      border: 'none',
                      padding: '8px 18px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                    }}
                  >
                    🔍 Search by Product Name (e.g. iPhone 15)
                  </button>
                </div>
              </div>
            ) : (!universalResult.has_reliable_match || universalResult.lowest_price === null || universalResult.stores.length === 0) ? (
              <div style={{ textAlign: 'center', padding: '24px 16px', background: '#fff', border: '1px dashed #d5ddd8', borderRadius: '10px' }}>
                <div style={{ fontSize: '28px', marginBottom: '8px' }}>🔎</div>
                <div style={{ fontSize: '15px', fontWeight: '800', color: '#18231f' }}>
                  {universalResult.cheapest_store.includes('trusted') || universalResult.cheapest_store.includes('comparable') || universalResult.cheapest_store.includes('found')
                    ? 'No Trusted Comparable Listings Found'
                    : 'Price Unavailable / No Reliable Match'}
                </div>
                <p style={{ fontSize: '13px', color: '#6e7d75', margin: '6px 0 14px' }}>
                  {universalResult.recommendation_summary || `No verified price data found for '${universalResult.extracted_title}' in trusted data sources.`}
                </p>
                {universalResult.direct_retailer_links && (
                  <div style={{ display: 'inline-flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                    {universalResult.direct_retailer_links.amazon && (
                      <a
                        href={universalResult.direct_retailer_links.amazon}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: '700', color: '#ffffff', background: '#1f7359', textDecoration: 'none', padding: '6px 12px', borderRadius: '6px' }}
                      >
                        🛒 Check Amazon.in ↗
                      </a>
                    )}
                    {universalResult.direct_retailer_links.flipkart && (
                      <a
                        href={universalResult.direct_retailer_links.flipkart}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: '700', color: '#ffffff', background: '#1f7359', textDecoration: 'none', padding: '6px 12px', borderRadius: '6px' }}
                      >
                        🛍️ Check Flipkart ↗
                      </a>
                    )}
                    {universalResult.direct_retailer_links.croma && (
                      <a
                        href={universalResult.direct_retailer_links.croma}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: '700', color: '#ffffff', background: '#1f7359', textDecoration: 'none', padding: '6px 12px', borderRadius: '6px' }}
                      >
                        🏬 Check Croma ↗
                      </a>
                    )}
                    {universalResult.direct_retailer_links.reliance && (
                      <a
                        href={universalResult.direct_retailer_links.reliance}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: '700', color: '#ffffff', background: '#1f7359', textDecoration: 'none', padding: '6px 12px', borderRadius: '6px' }}
                      >
                        📱 Check Reliance ↗
                      </a>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
                {universalResult.stores.map((s) => (
                  <div
                    key={`${s.store_name}-${s.price || 'na'}`}
                    style={{
                      border: s.is_lowest && universalResult.is_comparable_comparison && universalResult.max_savings !== null ? '2px solid #1f7359' : (s.price_status === 'excluded' ? '1px dashed #e57373' : '1px solid #e0e6e2'),
                      background: s.is_lowest && universalResult.is_comparable_comparison && universalResult.max_savings !== null ? '#ffffff' : (s.price_status === 'excluded' ? '#fffaf9' : '#fafcfb'),
                      borderRadius: '10px',
                      padding: '14px',
                      position: 'relative',
                      boxShadow: s.is_lowest && universalResult.is_comparable_comparison && universalResult.max_savings !== null ? '0 4px 12px rgba(31,115,89,0.08)' : 'none',
                    }}
                  >
                    {s.is_lowest && universalResult.is_comparable_comparison && universalResult.max_savings !== null && (
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
                      {s.store_url ? (
                        <a
                          href={s.store_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: '14px', fontWeight: '700', color: '#18231f', textDecoration: 'none' }}
                          title="Opens in a new tab"
                        >
                          {s.store_badge_emoji} {s.store_name} <span style={{ fontSize: '11px', color: '#1f7359' }}>↗</span>
                        </a>
                      ) : (
                        <span style={{ fontSize: '14px', fontWeight: '700', color: '#18231f' }}>
                          {s.store_badge_emoji} {s.store_name}
                        </span>
                      )}
                      <span style={{ fontSize: '12px', color: '#77827d' }}>★ {s.rating}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                      {s.condition && (
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: '700',
                            background: s.condition.toLowerCase().includes('refurb') ? '#fff3e0' : '#f3e5f5',
                            color: s.condition.toLowerCase().includes('refurb') ? '#b78103' : '#6a1b9a',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            border: `1px solid ${s.condition.toLowerCase().includes('refurb') ? '#ffe0b2' : '#e1bee7'}`,
                          }}
                        >
                          {s.condition}
                        </span>
                      )}
                      {s.variant_spec && (
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: '700',
                            background: s.is_comparable ? '#e8f5e9' : '#fff3e0',
                            color: s.is_comparable ? '#1b5e20' : '#b78103',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            border: `1px solid ${s.is_comparable ? '#c8e6c9' : '#ffe0b2'}`,
                          }}
                        >
                          {s.variant_spec}
                        </span>
                      )}
                      {!s.is_comparable && s.price_status === 'verified' && (
                        <span style={{ fontSize: '10px', color: '#b78103', fontWeight: '600' }}>
                          (Different variant/condition)
                        </span>
                      )}
                      {s.price_status === 'excluded' && (
                        <span style={{ fontSize: '10px', color: '#c0392b', fontWeight: '700' }}>
                          ⚠️ Excluded Outlier
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '11px', color: '#1f7359', fontWeight: '600', marginTop: '4px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {s.store_url ? (
                        <a
                          href={s.store_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: 'inherit', textDecoration: 'none' }}
                          title={s.matched_product_title || universalResult.extracted_title}
                        >
                          📦 {s.matched_product_title || universalResult.extracted_title}
                        </a>
                      ) : (
                        <span title={s.matched_product_title || universalResult.extracted_title}>
                          📦 {s.matched_product_title || universalResult.extracted_title}
                        </span>
                      )}
                    </div>
                    <div
                      style={{
                        fontSize: '20px',
                        fontWeight: '800',
                        color: s.price_status === 'excluded' ? '#c0392b' : (s.is_lowest && universalResult.is_comparable_comparison && universalResult.max_savings !== null ? '#1f7359' : '#18231f'),
                        margin: '8px 0 4px',
                      }}
                    >
                      {s.price_status === 'excluded'
                        ? 'Price not verified'
                        : (s.price !== null && s.price !== undefined
                          ? `${s.currency === 'USD' ? '$' : '₹'}${parseFloat(s.price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                          : 'Price unavailable')}
                    </div>
                    <div style={{ fontSize: '11px', color: s.in_stock ? '#77827d' : '#c0392b', fontWeight: s.in_stock ? 'normal' : '600' }}>
                      {s.in_stock ? s.delivery_info : `⚠️ ${s.delivery_info}`}
                    </div>
                    {s.fetched_at && (
                      <div style={{ fontSize: '10px', color: '#88958f', marginTop: '2px' }}>
                        Checked: {new Date(s.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid #f0f3f1' }}>
                      {s.is_lowest && universalResult.is_comparable_comparison && universalResult.max_savings !== null ? (
                        <span style={{ fontSize: '12px', color: '#1f7359', fontWeight: '700' }}>✓ Best Deal</span>
                      ) : s.price_status === 'excluded' ? (
                        <span style={{ fontSize: '11px', color: '#c0392b', fontWeight: '600' }}>Excluded outlier</span>
                      ) : s.difference_from_lowest !== null && s.difference_from_lowest !== undefined ? (
                        <span style={{ fontSize: '12px', color: '#dc3545', fontWeight: '600' }}>
                          {`+₹${parseFloat(s.difference_from_lowest).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#1f7359', fontWeight: '600' }}>Verified listing</span>
                      )}
                      {s.store_url ? (
                        <a
                          href={s.store_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '6px 14px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: '700',
                            textDecoration: 'none',
                            cursor: 'pointer',
                            background: s.is_direct_url ? '#1f7359' : '#ffffff',
                            color: s.is_direct_url ? '#ffffff' : '#1f7359',
                            border: '1px solid #1f7359',
                          }}
                          title="Opens in a new tab"
                        >
                          {s.is_direct_url ? 'Visit Store ↗' : `Search on ${s.store_name} ↗`}
                        </a>
                      ) : (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            padding: '6px 14px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: '600',
                            background: '#e2e8e5',
                            color: '#77827d',
                            cursor: 'not-allowed',
                          }}
                          title="Store link unavailable"
                        >
                          Store link unavailable
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
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
            id="universalSearchInput"
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
                {p.latest_price ? `${p.currency === 'INR' ? '₹' : (p.currency || '')} ${parseFloat(p.latest_price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Price unavailable'}
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
                <div style={{ fontSize: '18px', fontWeight: '800' }}>
                  {selectedProduct.latest_price ? `₹${parseFloat(selectedProduct.latest_price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Price unavailable'}
                </div>
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
                        {s.store_url ? (
                          <a
                            href={s.store_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ fontSize: '13px', fontWeight: '700', color: '#192620', textDecoration: 'none' }}
                            title="Opens in a new tab"
                          >
                            {s.store_badge_emoji} {s.store_name} <span style={{ fontSize: '10px', color: '#1f7359' }}>↗</span>
                          </a>
                        ) : (
                          <span style={{ fontSize: '13px', fontWeight: '700', color: '#192620' }}>
                            {s.store_badge_emoji} {s.store_name}
                          </span>
                        )}
                        <span style={{ fontSize: '11px', color: '#888' }}>★ {s.rating}</span>
                      </div>
                      <div style={{ fontSize: '17px', fontWeight: '800', color: s.is_lowest ? '#1f7359' : '#192620', margin: '6px 0 4px' }}>
                        {s.price !== null && s.price !== undefined ? `₹${parseFloat(s.price).toFixed(2)}` : 'Price unavailable'}
                      </div>
                      <div style={{ fontSize: '11px', color: s.in_stock ? '#7a8781' : '#c0392b', fontWeight: s.in_stock ? 'normal' : '600' }}>
                        {s.in_stock ? s.delivery_info : `⚠️ ${s.delivery_info}`}
                      </div>
                      {s.fetched_at && (
                        <div style={{ fontSize: '10px', color: '#88958f', marginTop: '2px' }}>
                          Checked: {new Date(s.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      )}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid #f0f3f1' }}>
                        {s.is_lowest ? (
                          <span style={{ fontSize: '11px', color: '#1f7359', fontWeight: '700' }}>✓ Best Deal</span>
                        ) : (
                          <span style={{ fontSize: '11px', color: '#dc3545', fontWeight: '600' }}>
                            +₹{parseFloat(s.difference_from_lowest).toFixed(2)}
                          </span>
                        )}
                        {s.store_url ? (
                          <a
                            href={s.store_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 14px',
                              borderRadius: '6px',
                              fontSize: '11px',
                              fontWeight: '700',
                              textDecoration: 'none',
                              cursor: 'pointer',
                              background: s.is_direct_url ? '#1f7359' : '#ffffff',
                              color: s.is_direct_url ? '#ffffff' : '#1f7359',
                              border: '1px solid #1f7359',
                            }}
                            title="Opens in a new tab"
                          >
                            {s.is_direct_url ? 'Visit Store ↗' : `Search on ${s.store_name} ↗`}
                          </a>
                        ) : (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '6px 14px',
                              borderRadius: '6px',
                              fontSize: '11px',
                              fontWeight: '600',
                              background: '#e2e8e5',
                              color: '#77827d',
                              cursor: 'not-allowed',
                            }}
                            title="Store link unavailable"
                          >
                            Store link unavailable
                          </span>
                        )}
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
