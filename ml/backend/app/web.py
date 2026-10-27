"""Web UI dashboard served directly by FastAPI for zero-dependency local demonstrations."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

web_router = APIRouter()

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EcomInsights - Price Intelligence Dashboard</title>
  <style>
    :root {
      --primary: #1f7359;
      --primary-dark: #165642;
      --primary-light: #e8f5f0;
      --bg: #f5f7fb;
      --surface: #ffffff;
      --text: #192620;
      --text-muted: #6e7d75;
      --border: #e2e8e4;
      --accent: #2e8b57;
      --danger: #dc3545;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 0 24px 60px;
    }
    .container { max-width: 1140px; margin: 0 auto; }
    
    /* Topbar */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px 0;
      border-bottom: 1px solid var(--border);
      margin-bottom: 32px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 20px;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
    }
    .brand-mark {
      width: 36px;
      height: 36px;
      background: var(--primary);
      color: white;
      border-radius: 10px;
      display: grid;
      place-items: center;
      font-weight: 800;
      font-size: 18px;
    }
    .badges {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .badge {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
      padding: 5px 10px;
      border-radius: 20px;
      text-transform: uppercase;
    }
    .badge-viva { background: #e6edf8; color: #1c529e; }
    .badge-sample { background: var(--primary-light); color: var(--primary); }
    .api-status {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--text-muted);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #28a745;
    }

    /* Hero */
    .hero {
      margin-bottom: 32px;
    }
    .hero h1 {
      font-size: 36px;
      font-weight: 800;
      line-height: 1.2;
      margin-bottom: 8px;
    }
    .hero h1 span { color: var(--primary); }
    .hero p {
      color: var(--text-muted);
      font-size: 16px;
      max-width: 650px;
    }

    /* Action bar */
    .action-bar {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      margin-bottom: 24px;
      background: var(--surface);
      padding: 16px 20px;
      border-radius: 12px;
      border: 1px solid var(--border);
    }
    .search-group {
      display: flex;
      gap: 12px;
      align-items: center;
    }
    .search-input {
      padding: 10px 16px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
      width: 280px;
      outline: none;
      transition: border 0.2s;
    }
    .search-input:focus { border-color: var(--primary); }
    .category-pills {
      display: flex;
      gap: 8px;
    }
    .pill {
      border: 1px solid var(--border);
      background: var(--surface);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      cursor: pointer;
      font-weight: 600;
      color: var(--text-muted);
      transition: all 0.2s;
    }
    .pill.active {
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }
    .btn {
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .btn-primary {
      background: var(--primary);
      color: white;
    }
    .btn-primary:hover { background: var(--primary-dark); }
    .btn-secondary {
      background: #f0f3f1;
      color: var(--text);
    }

    /* Product Grid */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
      margin-bottom: 36px;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 22px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.03);
      transition: transform 0.2s, box-shadow 0.2s;
      cursor: pointer;
      position: relative;
    }
    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(31, 115, 89, 0.08);
      border-color: var(--primary);
    }
    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .card-category {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--primary);
      background: var(--primary-light);
      padding: 4px 8px;
      border-radius: 6px;
    }
    .card-title {
      font-size: 18px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 8px;
    }
    .price-tag {
      font-size: 26px;
      font-weight: 800;
      color: var(--text);
      display: flex;
      align-items: baseline;
      gap: 4px;
      margin-bottom: 12px;
    }
    .price-currency {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-muted);
    }
    .card-meta {
      font-size: 12px;
      color: var(--text-muted);
      border-top: 1px solid #f0f3f1;
      padding-top: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .view-link {
      color: var(--primary);
      font-weight: 700;
      font-size: 12px;
    }

    /* Modal */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(18, 28, 24, 0.45);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
    }
    .modal-backdrop.active { display: flex; }
    .modal {
      background: var(--surface);
      border-radius: 16px;
      width: 100%;
      max-width: 620px;
      padding: 28px;
      box-shadow: 0 20px 48px rgba(0,0,0,0.15);
      max-height: 90vh;
      overflow-y: auto;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
    }
    .modal-close {
      background: none;
      border: none;
      font-size: 22px;
      cursor: pointer;
      color: var(--text-muted);
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      background: #f8faf9;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 24px;
      text-align: center;
    }
    .stat-label { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }
    .stat-val { font-size: 18px; font-weight: 800; color: var(--text); margin-top: 4px; }
    
    .timeline {
      margin-top: 16px;
      position: relative;
      padding-left: 24px;
    }
    .timeline::before {
      content: '';
      position: absolute;
      left: 7px;
      top: 6px;
      bottom: 6px;
      width: 2px;
      background: #dde4e0;
    }
    .timeline-item {
      position: relative;
      margin-bottom: 18px;
    }
    .timeline-dot {
      position: absolute;
      left: -24px;
      top: 5px;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: white;
      border: 3px solid var(--primary);
    }
    .timeline-content {
      background: #fbfcfc;
      border: 1px solid #eef2f0;
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .timeline-date { font-size: 12px; color: var(--text-muted); }
    .timeline-price { font-size: 16px; font-weight: 700; color: var(--text); }
    .trend-up { color: var(--danger); font-size: 12px; font-weight: 600; }
    .trend-down { color: var(--accent); font-size: 12px; font-weight: 600; }

    .insight-card {
      background: #f0f8f4;
      border: 1px solid #cce8db;
      border-radius: 12px;
      padding: 16px 18px;
      margin-bottom: 22px;
    }
    .insight-card.wait {
      background: #fdfaf2;
      border-color: #f7e3af;
    }
    .insight-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .insight-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 14px;
      letter-spacing: 0.5px;
    }
    .insight-badge.buy { background: #d4edd9; color: #155724; }
    .insight-badge.wait { background: #fff3cd; color: #856404; }
    .insight-badge.neutral { background: #e2e3e5; color: #383d41; }
    .insight-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed rgba(0,0,0,0.1);
    }
    .insight-label { font-size: 11px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; }
    .insight-value { font-size: 15px; font-weight: 700; color: var(--text); }

    footer {
      text-align: center;
      color: var(--text-muted);
      font-size: 12px;
      margin-top: 48px;
      padding-top: 24px;
      border-top: 1px solid var(--border);
    }
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e3a2f;
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 8px 24px rgba(0,0,0,0.15);
      display: none;
      z-index: 2000;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <a href="/" class="brand">
        <span class="brand-mark">E</span>
        <span>EcomInsights</span>
      </a>
      <div class="badges">
        <span class="badge badge-viva">Major Project · Prototype</span>
        <span class="badge badge-sample">Synthetic Data Only</span>
        <div class="api-status">
          <span class="status-dot"></span>
          <span id="apiStatusText">Connected to FastAPI</span>
        </div>
      </div>
    </header>

    <section class="hero">
      <h1>Track & Analyze <span>Product Price Trends</span></h1>
      <p>A college engineering workspace demonstrating relational price tracking, REST APIs, and historical observations using synthetic benchmark data.</p>
    </section>

    <!-- Link & Product Universal Search Card -->
    <div style="background:#ffffff; border:1px solid #cce2d6; border-radius:12px; padding:18px 20px; margin-bottom:24px; box-shadow:0 4px 16px rgba(0,0,0,0.04);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:14px; font-weight:800; color:var(--primary);">🔗 Link-Based & Universal Search</span>
          <span style="font-size:10px; background:#d4edd9; color:#155724; padding:2px 8px; border-radius:10px; font-weight:700;">Amazon / Flipkart Link or Keyword</span>
        </div>
        <span style="font-size:11px; color:var(--text-muted);">Real-time cross-store arbitrage finder</span>
      </div>
      <div style="display:flex; gap:10px;">
        <input type="text" id="universalSearchInput" placeholder="Paste Amazon/Flipkart product link or type product (e.g. iPhone 15, Sony WH-1000XM4)..." style="flex:1; padding:12px 16px; border:1px solid #d5ddd8; border-radius:8px; font-size:14px; outline:none;" />
        <button type="button" id="btnUniversalSearch" class="btn btn-primary" style="padding:12px 22px; font-size:13px; font-weight:700;">
          <span>🔍</span> Compare Across Stores
        </button>
      </div>

      <!-- Universal Search Result Container -->
      <div id="universalResultContainer" style="display:none; margin-top:16px;"></div>
    </div>

    <div class="action-bar">

      <div class="search-group">
        <input type="text" id="searchInput" class="search-input" placeholder="Search products by name...">
        <div class="category-pills" id="categoryPills">
          <button class="pill active" data-cat="ALL">All Categories</button>
        </div>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="btn btn-secondary" id="btnReset" title="Wipe test observations and restore pristine sample data">
          <span>↺</span> Reset Clean Data
        </button>
        <button class="btn btn-primary" id="btnSeed">
          <span>🔄</span> Re-seed Sample Data
        </button>
      </div>
    </div>


    <div class="grid" id="productGrid">
      <p style="color: var(--text-muted); padding: 20px;">Loading product catalogue...</p>
    </div>

    <footer>
      <strong>EcomInsights Prototype</strong> · Built with FastAPI, SQLAlchemy, PostgreSQL/SQLite & React · Safe Synthetic Data (No Scraping)
    </footer>
  </div>

  <!-- Detail Modal -->
  <div class="modal-backdrop" id="modalBackdrop">
    <div class="modal">
      <div class="modal-header">
        <div>
          <span class="card-category" id="modalCategory">Category</span>
          <h2 class="card-title" id="modalTitle" style="font-size: 22px; margin-top: 8px;">Product Name</h2>
        </div>
        <button class="modal-close" id="modalClose">&times;</button>
      </div>

      <div class="stats-row">
        <div>
          <div class="stat-label">Current Price</div>
          <div class="stat-val" id="statCurrent">₹0</div>
        </div>
        <div>
          <div class="stat-label">Lowest Observed</div>
          <div class="stat-val" id="statLowest">₹0</div>
        </div>
        <div>
          <div class="stat-label">Highest Observed</div>
          <div class="stat-val" id="statHighest">₹0</div>
        </div>
      </div>

      <div id="insightSection"></div>

      <div id="chartSection"></div>

      <!-- Price Deal Checker & Comparator (Simulation Mode) -->
      <div style="background:#f8faf9; border:1px solid #dde5e1; border-radius:12px; padding:16px; margin-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div>
            <span style="font-size:13px; font-weight:700; color:var(--primary);">🔍 Check & Compare a Price</span>
            <div style="font-size:11px; color:var(--text-muted);">Compare any price against historical low & average without altering the real timeline.</div>
          </div>
          <span style="font-size:10px; background:#e1eae5; color:#234e3f; padding:3px 8px; border-radius:10px; font-weight:700;">Safe Simulator</span>
        </div>
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <input type="number" step="0.01" id="newPriceInput" placeholder="Enter price to check (₹)" style="padding:8px 12px; border:1px solid #d5ddd8; border-radius:6px; font-size:13px; width:180px; outline:none;" />
          <button type="button" id="btnCompareDeal" class="btn btn-primary" style="padding:8px 16px; font-size:12px;">
            <span>🔍</span> Check & Compare Deal
          </button>
          <button type="button" id="btnSaveCheckpoint" class="btn btn-secondary" style="padding:8px 12px; font-size:12px; display:none;" title="Save this price to permanent history">
            <span>💾</span> Save to History
          </button>
        </div>
        
        <!-- Live Deal Comparison Box -->
        <div id="compareResultBox" style="display:none; margin-top:14px; padding:14px; border-radius:10px; background:#ffffff; border:1px solid #cce0d6;"></div>
      </div>

      <!-- Cross-Store Live Price Comparison -->
      <div id="multiStoreSection"></div>

      <h3 style="font-size: 14px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 12px;">Historical Price Timeline</h3>
      <div class="timeline" id="timelineList"></div>

    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    function extractModelIdentifiers(text) {
      if (!text) return { normalized: '', tokens: [], numbers: new Set(), modelCodes: new Set(), families: {}, variants: new Set() };
      const norm = text.toLowerCase().replace(/[\-_/+,|:;*#()\[\]{}'"`~!?@$%^&=<>]/g, ' ').replace(/\s+/g, ' ').trim();
      const tokens = norm.split(' ').filter(Boolean);
      const numbers = new Set(norm.match(/\b\d+\b/g) || []);
      const modelCodes = new Set(norm.match(/\b(?:[a-z]+\d+|\d+[a-z]+[a-z0-9]*)\b/g) || []);

      const families = {};
      const iphoneM = norm.match(/\biphone\s+(\d+|se|x|xs|xr)\b/);
      if (iphoneM) families.iphone = iphoneM[1];
      const galaxySM = norm.match(/\b(?:galaxy\s+)?s\s*(\d+)\b/);
      if (galaxySM) families.galaxy_s = galaxySM[1];
      const ipadM = norm.match(/\bipad\s+(mini|air|pro|\d+)\b/);
      if (ipadM) families.ipad = ipadM[1];
      const sonyWhM = norm.match(/\bwh\s*(\d+[a-z0-9]+)\b/);
      if (sonyWhM) families.sony_wh = sonyWhM[1];

      const variants = new Set();
      ['pro max', 'pro', 'plus', 'mini', 'ultra', 'fe', 'air'].forEach(v => {
        if (new RegExp(`\\b${v}\\b`).test(norm)) variants.add(v);
      });

      return { normalized: norm, tokens, numbers, modelCodes, families, variants };
    }

    function matchProduct(query, candidateName) {
      if (!query || !query.trim()) return { matched: true, score: 50 };
      const q = extractModelIdentifiers(query);
      const c = extractModelIdentifiers(candidateName);

      // 1. Model family conflict: e.g. iPhone 16 must not match iPhone 18
      for (const [fam, qVal] of Object.entries(q.families)) {
        if (c.families[fam] && qVal !== c.families[fam]) {
          return { matched: false, score: 0 };
        }
      }

      // 2. Standalone number conflict
      if (q.numbers.size > 0) {
        for (const num of q.numbers) {
          if (!c.numbers.has(num)) {
            return { matched: false, score: 0 };
          }
        }
      }

      // 3. Model code conflict
      if (q.modelCodes.size > 0 && c.modelCodes.size > 0) {
        for (const code of q.modelCodes) {
          if (!c.modelCodes.has(code)) return { matched: false, score: 0 };
        }
      }

      // 4. Variant conflict: if query requested pro but candidate has no pro
      if (q.variants.size > 0) {
        let hasVariant = false;
        for (const v of q.variants) {
          if (c.variants.has(v)) hasVariant = true;
        }
        if (!hasVariant) return { matched: false, score: 0 };
      }

      const fillers = new Set(['the', 'and', 'with', 'for', 'in', 'by', 'apple']);
      const sigQ = q.tokens.filter(t => !fillers.has(t));
      const sigC = new Set(c.tokens.filter(t => !fillers.has(t)));

      if (q.normalized === c.normalized) return { matched: true, score: 100 };
      if (sigQ.length > 0 && sigQ.every(t => sigC.has(t))) {
        let extraVariants = 0;
        c.variants.forEach(v => { if (!q.variants.has(v)) extraVariants++; });
        return { matched: true, score: extraVariants > 0 ? 70 : 90 };
      }

      const overlap = sigQ.filter(t => sigC.has(t));
      const ratio = sigQ.length > 0 ? overlap.length / sigQ.length : 0;
      if (ratio >= 0.75) return { matched: true, score: Math.round(ratio * 75) };
      return { matched: false, score: 0 };
    }

    let allProducts = [];
    let currentCategory = 'ALL';

    const grid = document.getElementById('productGrid');
    const searchInput = document.getElementById('searchInput');
    const pillsContainer = document.getElementById('categoryPills');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const modalClose = document.getElementById('modalClose');
    const toast = document.getElementById('toast');
    const btnSeed = document.getElementById('btnSeed');

    function showToast(msg) {
      toast.innerText = msg;
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }

    async function loadProducts() {
      try {
        const res = await fetch('/api/v1/products');
        if (!res.ok) throw new Error('Failed to load');
        allProducts = await res.json();
        renderCategories();
        renderProducts();
      } catch (err) {
        grid.innerHTML = '<p style="color:red;">Could not load products from API.</p>';
      }
    }

    function renderCategories() {
      const cats = ['ALL', ...new Set(allProducts.map(p => p.category).filter(Boolean))];
      pillsContainer.innerHTML = cats.map(c => `
        <button class="pill ${c === currentCategory ? 'active' : ''}" data-cat="${c}">
          ${c === 'ALL' ? 'All Categories' : c}
        </button>
      `).join('');

      pillsContainer.querySelectorAll('.pill').forEach(btn => {
        btn.addEventListener('click', () => {
          currentCategory = btn.dataset.cat;
          renderCategories();
          renderProducts();
        });
      });
    }

    function renderProducts() {
      const query = searchInput.value.trim();
      const filtered = allProducts
        .filter(p => {
          const match = matchProduct(query, p.name);
          const matchesCat = currentCategory === 'ALL' || p.category === currentCategory;
          return match.matched && matchesCat;
        })
        .sort((a, b) => {
          if (!query) return 0;
          const scoreA = matchProduct(query, a.name).score;
          const scoreB = matchProduct(query, b.name).score;
          return scoreB - scoreA;
        });

      if (filtered.length === 0) {
        grid.innerHTML = '<p style="color:var(--text-muted); grid-column: 1/-1; padding:24px; text-align:center;">No matching products found for your search criteria.</p>';
        return;
      }

      grid.innerHTML = filtered.map(p => {
        const hasPrice = p.latest_price !== null && p.latest_price !== undefined;
        const priceDisplay = hasPrice ? `₹${parseFloat(p.latest_price).toLocaleString('en-IN')}` : 'Price unavailable';
        return `
        <div class="card" onclick="openProduct(${p.id})">
          <div class="card-top">
            <span class="card-category">${p.category || 'General'}</span>
            <span style="font-size:11px; color:var(--text-muted);">ID: #${p.id}</span>
          </div>
          <div class="card-title">${p.name}</div>
          <div class="price-tag">
            <span style="font-size:${hasPrice ? '22px' : '15px'}; color:${hasPrice ? 'var(--primary)' : 'var(--text-muted)'}; font-weight:700;">${priceDisplay}</span>
          </div>
          <div class="card-meta">
            <span>Last seen: ${p.last_observed_at ? new Date(p.last_observed_at).toLocaleDateString() : 'N/A'}</span>
            <span class="view-link">View History →</span>
          </div>
        </div>
      `;
      }).join('');
    }

    let currentModalProductId = null;
    let currentProductData = null;

    function renderPriceChart(obs, predictedPrice, candidatePrice = null) {
      if (!obs || obs.length === 0) return '';
      const prices = obs.map(o => parseFloat(o.price));
      const allPrices = [...prices];
      if (predictedPrice) allPrices.push(parseFloat(predictedPrice));
      if (candidatePrice) allPrices.push(parseFloat(candidatePrice));

      const minP = Math.min(...allPrices);
      const maxP = Math.max(...allPrices);
      const rawSpread = maxP - minP;
      const spread = rawSpread > 0 ? rawSpread : (maxP * 0.1 || 10);
      
      const width = 500;
      const height = 150;
      const paddingX = 45;
      const paddingY = 25;
      const graphW = width - (paddingX * 2);
      const graphH = height - (paddingY * 2);

      const n = obs.length;
      let extraPoints = 0;
      if (predictedPrice) extraPoints++;
      if (candidatePrice) extraPoints++;
      const totalPoints = n + extraPoints;
      
      const points = obs.map((o, idx) => {
        const x = paddingX + (idx / Math.max(1, totalPoints - 1)) * graphW;
        const normY = rawSpread > 0 ? (parseFloat(o.price) - minP) / spread : 0.5;
        const y = height - paddingY - (normY * graphH);
        return { x, y, price: o.price, date: new Date(o.observed_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) };
      });

      let pathD = `M ${points[0].x} ${points[0].y}`;
      for (let i = 1; i < points.length; i++) {
        pathD += ` L ${points[i].x} ${points[i].y}`;
      }

      let singlePointLine = '';
      if (points.length === 1 && !predictedPrice) {
        singlePointLine = `<line x1="${paddingX}" y1="${points[0].y}" x2="${width - paddingX}" y2="${points[0].y}" stroke="#1f7359" stroke-width="2" stroke-dasharray="4,4" opacity="0.6" />`;
      }

      let forecastSvg = '';
      if (predictedPrice && points.length > 0) {
        const lastPt = points[points.length - 1];
        const forecastIdx = n;
        const fx = paddingX + (forecastIdx / Math.max(1, totalPoints - 1)) * graphW;
        const fnormY = rawSpread > 0 ? (parseFloat(predictedPrice) - minP) / spread : 0.5;
        const fy = height - paddingY - (fnormY * graphH);
        forecastSvg = `
          <line x1="${lastPt.x}" y1="${lastPt.y}" x2="${fx}" y2="${fy}" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4,4" />
          <circle cx="${fx}" cy="${fy}" r="5" fill="#f59e0b" stroke="#ffffff" stroke-width="2" />
          <text x="${fx}" y="${fy - 10}" font-size="10" font-weight="700" fill="#d97706" text-anchor="middle">₹${predictedPrice} (Forecast)</text>
        `;
      }

      let candidateSvg = '';
      if (candidatePrice && points.length > 0) {
        const lastPt = points[points.length - 1];
        const candIdx = totalPoints - 1;
        const cx = paddingX + (candIdx / Math.max(1, totalPoints - 1)) * graphW;
        const cnormY = rawSpread > 0 ? (parseFloat(candidatePrice) - minP) / spread : 0.5;
        const cy = height - paddingY - (cnormY * graphH);
        candidateSvg = `
          <line x1="${lastPt.x}" y1="${lastPt.y}" x2="${cx}" y2="${cy}" stroke="#6366f1" stroke-width="2" stroke-dasharray="3,3" />
          <circle cx="${cx}" cy="${cy}" r="6" fill="#6366f1" stroke="#ffffff" stroke-width="2" />
          <text x="${cx}" y="${cy - 10}" font-size="10" font-weight="800" fill="#4f46e5" text-anchor="middle">₹${parseFloat(candidatePrice).toFixed(0)} (Simulated Check)</text>
        `;
      }

      const dotsSvg = points.map(p => `
        <circle cx="${p.x}" cy="${p.y}" r="4.5" fill="#1f7359" stroke="#ffffff" stroke-width="2" />
        <text x="${p.x}" y="${p.y - 8}" font-size="10" font-weight="700" fill="#1f7359" text-anchor="middle">₹${p.price}</text>
        <text x="${p.x}" y="${height - 6}" font-size="9" fill="#888888" text-anchor="middle">${p.date}</text>
      `).join('');

      return `
        <div style="background:#ffffff; border:1px solid #e1e7e4; border-radius:12px; padding:16px; margin-bottom:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Visual Price Trajectory & Forecast</span>
            <div style="display:flex; gap:10px; font-size:10px; font-weight:700;">
              <span style="color:#1f7359;">● Historical Trend</span>
              ${predictedPrice ? '<span style="color:#f59e0b;">--- AI Forecast</span>' : ''}
              ${candidatePrice ? '<span style="color:#6366f1;">--- Simulated Deal</span>' : ''}
            </div>
          </div>
          <svg viewBox="0 0 ${width} ${height}" style="width:100%; height:auto; display:block;">
            <line x1="${paddingX}" y1="${height - paddingY}" x2="${width - paddingX}" y2="${height - paddingY}" stroke="#e8ece9" stroke-width="1" />
            ${singlePointLine}
            <path d="${pathD}" fill="none" stroke="#1f7359" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
            ${forecastSvg}
            ${candidateSvg}
            ${dotsSvg}
          </svg>
        </div>
      `;
    }

    async function openProduct(id) {
      try {
        currentModalProductId = id;
        const res = await fetch('/api/v1/products/' + id);
        if (!res.ok) throw new Error('Not found');
        const p = await res.json();
        currentProductData = p;

        document.getElementById('modalTitle').innerText = p.name;
        document.getElementById('modalCategory').innerText = p.category || 'General';

        const prices = (p.observations && p.observations.length > 0) ? p.observations.map(o => parseFloat(o.price)) : [];
        const hasPrices = prices.length > 0;
        const minP = hasPrices ? Math.min(...prices) : null;
        const maxP = hasPrices ? Math.max(...prices) : null;

        const hasLatest = p.latest_price !== null && p.latest_price !== undefined;
        document.getElementById('statCurrent').innerText = hasLatest ? '₹' + parseFloat(p.latest_price).toLocaleString('en-IN') : 'Price unavailable';
        document.getElementById('statLowest').innerText = minP !== null ? '₹' + minP.toFixed(2) : 'N/A';
        document.getElementById('statHighest').innerText = maxP !== null ? '₹' + maxP.toFixed(2) : 'N/A';

        const insightSec = document.getElementById('insightSection');
        if (p.insight) {
          const ins = p.insight;
          const isBuy = ins.recommendation === 'BUY_NOW';
          const isWait = ins.recommendation === 'WAIT';
          const badgeClass = isBuy ? 'buy' : (isWait ? 'wait' : 'neutral');
          const badgeText = isBuy ? '🟢 Good Time to Buy' : (isWait ? '🟡 Wait for Price Drop' : '⚪ Price is Steady');
          const trendColor = ins.trend_direction === 'UP' ? 'var(--danger)' : (ins.trend_direction === 'DOWN' ? 'var(--accent)' : 'var(--text)');
          const trendSign = ins.change_percentage > 0 ? '+' : '';

          insightSec.innerHTML = `
            <div class="insight-card ${isWait ? 'wait' : ''}">
              <div class="insight-top">
                <span style="font-size: 12px; font-weight: 700; color: var(--primary);">🤖 AI Price Forecast & Advice</span>
                <span class="insight-badge ${badgeClass}">${badgeText}</span>
              </div>
              <p style="font-size: 13px; color: var(--text); line-height: 1.4; margin-bottom: 6px;">${ins.recommendation_reason}</p>
              <div class="insight-grid">
                <div>
                  <div class="insight-label">Estimated Next Price</div>
                  <div class="insight-value">₹${ins.predicted_next_price}</div>
                </div>
                <div>
                  <div class="insight-label">Recent Trend (${ins.observation_count} checks)</div>
                  <div class="insight-value" style="color: ${trendColor};">${ins.trend_direction} (${trendSign}${ins.change_percentage}%)</div>
                </div>
              </div>
            </div>
          `;
        } else {
          insightSec.innerHTML = '';
        }

        // Render SVG Price Chart
        document.getElementById('chartSection').innerHTML = renderPriceChart(p.observations, p.insight ? p.insight.predicted_next_price : null);

        const timeline = document.getElementById('timelineList');
        timeline.innerHTML = p.observations.map((obs, idx) => {
          let diffText = '';
          if (idx > 0) {
            const prev = parseFloat(p.observations[idx - 1].price);
            const curr = parseFloat(obs.price);
            const diff = curr - prev;
            if (diff > 0) {
              diffText = `<span class="trend-up">+₹${diff.toFixed(2)}</span>`;
            } else if (diff < 0) {
              diffText = `<span class="trend-down">-₹${Math.abs(diff).toFixed(2)}</span>`;
            } else {
              diffText = `<span style="font-size:12px; color:var(--text-muted);">Unchanged</span>`;
            }
          }

          return `
            <div class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <div>
                  <div class="timeline-date">${new Date(obs.observed_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}</div>
                  <div style="font-size: 11px; color: var(--text-muted);">Source: ${obs.source_label}</div>
                </div>
                <div style="text-align: right;">
                  <div class="timeline-price">₹${obs.price}</div>
                  ${diffText}
                </div>
              </div>
            </div>
          `;
        }).join('');

        // Clear comparator state on product modal open
        document.getElementById('newPriceInput').value = '';
        document.getElementById('compareResultBox').style.display = 'none';
        document.getElementById('btnSaveCheckpoint').style.display = 'none';

        // Load Multi-Store Cross-Retailer Comparison
        try {
          const storeRes = await fetch(`/api/v1/products/${id}/multi-store-compare`);
          if (storeRes.ok) {
            const comp = await storeRes.json();
            document.getElementById('multiStoreSection').innerHTML = `
              <div style="background:#ffffff; border:1px solid #e1e7e4; border-radius:12px; padding:16px; margin-bottom:20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                  <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:12px; font-weight:700; color:var(--primary); text-transform:uppercase;">🏬 Multi-Store Price Comparison</span>
                    <span style="font-size:10px; font-weight:700; padding:2px 8px; border-radius:10px; ${comp.is_live_api ? 'background:#d4edd9; color:#155724;' : 'background:#e2e8e5; color:#314e41;'}">${comp.is_live_api ? '🟢 Live Google Shopping' : '🔌 Multi-Store Adapter Mode'}</span>
                  </div>
                  <span style="font-size:11px; font-weight:700; background:#d4edd9; color:#155724; padding:3px 10px; border-radius:12px;">🏆 ${comp.cheapest_store.includes('found') ? comp.cheapest_store : 'Best: ' + comp.cheapest_store}</span>
                </div>
                <div style="font-size:12px; color:var(--text); margin-bottom:12px; line-height:1.4; background:#f4f8f5; padding:8px 12px; border-radius:6px; border:1px solid #d5e5db;">
                  💡 <strong>${comp.recommendation_summary}</strong>
                </div>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:10px;">
                  ${comp.stores.map(s => `
                    <div style="border:${s.is_lowest && comp.is_comparable_comparison && comp.max_savings !== null ? '2px solid #1f7359' : (s.price_status === 'excluded' ? '1px dashed #e57373' : '1px solid #e5eae7')}; background:${s.is_lowest && comp.is_comparable_comparison && comp.max_savings !== null ? '#f7fbf9' : (s.price_status === 'excluded' ? '#fffaf9' : '#fff')}; border-radius:8px; padding:12px; position:relative;">
                      ${s.is_lowest && comp.is_comparable_comparison && comp.max_savings !== null ? '<span style="position:absolute; top:-8px; right:8px; background:#1f7359; color:#fff; font-size:9px; font-weight:800; padding:2px 6px; border-radius:4px; text-transform:uppercase;">Lowest Price</span>' : ''}
                      <div style="display:flex; justify-content:space-between; align-items:center;">
                        <a href="${s.store_url}" target="_blank" rel="noopener noreferrer" style="font-size:13px; font-weight:700; color:var(--text); text-decoration:none;" title="Click to visit store directly">${s.store_badge_emoji} ${s.store_name} <span style="font-size:10px; color:#1f7359;">↗</span></a>
                        <span style="font-size:11px; color:#888;">★ ${s.rating}</span>
                      </div>
                      <div style="display:flex; align-items:center; gap:6px; margin-top:4px; flex-wrap:wrap;">
                        ${s.condition ? `<span style="font-size:10px; font-weight:700; background:${s.condition.toLowerCase().includes('refurb') ? '#fff3e0' : '#f3e5f5'}; color:${s.condition.toLowerCase().includes('refurb') ? '#b78103' : '#6a1b9a'}; padding:2px 6px; border-radius:4px; border:1px solid ${s.condition.toLowerCase().includes('refurb') ? '#ffe0b2' : '#e1bee7'};">${s.condition}</span>` : ''}
                        ${s.variant_spec ? `<span style="font-size:10px; font-weight:700; background:${s.is_comparable ? '#e8f5e9' : '#fff3e0'}; color:${s.is_comparable ? '#1b5e20' : '#b78103'}; padding:2px 6px; border-radius:4px; border:1px solid ${s.is_comparable ? '#c8e6c9' : '#ffe0b2'};">${s.variant_spec}</span>` : ''}
                        ${!s.is_comparable && s.price_status === 'verified' ? `<span style="font-size:10px; color:#b78103; font-weight:600;">(Different variant/condition)</span>` : ''}
                        ${s.price_status === 'excluded' ? `<span style="font-size:10px; color:#c0392b; font-weight:700;">⚠️ Excluded Outlier</span>` : ''}
                      </div>
                      <div style="font-size:17px; font-weight:800; color:${s.price_status === 'excluded' ? '#c0392b' : (s.is_lowest && comp.is_comparable_comparison && comp.max_savings !== null ? '#1f7359' : 'var(--text)')}; margin:6px 0 4px;">
                        ${s.price_status === 'excluded' ? 'Price not verified' : (s.price !== null && s.price !== undefined ? '₹' + parseFloat(s.price).toFixed(2) : 'Price unavailable')}
                      </div>
                      <div style="font-size:11px; color:${s.in_stock ? 'var(--text-muted)' : '#c0392b'}; font-weight:${s.in_stock ? 'normal' : '600'};">${s.in_stock ? s.delivery_info : `⚠️ ${s.delivery_info}`}</div>
                      ${s.fetched_at ? `<div style="font-size:10px; color:#88958f; margin-top:2px;">Checked: ${new Date(s.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>` : ''}
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px solid #f0f3f1;">
                        ${s.is_lowest && comp.is_comparable_comparison && comp.max_savings !== null ? '<div style="font-size:11px; color:#1f7359; font-weight:700;">✓ Best Deal Selected</div>' : (s.price_status === 'excluded' ? '<div style="font-size:11px; color:#c0392b; font-weight:600;">Excluded outlier</div>' : (s.difference_from_lowest !== null && s.difference_from_lowest !== undefined ? `<div style="font-size:11px; color:#dc3545; font-weight:600;">+₹${parseFloat(s.difference_from_lowest).toFixed(2)} higher</div>` : '<div style="font-size:11px; color:#1f7359; font-weight:600;">Verified listing</div>'))}
                        <a href="${s.store_url}" target="_blank" rel="noopener noreferrer" style="font-size:11px; color:var(--primary); font-weight:700; text-decoration:none;">Visit Store →</a>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            `;
          }
        } catch (e) {
          document.getElementById('multiStoreSection').innerHTML = '';
        }

        modalBackdrop.classList.add('active');
      } catch (err) {
        showToast('Error loading product details');
      }
    }


    const btnCompareDeal = document.getElementById('btnCompareDeal');
    const btnSaveCheckpoint = document.getElementById('btnSaveCheckpoint');
    const compareInput = document.getElementById('newPriceInput');
    const compareResultBox = document.getElementById('compareResultBox');
    const btnReset = document.getElementById('btnReset');

    async function runPriceComparison() {
      const val = parseFloat(compareInput.value);
      if (!val || val <= 0 || !currentModalProductId) {
        showToast('Please enter a valid price greater than 0');
        return;
      }

      btnCompareDeal.disabled = true;
      btnCompareDeal.innerText = 'Comparing...';

      try {
        const res = await fetch(`/api/v1/products/${currentModalProductId}/compare?price=${val}`);
        if (!res.ok) throw new Error('Failed to compare price');
        const data = await res.json();

        const isBuy = data.simulated_recommendation === 'BUY_NOW';
        const isWait = data.simulated_recommendation === 'WAIT';
        const badgeColor = isBuy ? '#155724' : (isWait ? '#856404' : '#383d41');
        const badgeBg = isBuy ? '#d4edd9' : (isWait ? '#fff3cd' : '#e2e3e5');
        const diffSignLowest = data.diff_from_lowest < 0 ? '-' : '+';
        const diffSignAvg = data.diff_from_average < 0 ? '-' : '+';

        compareResultBox.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:12px; font-weight:700; color:var(--primary);">🎯 Deal Assessment Result</span>
            <span style="font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px; background:${badgeBg}; color:${badgeColor};">${data.verdict_badge}</span>
          </div>
          <p style="font-size:13px; color:var(--text); font-weight:600; margin-bottom:12px; line-height:1.4;">${data.deal_summary}</p>
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; text-align:center; background:#f7faf8; padding:10px; border-radius:8px; border:1px solid #e1e7e4;">
            <div>
              <div style="font-size:10px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Candidate Price</div>
              <div style="font-size:14px; font-weight:800; color:var(--primary);">₹${parseFloat(data.target_price).toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size:10px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">vs All-Time Low</div>
              <div style="font-size:12px; font-weight:700; color:${data.diff_from_lowest <= 0 ? 'var(--accent)' : 'var(--danger)'};">${diffSignLowest}₹${Math.abs(data.diff_from_lowest).toFixed(2)} (${data.diff_lowest_pct}%)</div>
            </div>
            <div>
              <div style="font-size:10px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">vs Historical Avg</div>
              <div style="font-size:12px; font-weight:700; color:${data.diff_from_average <= 0 ? 'var(--accent)' : 'var(--danger)'};">${diffSignAvg}₹${Math.abs(data.diff_from_average).toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size:10px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">All-Time High</div>
              <div style="font-size:13px; font-weight:700; color:var(--text);">₹${parseFloat(data.historical_highest).toFixed(2)}</div>
            </div>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; font-size:11px; color:var(--text-muted);">
            <span>🛡️ Simulation only. Product history has NOT been changed.</span>
            <span style="font-weight:700; color:var(--primary);">AI Advice: ${isBuy ? '🟢 Good Time to Buy' : (isWait ? '🟡 Wait for Drop' : '⚪ Price is Steady')}</span>
          </div>
        `;

        compareResultBox.style.display = 'block';
        btnSaveCheckpoint.style.display = 'inline-flex';
        btnSaveCheckpoint.innerText = `💾 Save ₹${val.toFixed(0)} to History`;

        if (currentProductData) {
          document.getElementById('chartSection').innerHTML = renderPriceChart(
            currentProductData.observations,
            currentProductData.insight ? currentProductData.insight.predicted_next_price : null,
            val
          );
        }
      } catch (err) {
        showToast('Error comparing price');
      } finally {
        btnCompareDeal.disabled = false;
        btnCompareDeal.innerHTML = '<span>🔍</span> Check & Compare Deal';
      }
    }

    btnCompareDeal.addEventListener('click', runPriceComparison);
    compareInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        runPriceComparison();
      }
    });

    btnSaveCheckpoint.addEventListener('click', async () => {
      const val = parseFloat(compareInput.value);
      if (!val || !currentModalProductId) return;

      if (!confirm(`Permanently record ₹${val.toFixed(2)} as an official historical checkpoint?`)) {
        return;
      }

      btnSaveCheckpoint.disabled = true;
      try {
        const res = await fetch(`/api/v1/products/${currentModalProductId}/observations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ price: val, source_label: 'manual_checkpoint' })
        });
        if (!res.ok) throw new Error('Failed to record price');
        showToast(`Recorded new permanent price checkpoint: ₹${val.toFixed(2)}`);
        compareInput.value = '';
        compareResultBox.style.display = 'none';
        btnSaveCheckpoint.style.display = 'none';
        await loadProducts();
        await openProduct(currentModalProductId);
      } catch (err) {
        showToast('Error saving checkpoint');
      } finally {
        btnSaveCheckpoint.disabled = false;
      }
    });

    modalClose.addEventListener('click', () => modalBackdrop.classList.remove('active'));
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) modalBackdrop.classList.remove('active');
    });

    searchInput.addEventListener('input', renderProducts);

    btnReset.addEventListener('click', async () => {
      if (!confirm('Reset database back to pristine original sample data? This will clear all test checkpoints.')) {
        return;
      }
      btnReset.disabled = true;
      btnReset.innerText = 'Resetting...';
      try {
        const res = await fetch('/api/v1/reset', { method: 'POST' });
        const data = await res.json();
        showToast('Database reset to clean sample data!');
        modalBackdrop.classList.remove('active');
        await loadProducts();
      } catch (err) {
        showToast('Failed to reset database');
      } finally {
        btnReset.disabled = false;
        btnReset.innerHTML = '<span>↺</span> Reset Clean Data';
      }
    });

    btnSeed.addEventListener('click', async () => {
      btnSeed.disabled = true;
      btnSeed.innerText = 'Seeding...';
      try {
        const res = await fetch('/api/v1/seed', { method: 'POST' });
        const data = await res.json();
        showToast(`Seeded: ${data.products_created} products, ${data.observations_created} observations.`);
        await loadProducts();
      } catch (err) {
        showToast('Failed to seed database');
      } finally {
        btnSeed.disabled = false;
        btnSeed.innerHTML = '<span>🔄</span> Re-seed Sample Data';
      }
    });

    // Universal Link-Based & Keyword Search
    const universalInput = document.getElementById('universalSearchInput');
    const btnUniversalSearch = document.getElementById('btnUniversalSearch');
    const universalResult = document.getElementById('universalResultContainer');

    async function runUniversalSearch() {
      const q = universalInput.value.trim();
      if (!q) {
        showToast('Please paste a link or type a product name');
        return;
      }

      btnUniversalSearch.disabled = true;
      btnUniversalSearch.innerHTML = '<span>⏳</span> Searching Stores...';
      universalResult.style.display = 'block';
      universalResult.innerHTML = '<p style="color:var(--text-muted); font-size:13px; padding:10px;">Searching and comparing across live retailers...</p>';

      try {
        const res = await fetch(`/api/v1/search/universal?query=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error('Search failed');
        const data = await res.json();

        if (data.db_updated) {
          await loadProducts();
          const act = data.db_action === 'created' ? 'Added new product to' : 'Updated price checkpoint in';
          showToast(`✓ Automatically ${act} catalog (Product ID: ${data.tracked_product_id})`);
        }

        const hasReliable = data.has_reliable_match && data.lowest_price !== null && data.stores && data.stores.length > 0;

        let actionButtonHtml = '';
        if (data.tracked_product_id) {
          actionButtonHtml = `
            <button type="button" class="btn btn-primary" onclick="openProduct(${data.tracked_product_id})" style="padding:6px 14px; font-size:12px; font-weight:700; background:#1f7359; color:white; border:none; border-radius:6px; cursor:pointer; display:inline-flex; align-items:center; gap:6px;">
              <span>📈</span> View Price Graph & AI Forecast →
            </button>
          `;
        } else if (hasReliable) {
          actionButtonHtml = `
            <button type="button" class="btn btn-primary" id="btnTrackUniversal" style="padding:6px 12px; font-size:11px;">
              ➕ Track in Catalog
            </button>
          `;
        }

        let storeGridHtml = '';
        if (!hasReliable) {
          storeGridHtml = `
            <div style="text-align:center; padding:24px 16px; background:#fff; border:1px dashed #d5ddd8; border-radius:10px;">
              <div style="font-size:28px; margin-bottom:8px;">🔎</div>
              <div style="font-size:15px; font-weight:800; color:#18231f;">${data.cheapest_store.includes('trusted') || data.cheapest_store.includes('comparable') || data.cheapest_store.includes('found') ? 'No Trusted Comparable Listings Found' : 'Price Unavailable / No Reliable Match'}</div>
              <p style="font-size:13px; color:#6e7d75; margin:6px 0 0;">
                ${data.recommendation_summary || 'No verified price data found in trusted data sources.'}
              </p>
            </div>
          `;
        } else {
          storeGridHtml = `
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:10px;">
              ${data.stores.map(s => `
                <div style="border:${s.is_lowest && data.is_comparable_comparison && data.max_savings !== null ? '2px solid #1f7359' : (s.price_status === 'excluded' ? '1px dashed #e57373' : '1px solid #e5eae7')}; background:${s.is_lowest && data.is_comparable_comparison && data.max_savings !== null ? '#ffffff' : (s.price_status === 'excluded' ? '#fffaf9' : '#fafcfb')}; border-radius:8px; padding:12px; position:relative;">
                  ${s.is_lowest && data.is_comparable_comparison && data.max_savings !== null ? '<span style="position:absolute; top:-8px; right:8px; background:#1f7359; color:#fff; font-size:9px; font-weight:800; padding:2px 6px; border-radius:4px; text-transform:uppercase;">Lowest Price</span>' : ''}
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <a href="${s.store_url}" target="_blank" rel="noopener noreferrer" style="font-size:13px; font-weight:700; color:var(--text); text-decoration:none;" title="Click to visit store directly">${s.store_badge_emoji} ${s.store_name} <span style="font-size:10px; color:#1f7359;">↗</span></a>
                    <span style="font-size:11px; color:#888;">★ ${s.rating}</span>
                  </div>
                  <div style="display:flex; align-items:center; gap:6px; margin-top:4px; flex-wrap:wrap;">
                    ${s.condition ? `<span style="font-size:10px; font-weight:700; background:${s.condition.toLowerCase().includes('refurb') ? '#fff3e0' : '#f3e5f5'}; color:${s.condition.toLowerCase().includes('refurb') ? '#b78103' : '#6a1b9a'}; padding:2px 6px; border-radius:4px; border:1px solid ${s.condition.toLowerCase().includes('refurb') ? '#ffe0b2' : '#e1bee7'};">${s.condition}</span>` : ''}
                    ${s.variant_spec ? `<span style="font-size:10px; font-weight:700; background:${s.is_comparable ? '#e8f5e9' : '#fff3e0'}; color:${s.is_comparable ? '#1b5e20' : '#b78103'}; padding:2px 6px; border-radius:4px; border:1px solid ${s.is_comparable ? '#c8e6c9' : '#ffe0b2'};">${s.variant_spec}</span>` : ''}
                    ${!s.is_comparable && s.price_status === 'verified' ? `<span style="font-size:10px; color:#b78103; font-weight:600;">(Different variant/condition)</span>` : ''}
                    ${s.price_status === 'excluded' ? `<span style="font-size:10px; color:#c0392b; font-weight:700;">⚠️ Excluded Outlier</span>` : ''}
                  </div>
                  <div style="font-size:11px; color:var(--primary); font-weight:600; margin:3px 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    <a href="${s.store_url}" target="_blank" rel="noopener noreferrer" style="color:inherit; text-decoration:none;" title="${s.matched_product_title || data.extracted_title}">
                      📦 ${s.matched_product_title || data.extracted_title}
                    </a>
                  </div>
                  <div style="font-size:17px; font-weight:800; color:${s.price_status === 'excluded' ? '#c0392b' : (s.is_lowest && data.is_comparable_comparison && data.max_savings !== null ? '#1f7359' : 'var(--text)')}; margin:6px 0 4px;">
                    ${s.price_status === 'excluded' ? 'Price not verified' : (s.price !== null && s.price !== undefined ? (s.currency === 'USD' ? '$' : '₹') + parseFloat(s.price).toFixed(2) : 'Price unavailable')}
                  </div>
                  <div style="font-size:11px; color:${s.in_stock ? 'var(--text-muted)' : '#c0392b'}; font-weight:${s.in_stock ? 'normal' : '600'};">${s.in_stock ? s.delivery_info : `⚠️ ${s.delivery_info}`}</div>
                  ${s.fetched_at ? `<div style="font-size:10px; color:#88958f; margin-top:2px;">Checked: ${new Date(s.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>` : ''}
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                    ${s.is_lowest && data.is_comparable_comparison && data.max_savings !== null ? '<span style="font-size:11px; color:#1f7359; font-weight:700;">✓ Best Deal</span>' : (s.price_status === 'excluded' ? '<span style="font-size:11px; color:#c0392b; font-weight:600;">Excluded outlier</span>' : (s.difference_from_lowest !== null && s.difference_from_lowest !== undefined ? `<span style="font-size:11px; color:#dc3545; font-weight:600;">+₹${parseFloat(s.difference_from_lowest).toFixed(2)}</span>` : '<span style="font-size:11px; color:#1f7359; font-weight:600;">Verified listing</span>'))}
                    <a href="${s.store_url}" target="_blank" rel="noopener noreferrer" style="font-size:11px; color:var(--primary); font-weight:700; text-decoration:none;">Visit Store →</a>
                  </div>
                </div>
              `).join('')}
            </div>
          `;
        }

        const retailerStatusHtml = `
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px;">
            <span style="font-size:11px; font-weight:700; padding:4px 10px; border-radius:6px; background:${data.amazon_found ? '#e8f5e9' : '#fff3e0'}; color:${data.amazon_found ? '#1b5e20' : '#b78103'}; border:1px solid ${data.amazon_found ? '#c8e6c9' : '#ffe0b2'}; display:inline-flex; align-items:center; gap:4px;">
              🛒 Amazon India: ${data.amazon_found ? '✓ Verified Listing' : '✕ Not found in search results'}
            </span>
            <span style="font-size:11px; font-weight:700; padding:4px 10px; border-radius:6px; background:${data.flipkart_found ? '#e8f5e9' : '#fff3e0'}; color:${data.flipkart_found ? '#1b5e20' : '#b78103'}; border:1px solid ${data.flipkart_found ? '#c8e6c9' : '#ffe0b2'}; display:inline-flex; align-items:center; gap:4px;">
              🛍️ Flipkart: ${data.flipkart_found ? '✓ Verified Listing' : '✕ Not found in search results'}
            </span>
            ${data.comparable_spec ? `
              <span style="font-size:11px; font-weight:700; padding:4px 10px; border-radius:6px; background:#e3f2fd; color:#0d47a1; border:1px solid #bbdefb; display:inline-flex; align-items:center; gap:4px;">
                🎯 Specification Tier: ${data.comparable_spec}
              </span>
            ` : ''}
            ${data.comparable_condition ? `
              <span style="font-size:11px; font-weight:700; padding:4px 10px; border-radius:6px; background:${data.comparable_condition.toLowerCase().includes('refurb') ? '#fff3e0' : '#f3e5f5'}; color:${data.comparable_condition.toLowerCase().includes('refurb') ? '#e65100' : '#6a1b9a'}; border:1px solid ${data.comparable_condition.toLowerCase().includes('refurb') ? '#ffe0b2' : '#e1bee7'}; display:inline-flex; align-items:center; gap:4px;">
                🏷️ Condition: ${data.comparable_condition}
              </span>
            ` : ''}
          </div>
        `;

        universalResult.innerHTML = `
          <div style="background:#f7fbf9; border:1px solid #cce2d6; border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
              <div>
                <span style="font-size:11px; font-weight:700; color:var(--primary); text-transform:uppercase;">${data.source_platform} Detected</span>
                <h3 style="font-size:16px; font-weight:800; margin:4px 0 2px;">${data.extracted_title}</h3>
                <span style="font-size:11px; color:var(--text-muted);">${data.is_url ? 'Extracted from submitted product URL' : 'Searched by product keyword'}</span>
              </div>
              <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                <span style="font-size:11px; font-weight:700; padding:3px 10px; border-radius:12px; ${data.is_live_api ? 'background:#d4edd9; color:#155724;' : 'background:#e2e8e5; color:#314e41;'}">${data.is_live_api ? '🟢 Live Google Shopping' : '🔌 Multi-Store Adapter'}</span>
                ${data.db_updated ? `
                  <span style="font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px; background:#d4edd9; color:#155724; border:1px solid #b8dfc4;">
                    ✓ Saved to Database (${data.db_action})
                  </span>
                ` : ''}
                ${actionButtonHtml}
              </div>
            </div>

            <div style="font-size:12px; color:var(--text); margin-bottom:12px; line-height:1.4; background:#ffffff; padding:10px 14px; border-radius:8px; border:1px solid #d5e5db;">
              💡 <strong>${data.recommendation_summary}</strong>
            </div>

            ${retailerStatusHtml}

            ${storeGridHtml}
          </div>
        `;

        const btnTrack = document.getElementById('btnTrackUniversal');
        if (btnTrack) {
          btnTrack.addEventListener('click', async () => {
            try {
              const trackRes = await fetch('/api/v1/products/quick-add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  name: data.extracted_title,
                  price: parseFloat(data.lowest_price),
                  category: 'General'
                })
              });
              if (!trackRes.ok) throw new Error('Failed to track');
              showToast(`Added "${data.extracted_title}" to tracking catalog!`);
              await loadProducts();
            } catch (e) {
              showToast('Error tracking product');
            }
          });
        }

      } catch (err) {
        universalResult.innerHTML = '<p style="color:var(--danger); font-size:13px; padding:10px;">Failed to fetch prices for this link/query. Please check the URL and try again.</p>';
      } finally {
        btnUniversalSearch.disabled = false;
        btnUniversalSearch.innerHTML = '<span>🔍</span> Compare Across Stores';
      }
    }

    btnUniversalSearch.addEventListener('click', runUniversalSearch);
    universalInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        runUniversalSearch();
      }
    });

    loadProducts();

  </script>
</body>
</html>
"""


@web_router.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_dashboard() -> HTMLResponse:
    """Serve the interactive web interface."""
    return HTMLResponse(content=DASHBOARD_HTML)
