const state = {
  history: [],
  busy: false,
  gaps: [],
  roadmapUrl: "",
};

function issueLink(nid) {
  if (!nid) return "none";
  const m = /^issue_(\d+)$/.exec(nid);
  if (!m || !state.roadmapUrl) return `<code>${nid}</code>`;
  const url = `${state.roadmapUrl}/issues/${m[1]}`;
  return `<a href="${url}" target="_blank" rel="noreferrer">${nid}</a>`;
}

const $ = (sel) => document.querySelector(sel);

function renderMarkdownLite(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[(.+?)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

function addBubble(role, text) {
  const el = document.createElement("div");
  el.className = `bubble ${role}`;
  el.innerHTML = renderMarkdownLite(text);
  $("#messages").appendChild(el);
  $("#messages").scrollTop = $("#messages").scrollHeight;
}

async function refreshStatus() {
  const s = await fetch("/api/status").then((r) => r.json());
  $("#provider").textContent = `${s.provider.label} · ${s.provider.model}`;
  $("#subtitle").textContent = `${s.product} · ${s.gaps_count || 0} gaps loaded`;
  state.roadmapUrl = s.roadmap || "";
  if (s.gaps_count) {
    state.gaps = await fetch("/api/gaps").then((r) => r.json());
  }
  return s;
}

function renderGapCard(gap, rank) {
  if (!gap) {
    $("#gapCard").className = "gap-card empty";
    $("#gapCard").textContent = "No gap focused yet.";
    return;
  }
  $("#gapCard").className = "gap-card";
  $("#gapCard").innerHTML = `
    <span class="verdict ${gap.verdict || ""}">${gap.verdict || "—"} · ${gap.confidence}%</span>
    <div><strong>#${rank}</strong> ${renderMarkdownLite(gap.need || "")}</div>
    <div class="meta" style="margin-top:8px;color:#678073;font-size:0.82rem">
      Nearest: ${issueLink(gap.nearest_roadmap_item)}
      · sim ${gap.roadmap_similarity ?? "—"}
      · ${ (gap.evidence_ids || []).length } evidence IDs
    </div>
  `;
}

async function loadEvidence(ids, focusRank) {
  const list = $("#evidenceList");
  list.innerHTML = "";
  if (focusRank && state.gaps[focusRank - 1]) {
    renderGapCard(state.gaps[focusRank - 1], focusRank);
  }
  for (const id of (ids || []).slice(0, 8)) {
    try {
      const item = await fetch(`/api/evidence/${encodeURIComponent(id)}`).then((r) => {
        if (!r.ok) throw new Error("missing");
        return r.json();
      });
      const div = document.createElement("div");
      div.className = "ev-item";
      if (item.title) {
        div.innerHTML = `
          <div class="id">${item.id} · issue #${item.number || "?"}</div>
          <div>${renderMarkdownLite(item.title)}</div>
          <div class="meta">${renderMarkdownLite((item.body || "").slice(0, 220))}</div>
          ${item.url ? `<div class="meta"><a href="${item.url}" target="_blank" rel="noreferrer">Open on GitHub</a></div>` : ""}
        `;
      } else {
        div.innerHTML = `
          <div class="id">${item.id}</div>
          <div>${renderMarkdownLite(item.text || "")}</div>
          <div class="meta">rating ${item.rating ?? "—"} · ${item.date || ""}</div>
        `;
      }
      list.appendChild(div);
    } catch {
      /* skip missing */
    }
  }
}

async function send(message) {
  if (!message || state.busy) return;
  state.busy = true;
  $("#input").disabled = true;
  addBubble("user", message);
  state.history.push({ role: "user", content: message });

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: state.history }),
    }).then((r) => r.json());

    addBubble("bot", res.reply || "(empty reply)");
    state.history.push({ role: "assistant", content: res.reply || "" });
    await loadEvidence(res.evidence_ids || [], res.focus_rank);
  } catch (e) {
    addBubble("bot", `Something went wrong: ${e.message || e}`);
  } finally {
    state.busy = false;
    $("#input").disabled = false;
    $("#input").focus();
  }
}

async function runAnalyze() {
  const btn = $("#btnAnalyze");
  btn.disabled = true;
  btn.textContent = "Running…";
  addBubble("bot", "Running analysis on reviews + live GitHub issues. This can take a minute…");
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sample_n: 3000, top_n: 5 }),
    }).then((r) => r.json());
    await refreshStatus();
    const lines = (res.gaps || [])
      .map((g) => `#${g.rank} · ${g.confidence}% · ${g.verdict} — ${g.need}`)
      .join("\n");
    addBubble(
      "bot",
      `Done via **${res.provider.label}**. Top ${res.count} gaps:\n\n${lines}\n\nAsk me why any of them ranked.`
    );
  } catch (e) {
    addBubble("bot", `Analysis failed: ${e.message || e}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run analysis";
  }
}

$("#form").addEventListener("submit", (e) => {
  e.preventDefault();
  const val = $("#input").value.trim();
  $("#input").value = "";
  send(val);
});

$("#suggestions").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-q]");
  if (btn) send(btn.dataset.q);
});

$("#btnAnalyze").addEventListener("click", runAnalyze);

(async function boot() {
  const s = await refreshStatus();
  const intro = s.has_gaps
    ? `I have **${s.gaps_count}** unmet needs ranked for **${s.product}** against the live GitHub roadmap.\n\nAsk me anything — or hit a suggestion chip.`
    : `No gaps yet. Click **Run analysis** (works offline with heuristics, or set a free **GROQ_API_KEY** for stronger answers).`;
  addBubble("bot", intro);
  if (s.has_gaps && state.gaps[0]) {
    renderGapCard(state.gaps[0], 1);
    await loadEvidence((state.gaps[0].evidence_ids || []).slice(0, 5), 1);
  }
})();
