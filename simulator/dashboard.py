"""Dark educational dashboard for the simulator.

The page is a single self-contained document. It reads the synthetic API with
the demo key and renders balances, the seeded order book, open orders and
withdrawal history. It never loads a third-party asset and never contacts a
real exchange.
"""

DISPLAY_NAME = 'BINANCE SIMULATOR'
DISCLAIMER = (
    'INDEPENDENT EDUCATIONAL SIMULATOR — NOT BINANCE. '
    'Synthetic data, synthetic accounts and an in-process fake chain only. '
    'No real funds, wallets, keys or blockchain transactions.')

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME__ — Educational Demo</title>
<style>
  :root {
    --bg: #0b0e11;
    --panel: #14181d;
    --panel-2: #1b2129;
    --line: #2a323d;
    --text: #e6edf3;
    --muted: #8b98a5;
    --accent: #f0b90b;
    --green: #16c784;
    --red: #ea3943;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      Helvetica, Arial, sans-serif;
  }
  header {
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; padding: 18px 28px; border-bottom: 1px solid var(--line);
    background: #101418;
  }
  .brand { display: flex; align-items: center; gap: 14px; }
  .mark {
    width: 42px; height: 42px; border-radius: 12px; display: grid;
    place-items: center; background: var(--accent); color: #101418;
    font-weight: 800; font-size: 18px;
  }
  h1 { font-size: 20px; margin: 0; letter-spacing: .08em; }
  .sub { color: var(--muted); font-size: 12px; margin-top: 3px; }
  .badge {
    border: 1px solid #4a3b0b; background: #241d07; color: var(--accent);
    padding: 7px 11px; border-radius: 999px; font-size: 12px;
    white-space: nowrap;
  }
  .disclaimer {
    background: #1d1607; border-bottom: 1px solid #4a3b0b;
    color: #f5d982; font-size: 12.5px; line-height: 1.5;
    padding: 10px 28px;
  }
  main { padding: 24px 28px 48px; max-width: 1280px; margin: 0 auto; }
  .grid { display: grid; gap: 16px; }
  .cards { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .two { grid-template-columns: 1.15fr .85fr; margin-top: 16px; }
  .panel {
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 14px; overflow: hidden;
  }
  .panel h2 {
    font-size: 13px; text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); margin: 0; padding: 14px 16px;
    border-bottom: 1px solid var(--line);
  }
  .card { padding: 16px; }
  .label { color: var(--muted); font-size: 12px; }
  .value { font-size: 24px; font-weight: 650; margin-top: 7px; }
  .value.small { font-size: 17px; }
  .ok { color: var(--green); }
  .warn { color: var(--accent); }
  .bad { color: var(--red); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 16px; text-align: left; }
  th { color: var(--muted); font-weight: 500; font-size: 11px;
       text-transform: uppercase; letter-spacing: .06em; }
  tbody tr + tr { border-top: 1px solid #20262e; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .scroll { max-height: 360px; overflow: auto; }
  .empty { color: var(--muted); padding: 16px; font-size: 13px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; padding: 14px 16px; }
  .chip {
    border: 1px solid var(--line); background: var(--panel-2);
    padding: 7px 10px; border-radius: 8px; font-size: 12px;
  }
  .status { display: flex; gap: 18px; flex-wrap: wrap; padding: 14px 16px; }
  .status div { font-size: 12px; color: var(--muted); }
  .status b { display: block; color: var(--text); font-size: 14px;
              margin-top: 3px; }
  footer { color: var(--muted); font-size: 11.5px; margin-top: 20px;
           line-height: 1.6; }
  @media (max-width: 980px) {
    .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .two { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<header>
  <div class="brand">
    <div class="mark">BS</div>
    <div>
      <h1>__NAME__</h1>
      <div class="sub">Security Incident Simulator — Educational Demo</div>
    </div>
  </div>
  <div class="badge">SYNTHETIC ENVIRONMENT</div>
</header>
<div class="disclaimer">__DISCLAIMER__</div>
<main>
  <section class="grid cards">
    <div class="panel card"><div class="label">Account</div>
      <div class="value small" id="account">demo-user</div>
      <div class="label" id="account-state">loading…</div></div>
    <div class="panel card"><div class="label">Assets</div>
      <div class="value" id="asset-count">–</div>
      <div class="label">synthetic balances</div></div>
    <div class="panel card"><div class="label">Open orders</div>
      <div class="value" id="open-count">–</div>
      <div class="label">seeded OMGETH book</div></div>
    <div class="panel card"><div class="label">Chain broadcasts</div>
      <div class="value" id="broadcast-count">–</div>
      <div class="label">in-process fake chain</div></div>
  </section>

  <section class="grid two">
    <div class="panel">
      <h2>Balances</h2>
      <div class="scroll"><table>
        <thead><tr><th>Asset</th><th class="num">Free</th>
          <th class="num">Locked</th></tr></thead>
        <tbody id="balances"><tr><td colspan="3" class="empty">loading…</td></tr></tbody>
      </table></div>
    </div>
    <div class="panel">
      <h2>Withdrawal controls</h2>
      <div class="status" id="controls">
        <div>Guard<b>loading…</b></div>
      </div>
      <h2>Withdrawal history</h2>
      <div class="scroll"><table>
        <thead><tr><th>Asset</th><th class="num">Amount</th>
          <th>Address</th><th>Tx</th></tr></thead>
        <tbody id="withdrawals"><tr><td colspan="4" class="empty">loading…</td></tr></tbody>
      </table></div>
    </div>
  </section>

  <section class="grid two">
    <div class="panel">
      <h2>Order book — OMGETH</h2>
      <table>
        <thead><tr><th>Side</th><th class="num">Price</th>
          <th class="num">Quantity</th></tr></thead>
        <tbody id="book"><tr><td colspan="3" class="empty">loading…</td></tr></tbody>
      </table>
    </div>
    <div class="panel">
      <h2>Trading pairs</h2>
      <div class="chips" id="pairs"><span class="empty">loading…</span></div>
    </div>
  </section>

  <footer>
    Data is generated by <code>scripts/run_demo_server.py</code> with
    fakeredis and <code>simulator/fake_chain.py</code>. The real October 2026
    incident involved an internal wallet signing service and EIP-7702
    authorizations; this page is an independent withdrawal-control analogue,
    not a reproduction of that intrusion.
  </footer>
</main>
<script>
const KEY = 'demo-user';
const H = { 'X-MBX-APIKEY': KEY };

async function get(path) {
  const response = await fetch(path, { headers: H });
  return response.json();
}

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function row(cells, numeric) {
  const tr = document.createElement('tr');
  cells.forEach(function (value, index) {
    const td = el('td', value);
    if (numeric && numeric.indexOf(index) >= 0) td.className = 'num';
    tr.appendChild(td);
  });
  return tr;
}

async function load() {
  try {
    const [account, book, history, openOrders, info, status] =
      await Promise.all([
        get('/api/v3/account'),
        get('/api/v1/depth?symbol=OMGETH'),
        get('/wapi/v3/withdrawHistory.html'),
        get('/api/v3/openOrders?symbol=OMGETH'),
        get('/api/v1/exchangeInfo'),
        get('/api/v1/simulator/status'),
      ]);

    const balances = document.getElementById('balances');
    balances.innerHTML = '';
    account.balances.forEach(function (balance) {
      const total = Number(balance.free) + Number(balance.locked);
      if (total <= 0) return;
      balances.appendChild(row([
        balance.asset, balance.free, balance.locked], [1, 2]));
    });
    if (!balances.children.length) {
      balances.appendChild(row(['No synthetic balances', '', '']));
    }
    document.getElementById('asset-count').textContent = account.balances.length;
    document.getElementById('account-state').textContent =
      account.canWithdraw ? 'withdrawal permission active'
                          : 'withdrawal permission blocked';
    document.getElementById('account-state').className =
      'label ' + (account.canWithdraw ? 'ok' : 'bad');

    document.getElementById('open-count').textContent = openOrders.length;
    document.getElementById('broadcast-count').textContent =
      status.chain.broadcasts;

    const bookBody = document.getElementById('book');
    bookBody.innerHTML = '';
    (book.asks || []).forEach(function (ask) {
      bookBody.appendChild(row(['ASK', ask[0], ask[1]], [1, 2]));
    });
    (book.bids || []).forEach(function (bid) {
      bookBody.appendChild(row(['BID', bid[0], bid[1]], [1, 2]));
    });

    const withdrawals = document.getElementById('withdrawals');
    withdrawals.innerHTML = '';
    (history.withdrawList || []).forEach(function (item) {
      withdrawals.appendChild(row([
        item.asset, item.amount, item.address, item.txId], [1]));
    });
    if (!withdrawals.children.length) {
      withdrawals.appendChild(row(['No synthetic withdrawals', '', '', '']));
    }

    const pairs = document.getElementById('pairs');
    pairs.innerHTML = '';
    info.symbols.slice(0, 60).forEach(function (symbol) {
      pairs.appendChild(el('span', symbol.symbol, 'chip'));
    });

    const controls = document.getElementById('controls');
    controls.innerHTML = '';
    [
      ['Guard', status.guard.paused ? 'PAUSED' : 'ACTIVE'],
      ['Audit chain', status.guard.audit_chain_valid ? 'VALID' : 'BROKEN'],
      ['Audit records', status.guard.audit_records],
      ['Revoked keys', status.guard.revoked.length],
    ].forEach(function (item) {
      const box = el('div', null);
      box.appendChild(el('span', item[0]));
      const value = el('b', String(item[1]));
      if (item[0] === 'Guard') value.className = status.guard.paused ? 'bad' : 'ok';
      if (item[0] === 'Audit chain') {
        value.className = status.guard.audit_chain_valid ? 'ok' : 'bad';
      }
      box.appendChild(value);
      controls.appendChild(box);
    });
  } catch (error) {
    document.getElementById('account-state').textContent =
      'API error: ' + error.message;
  }
}

load();
</script>
</body>
</html>
"""


def render_dashboard():
    return (PAGE.replace('__NAME__', DISPLAY_NAME)
                .replace('__DISCLAIMER__', DISCLAIMER))
