/* Dashboard UI. Every number comes from window.DATA, built from the DuckDB marts. */
(function () {
  "use strict";
  var D = window.DATA;
  var theme = new URLSearchParams(location.search).get("theme");
  if (theme === "light" || theme === "dark") document.documentElement.setAttribute("data-theme", theme);
  var TABS = [["executive", "Executive Overview"], ["utilization", "Utilization & Payment"], ["providers", "Provider Operations"],
    ["quality", "Quality & Cohorts"], ["definitions", "Data Quality & Definitions"]];
  var SETTINGS = ["inpatient", "outpatient", "carrier"];
  var COLORS = { inpatient: "var(--c1)", outpatient: "var(--c2)", carrier: "var(--c3)" };
  var YEARS = D.kpi_annual.map(function (r) { return r.year; });
  var state = { tab: "executive", year: YEARS.indexOf(2009) >= 0 ? 2009 : YEARS[YEARS.length - 1], setting: "all", sex: "all", race: "all", age: "all",
    iqr: 3.0, topN: 10, ptype: "facility_inpatient", provider: null, query: "", condition: "" };

  function esc(v) { return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function num(x, d) { return x === null || x === undefined || isNaN(x) ? "n/a" : Number(x).toLocaleString("en-US", { maximumFractionDigits: d || 0, minimumFractionDigits: d || 0 }); }
  function usd(x, d) { if (x === null || x === undefined || isNaN(x)) return "n/a"; var a = Math.abs(x), s = x < 0 ? "-" : ""; if (a >= 1e9) return s + "$" + (a / 1e9).toFixed(2) + "B"; if (a >= 1e6) return s + "$" + (a / 1e6).toFixed(1) + "M"; if (a >= 1e3) return s + "$" + (a / 1e3).toFixed(1) + "K"; return s + "$" + a.toFixed(d || 0); }
  function pct(x, d) { return x === null || x === undefined || isNaN(x) ? "n/a" : (x * 100).toFixed(d === undefined ? 1 : d) + "%"; }
  function card(label, value, sub, tip) { return '<div class="card" title="' + esc(tip || "") + '"><div class="card-label">' + label + '</div><div class="card-value">' + value + '</div><div class="card-sub">' + sub + "</div></div>"; }
  function table(headers, rows, numeric) { numeric = numeric || []; return '<div class="table-wrap"><table><thead><tr>' + headers.map(function (h, i) { return "<th" + (numeric.indexOf(i) >= 0 ? ' class="num"' : "") + ' scope="col">' + esc(h) + "</th>"; }).join("") + "</tr></thead><tbody>" + rows.map(function (r) { return "<tr>" + r.map(function (c, i) { return "<td" + (numeric.indexOf(i) >= 0 ? ' class="num"' : "") + ">" + c + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table></div>"; }
  function sel(id, label, options, value) { return '<label>' + label + '<select id="' + id + '">' + options.map(function (o) { var v = Array.isArray(o) ? o[0] : o, t = Array.isArray(o) ? o[1] : o; return '<option value="' + esc(v) + '"' + (String(v) === String(value) ? " selected" : "") + ">" + esc(t) + "</option>"; }).join("") + "</select></label>"; }
  function svg(w, h, label, inner) { return '<svg viewBox="0 0 ' + w + " " + h + '" role="img" aria-label="' + esc(label) + '" class="chart">' + inner + "</svg>"; }
  function scale(d0, d1, r0, r1) { return function (v) { return d1 === d0 ? r0 : r0 + (v - d0) * (r1 - r0) / (d1 - d0); }; }
  function ticks(lo, hi, n) { var span = hi - lo || 1, step = Math.pow(10, Math.floor(Math.log10(span / n))), e = span / n / step; step *= e >= 5 ? 5 : e >= 2 ? 2 : 1; var out = [], t = Math.ceil(lo / step) * step; for (; t <= hi + 1e-9; t += step) out.push(t); return out; }
  function tag(kind, t) { return '<span class="tag tag-' + kind + '">' + esc(t) + "</span>"; }
  function yearRow(y) { return D.kpi_annual.filter(function (r) { return r.year === y; })[0]; }

  function stackedMonthly(valueKey, fmt, label) {
    var months = Array.from(new Set(D.monthly_payments.map(function (r) { return r.year_month; }))).sort();
    var W = 760, H = 250, L = 64, R = 12, T = 12, B = 30;
    var data = months.map(function (m) { var o = { m: m, total: 0 }; SETTINGS.forEach(function (s) { var r = D.monthly_payments.filter(function (x) { return x.year_month === m && x.setting === s; })[0]; o[s] = r ? r[valueKey] : 0; o.total += Math.max(0, o[s]); }); return o; });
    var hi = Math.max.apply(null, data.map(function (d) { return d.total; })), tk = ticks(0, hi, 4); hi = Math.max(hi, tk[tk.length - 1]);
    var y = scale(0, hi, H - B, T), step = (W - L - R) / months.length, bw = step * 0.78, inner = "";
    tk.forEach(function (t) { inner += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(t) + '" y2="' + y(t) + '" class="grid"/><text x="' + (L - 6) + '" y="' + (y(t) + 4) + '" class="axis" text-anchor="end">' + fmt(t) + "</text>"; });
    data.forEach(function (d, i) { var base = 0, x0 = L + i * step + (step - bw) / 2; SETTINGS.forEach(function (s) { var v = Math.max(0, d[s]); if (!v) return; inner += '<rect x="' + x0 + '" y="' + y(base + v) + '" width="' + bw + '" height="' + (y(base) - y(base + v)) + '" fill="' + COLORS[s] + '"><title>' + d.m + " " + s + ": " + fmt(d[s]) + "</title></rect>"; base += v; }); if (i % 6 === 0) inner += '<text x="' + (x0 + bw / 2) + '" y="' + (H - 10) + '" class="axis" text-anchor="middle">' + d.m + "</text>"; });
    return svg(W, H, label, inner) + '<div class="legend">' + SETTINGS.map(function (s) { return '<span><i style="background:' + COLORS[s] + '"></i>' + s + "</span>"; }).join("") + "</div>";
  }
  function lineMonthly(label) {
    var months = Array.from(new Set(D.monthly_utilization.map(function (r) { return r.year_month; }))).sort();
    var vals = months.map(function (m) { var rows = D.monthly_utilization.filter(function (r) { return r.year_month === m; }); var members = rows[0].members, claims = rows.reduce(function (s, r) { return s + r.claims; }, 0); return members ? claims * 1000 / members : null; });
    var W = 760, H = 220, L = 64, R = 12, T = 12, B = 30, hi = Math.max.apply(null, vals.filter(function (v) { return v !== null; })), tk = ticks(0, hi, 4); hi = Math.max(hi, tk[tk.length - 1]);
    var x = scale(0, vals.length - 1, L, W - R), y = scale(0, hi, H - B, T), inner = "";
    tk.forEach(function (t) { inner += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(t) + '" y2="' + y(t) + '" class="grid"/><text x="' + (L - 6) + '" y="' + (y(t) + 4) + '" class="axis" text-anchor="end">' + num(t) + "</text>"; });
    inner += '<path d="' + vals.map(function (v, i) { return v === null ? "" : (i ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); }).join("") + '" class="line"/>';
    months.forEach(function (m, i) { if (i % 6 === 0) inner += '<text x="' + x(i) + '" y="' + (H - 10) + '" class="axis" text-anchor="middle">' + m + "</text>"; if (vals[i] !== null) inner += '<circle cx="' + x(i) + '" cy="' + y(vals[i]) + '" r="7" class="hit"><title>' + m + ": " + num(vals[i], 0) + " claims per 1,000 members</title></circle>"; });
    return svg(W, H, label, inner);
  }

  function pageExecutive() {
    var r = yearRow(state.year), conc = D.payment_concentration.filter(function (c) { return c.year === state.year; })[0];
    return '<div class="controls">' + sel("f-year", "Year", YEARS.map(function (y) { return [y, y]; }), state.year) + "</div>" +
      '<div class="cards">' +
      card("Beneficiaries", num(r.beneficiaries), num(r.member_years, 0) + " member-years", "Synthetic beneficiary summary rows in the year") +
      card("Claims", num(r.claims), num(r.claims_per_1000_member_years) + " per 1,000 member-years", "Analytic claims across inpatient, outpatient and carrier") +
      card("Paid amount", usd(r.payment_total), "CLM_PMT_AMT + LINE_NCH_PMT_AMT", "Medicare trust fund payment, synthetic. Not a cost or charge.") +
      card("Paid per beneficiary", usd(r.payment_per_beneficiary, 0), "includes beneficiaries with no claims", "Paid amount / beneficiaries") +
      card("Admissions per 1,000", num(r.admissions_per_1000_member_years), num(r.admissions) + " continuous stays", "Inpatient stays / member-years x 1,000") +
      card("30-day readmission proxy", pct(r.readmission_rate), num(r.readmission_events) + " of " + num(r.readmission_eligible_index) + " index stays", "Measure-inspired proxy, not a certified measure") +
      card("Top 5% payment share", pct(conc.top_share), num(conc.top_count) + " of " + num(conc.beneficiaries) + " beneficiaries", "Share of paid amount held by the highest-paid 5 percent") + "</div>" +
      '<div class="panel wide"><h2>Monthly paid amount by care setting ' + tag("fact", "Synthetic sample") + "</h2>" + stackedMonthly("payment_amount", usd, "Monthly paid amount by care setting") +
      '<p class="note">Payment adjustments (negative amounts) are included in totals but not drawn below zero. Monthly claim volume in the synthetic source tapers from mid-2009 onward, so year-over-year and monthly trends are not interpretable.</p></div>' +
      '<div class="panel wide"><h2>Claims per 1,000 members, monthly ' + tag("fact", "Synthetic sample") + "</h2>" + lineMonthly("Monthly claims per 1,000 members") + "</div>";
  }

  function pageUtilization() {
    var ann = D.annual_by_setting.filter(function (r) { return r.year === state.year; });
    var totalClaims = ann.reduce(function (s, r) { return s + r.claims; }, 0), totalPay = ann.reduce(function (s, r) { return s + r.payment_amount; }, 0);
    var demo = D.demographic_summary.filter(function (r) { return r.year === state.year && (state.sex === "all" || r.sex === state.sex) && (state.race === "all" || r.race === state.race) && (state.age === "all" || r.age_band === state.age); });
    var agg = demo.reduce(function (a, r) { a.b += r.beneficiaries; a.mm += r.member_months; a.c += r.claims; a.p += r.payment_amount; a.ad += r.admissions; return a; }, { b: 0, mm: 0, c: 0, p: 0, ad: 0 });
    var uniq = function (k) { return Array.from(new Set(D.demographic_summary.map(function (r) { return r[k]; }))).sort(); };
    var conds = D.condition_summary.filter(function (r) { return r.year === state.year && r.condition_type === "primary_diagnosis_ccs" && (state.setting === "all" || r.setting === state.setting); });
    var byCond = {}; conds.forEach(function (r) { var k = r.condition_id; var o = byCond[k] || (byCond[k] = { name: r.condition_name, claims: 0, payment: 0, bene: 0 }); o.claims += r.claims; o.payment += r.payment_amount; o.bene = Math.max(o.bene, r.beneficiaries); });
    var list = Object.keys(byCond).map(function (k) { return byCond[k]; }).sort(function (a, b) { return b.payment - a.payment; }).slice(0, 15);
    var chronic = D.condition_summary.filter(function (r) { return r.year === state.year && r.condition_type === "chronic_condition_flag"; }).sort(function (a, b) { return b.prevalence - a.prevalence; });
    var mixRows = ann.map(function (r) { return '<tr><td>' + esc(r.setting) + '</td><td class="num">' + pct(r.claims / totalClaims) + '</td><td class="num">' + pct(r.payment_amount / totalPay) + '</td><td class="num">' + num(r.claims) + '</td><td class="num">' + usd(r.payment_amount) + '</td><td class="num">' + usd(r.payment_per_claim, 0) + "</td></tr>"; }).join("");
    return '<div class="controls">' + sel("f-year", "Year", YEARS.map(function (y) { return [y, y]; }), state.year) +
      sel("f-setting", "Care setting (conditions)", ["all"].concat(SETTINGS), state.setting) + sel("f-sex", "Sex", ["all"].concat(uniq("sex")), state.sex) +
      sel("f-race", "Race", ["all"].concat(uniq("race")), state.race) + sel("f-age", "Age band", ["all"].concat(uniq("age_band")), state.age) + "</div>" +
      '<div class="panel wide"><h2>Setting mix, ' + state.year + '</h2><div class="table-wrap"><table><thead><tr><th scope="col">Setting</th><th class="num" scope="col">Share of claims</th><th class="num" scope="col">Share of paid amount</th><th class="num" scope="col">Claims</th><th class="num" scope="col">Paid amount</th><th class="num" scope="col">Paid per claim</th></tr></thead><tbody>' + mixRows + "</tbody></table></div>" +
      '<p class="note">Denominator for shares: all analytic claims and all paid amount in the year across the three settings.</p></div>' +
      '<div class="panel wide"><h2>Demographic slice ' + tag("fact", "Synthetic sample") + "</h2>" + table(["Beneficiaries", "Claims", "Paid amount", "Paid per beneficiary", "Admissions per 1,000 member-years"], [[num(agg.b), num(agg.c), usd(agg.p), usd(agg.b ? agg.p / agg.b : null, 0), num(agg.mm ? agg.ad * 12000 / agg.mm : null)]], [0, 1, 2, 3, 4]) +
      '<p class="note">Filters combine. Rates use member months of the filtered beneficiaries as the denominator.</p></div>' +
      '<div class="panel wide"><h2>Top conditions by paid amount, primary diagnosis (AHRQ CCS) ' + tag("fact", "Synthetic sample") + "</h2>" + table(["Condition", "Claims", "Beneficiaries", "Paid amount"], list.map(function (c) { return [esc(c.name), num(c.claims), num(c.bene), usd(c.payment)]; }), [1, 2, 3]) +
      '<p class="note">Beneficiary counts are the largest single-setting count when a setting filter is "all". Grouping: AHRQ CCS 2015 for ICD-9-CM.</p></div>' +
      '<div class="panel wide"><h2>Chronic condition flags, share of beneficiaries</h2>' + table(["Condition flag", "Beneficiaries with flag", "Denominator", "Prevalence"], chronic.map(function (c) { return [esc(c.condition_name), num(c.beneficiaries), num(c.denominator_beneficiaries), pct(c.prevalence)]; }), [1, 2, 3]) + "</div>";
  }

  function pageProviders() {
    var rows = D.provider_review_facility.filter(function (r) { return r.year === state.year && r.provider_type === state.ptype; }).map(function (r) {
      var f1 = r.peer_count >= D.meta.peer_min && r.claims >= D.meta.min_claims && r.payment_per_claim_q3 > r.payment_per_claim_q1 && r.payment_per_claim > r.payment_per_claim_q3 + state.iqr * (r.payment_per_claim_q3 - r.payment_per_claim_q1);
      var f2 = r.peer_count >= D.meta.peer_min && r.claims >= D.meta.min_claims && r.claims_q3 > r.claims_q1 && r.claims > r.claims_q3 + state.iqr * (r.claims_q3 - r.claims_q1);
      return Object.assign({}, r, { flagged: f1 || f2, reasons: (f1 ? ["HIGH_PAYMENT_PER_CLAIM"] : []).concat(f2 ? ["HIGH_CLAIM_VOLUME"] : []) });
    });
    var flagged = rows.filter(function (r) { return r.flagged; }).sort(function (a, b) { return b.payment_amount - a.payment_amount; });
    var W = 760, H = 300, L = 70, R = 16, T = 14, B = 40, xs = rows.map(function (r) { return Math.log10(Math.max(1, r.claims)); }), ys = rows.map(function (r) { return r.payment_per_claim; });
    var xhi = Math.max.apply(null, xs.concat([1])), yhi = Math.max.apply(null, ys.concat([1])), x = scale(0, xhi, L, W - R), yy = scale(0, yhi, H - B, T), inner = "";
    ticks(0, yhi, 4).forEach(function (t) { inner += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + yy(t) + '" y2="' + yy(t) + '" class="grid"/><text x="' + (L - 6) + '" y="' + (yy(t) + 4) + '" class="axis" text-anchor="end">' + usd(t) + "</text>"; });
    [1, 10, 100, 1000, 10000].forEach(function (t) { if (Math.log10(t) <= xhi) inner += '<text x="' + x(Math.log10(t)) + '" y="' + (H - 22) + '" class="axis" text-anchor="middle">' + num(t) + "</text>"; });
    inner += '<text x="' + (W / 2) + '" y="' + (H - 4) + '" class="axis" text-anchor="middle">Claims (log scale)</text>';
    rows.forEach(function (r, i) { inner += '<circle data-provider="' + esc(r.provider_id) + '" cx="' + x(xs[i]) + '" cy="' + yy(ys[i]) + '" r="' + (r.flagged ? 5 : 3) + '" fill="' + (r.flagged ? "var(--c4)" : "var(--c1)") + '" fill-opacity="' + (r.flagged ? 0.95 : 0.35) + '" tabindex="0"><title>' + esc(r.provider_id) + ": " + num(r.claims) + " claims, " + usd(r.payment_per_claim, 0) + " per claim</title></circle>"; });
    var detail = "";
    if (state.provider) {
      var h = D.provider_review_facility.filter(function (r) { return r.provider_id === state.provider; }).sort(function (a, b) { return a.year - b.year; });
      detail = '<div class="panel wide"><h2>Provider drill-through: ' + esc(state.provider) + ' (synthetic ID)</h2>' + table(["Year", "Claims", "Beneficiaries", "Paid amount", "Paid per claim", "Peer count"], h.map(function (r) { return [r.year, num(r.claims), num(r.beneficiaries), usd(r.payment_amount), usd(r.payment_per_claim, 0), num(r.peer_count)]; }), [1, 2, 3, 4, 5]) + '<p class="note">Facilities show institutional claims (inpatient and outpatient). No specialty or geography exists in the source.</p></div>';
    }
    return '<div class="box warn"><strong>Review flags only.</strong> A flag means a facility sits above the interquartile fence of its peers. It is not evidence of fraud, poor quality or provider performance, and every provider ID is synthetic.</div>' +
      '<div class="controls">' + sel("f-year", "Year", YEARS.map(function (y) { return [y, y]; }), state.year) + sel("f-ptype", "Peer group", [["facility_inpatient", "Inpatient facilities"], ["facility_outpatient", "Outpatient facilities"]], state.ptype) +
      '<label class="range">Outlier threshold: Q3 + <output id="iqr-out">' + state.iqr.toFixed(1) + '</output> x IQR<input id="f-iqr" type="range" min="0.5" max="5" step="0.1" value="' + state.iqr + '" aria-label="IQR multiplier"></label>' +
      sel("f-topn", "Top N in list", [5, 10, 25, 50], state.topN) + "</div>" +
      '<div class="panel wide"><h2>Facility volume versus payment per claim, ' + state.year + ' (' + state.ptype.replace('facility_', '') + ' peers)</h2>' + svg(W, H, "Scatter of facility claims versus paid amount per claim", inner) +
      '<p class="note">Highlighted points are review flags at this threshold (minimum ' + D.meta.min_claims + " claims and " + D.meta.peer_min + " peers). On this synthetic data, volume flags mostly track facility size and payment-per-claim flags are rare, because CMS synthesized payments in a narrow range. Select a point or a row to drill through.</p></div>" +
      '<div class="panel wide"><h2>Review list, top ' + state.topN + " of " + flagged.length + " flagged facilities</h2>" + (flagged.length ? table(["Facility (synthetic ID)", "Claims", "Paid amount", "Paid per claim", "Reason codes"], flagged.slice(0, state.topN).map(function (r) { return ['<button type="button" class="link" data-provider="' + esc(r.provider_id) + '">' + esc(r.provider_id) + "</button>", num(r.claims), usd(r.payment_amount), usd(r.payment_per_claim, 0), esc(r.reasons.join(", "))]; }), [1, 2, 3]) : '<div class="empty">No facility is flagged at this threshold.</div>') + "</div>" + detail;
  }

  function pageQuality() {
    var rd = D.readmission_review.filter(function (r) { return r.year === state.year; });
    var tiers = D.risk_tier_summary.filter(function (r) { return r.year === state.year; });
    var conc = D.payment_concentration;
    var totalB = tiers.reduce(function (s, r) { return s + r.beneficiaries; }, 0), totalP = tiers.reduce(function (s, r) { return s + r.payment_amount; }, 0);
    return '<div class="controls">' + sel("f-year", "Year", YEARS.map(function (y) { return [y, y]; }), state.year) + "</div>" +
      '<div class="box note"><strong>Definitions.</strong> Index stay: valid dates, beneficiary did not die between admission and discharge, and a full 30-day follow-up before the study ends. Readmission: another stay beginning after the index discharge within 30 days. A measure-inspired proxy, not a certified measure; 2010 follow-up is truncated.</div>' +
      '<div class="panel wide"><h2>Readmission proxy by utilization risk tier, ' + state.year + ' ' + tag("model", "Descriptive proxy") + "</h2>" + table(["Risk tier", "Eligible index stays", "Readmitted", "Rate", "Excluded: died in stay", "Excluded: no follow-up window"], rd.map(function (r) { return [esc(r.utilization_risk_tier), num(r.eligible_index_stays), num(r.readmitted_stays), pct(r.readmission_rate), num(r.excluded_died_in_stay), num(r.excluded_insufficient_followup)]; }), [1, 2, 3, 4, 5]) + "</div>" +
      '<div class="panel wide"><h2>Utilization risk tiers, ' + state.year + ' ' + tag("model", "Descriptive stratification") + "</h2>" + table(["Tier", "Beneficiaries", "Share", "Paid per beneficiary", "Share of paid amount", "Admissions per 1,000 member-years"], tiers.map(function (r) { return [esc(r.utilization_risk_tier), num(r.beneficiaries), pct(r.beneficiaries / totalB), usd(r.payment_per_beneficiary, 0), pct(r.payment_amount / totalP), num(r.admissions_per_1000_member_years)]; }), [1, 2, 3, 4, 5]) +
      '<p class="note">Tier points use prior-year chronic condition flags, admissions and paid amount only. Not CMS-HCC, RAF or official risk adjustment. The first study year has no prior year, so its beneficiaries are not assessed.</p></div>' +
      '<div class="panel wide"><h2>Payment concentration</h2>' + table(["Year", "Beneficiaries", "Top 5% group", "Paid by top group", "Total paid", "Share"], conc.map(function (c) { return [c.year, num(c.beneficiaries), num(c.top_count), usd(c.top_payment), usd(c.total_payment), pct(c.top_share)]; }), [1, 2, 3, 4, 5]) + "</div>";
  }

  function pageDefinitions() {
    var rec = D.reconciliation_results, blocking = rec.filter(function (r) { return r.blocking; }), passed = blocking.filter(function (r) { return r.passed; }).length;
    var ind = D.independent, indPassed = ind.filter(function (r) { return r.passed; }).length, q = D.data_quality;
    var defs = D.metric_dictionary.filter(function (m) { return !state.query || (m.name + " " + m.definition + " " + m.category).toLowerCase().indexOf(state.query.toLowerCase()) >= 0; });
    var dqRows = [["Exact duplicate rows dropped", q.counts.duplicate_rows_dropped], ["Impossible or missing dates", q.counts.invalid_date_claims], ["Dated outside the study window", q.counts.outside_study_window_claims], ["Negative payment claims (adjustments)", q.counts.negative_payment_claims], ["Multi-segment claims merged", q.counts.multi_segment_claims]];
    return '<div class="panel wide"><h2>Source and refresh</h2><ul class="tight"><li>' + esc(D.meta.source_name) + '. <a href="' + esc(D.meta.overview_url) + '">CMS overview</a>, <a href="' + esc(D.meta.codebook_url) + '">codebook</a>.</li><li>Retrieved ' + esc(D.meta.retrieved) + "; SHA-256 hashes in data/data_manifest.json. Diagnosis grouping: " + esc(D.meta.ccs_name) + ".</li><li>Synthetic data intended for development and training. It cannot estimate real Medicare rates, provider performance, savings or prevalence.</li></ul></div>" +
      '<div class="panel"><h2>Reconciliation</h2><p class="' + (passed === blocking.length ? "ok" : "bad") + '">' + passed + " of " + blocking.length + " blocking checks passed</p><p class=\"" + (indPassed === ind.length ? "ok" : "bad") + '">' + indPassed + " of " + ind.length + " independent pandas checks agree</p><p class=\"note\">Independent checks recompute claims, payments, admissions, ED proxy, readmission proxy and concentration from the raw CSV without SQL.</p></div>" +
      '<div class="panel"><h2>Data quality</h2>' + table(["Check", "Inpatient", "Outpatient", "Carrier"], dqRows.map(function (r) { return [esc(r[0]), num(r[1].inpatient), num(r[1].outpatient), num(r[1].carrier)]; }), [1, 2, 3]) + "</div>" +
      '<div class="panel wide"><h2>Reconciliation checks</h2>' + table(["Check", "Category", "Expected", "Actual", "Blocking", "Result"], rec.map(function (r) { return [esc(r.check_name), esc(r.category), r.expected === null ? "n/a" : num(r.expected, 2), num(r.actual, 2), r.blocking ? "yes" : "no", '<span class="' + (r.passed ? "ok" : "bad") + '">' + (r.passed ? "pass" : "differs") + "</span>"]; }), [2, 3]) +
      '<p class="note">Rows marked informational tie the beneficiary summary MEDREIMB fields to claim payments. They differ in the source and are not used in any metric.</p></div>' +
      '<div class="controls"><label>Search definitions<input id="f-query" type="search" placeholder="e.g. readmission" value="' + esc(state.query) + '"></label></div>' +
      '<div class="panel wide"><h2>Metric definitions</h2>' + table(["Metric", "Definition", "Source fields", "Caveat"], defs.map(function (m) { return [esc(m.name), esc(m.definition), esc(m.source_fields), esc(m.caveat)]; })) + "</div>";
  }

  function render() {
    document.getElementById("view").innerHTML = { executive: pageExecutive, utilization: pageUtilization, providers: pageProviders, quality: pageQuality, definitions: pageDefinitions }[state.tab]();
    document.querySelectorAll("[data-tab]").forEach(function (t) { var on = t.getAttribute("data-tab") === state.tab; t.setAttribute("aria-selected", on ? "true" : "false"); t.tabIndex = on ? 0 : -1; });
    document.getElementById("status").textContent = "Years " + YEARS[0] + " to " + YEARS[YEARS.length - 1] + ".";
  }
  function set(p) { Object.keys(p).forEach(function (k) { state[k] = p[k]; }); var a = document.activeElement && document.activeElement.id; render(); if (a) { var el = document.getElementById(a); if (el) { el.focus(); if (el.type === "search") { var n = el.value.length; el.setSelectionRange(n, n); } } } }
  document.addEventListener("change", function (ev) { var t = ev.target, m = { "f-year": function () { set({ year: parseInt(t.value, 10) }); }, "f-setting": function () { set({ setting: t.value }); }, "f-sex": function () { set({ sex: t.value }); }, "f-race": function () { set({ race: t.value }); }, "f-age": function () { set({ age: t.value }); }, "f-topn": function () { set({ topN: parseInt(t.value, 10) }); }, "f-ptype": function () { set({ ptype: t.value, provider: null }); } }; if (m[t.id]) m[t.id](); });
  document.addEventListener("input", function (ev) { var t = ev.target; if (t.id === "f-iqr") set({ iqr: parseFloat(t.value) }); else if (t.id === "f-query") set({ query: t.value }); });
  document.addEventListener("click", function (ev) { var t = ev.target.closest("[data-tab], [data-provider]"); if (!t) return; if (t.hasAttribute("data-tab")) set({ tab: t.getAttribute("data-tab") }); else set({ provider: t.getAttribute("data-provider") }); });
  document.addEventListener("keydown", function (ev) { var t = ev.target; if (t.hasAttribute && t.hasAttribute("data-tab") && (ev.key === "ArrowRight" || ev.key === "ArrowLeft")) { var i = TABS.findIndex(function (x) { return x[0] === state.tab; }), n = (i + (ev.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length; set({ tab: TABS[n][0] }); document.getElementById("tab-" + TABS[n][0]).focus(); } else if (t.hasAttribute && t.hasAttribute("data-provider") && ev.key === "Enter") set({ provider: t.getAttribute("data-provider") }); });
  document.getElementById("tabs").innerHTML = TABS.map(function (t) { return '<button type="button" role="tab" id="tab-' + t[0] + '" data-tab="' + t[0] + '" aria-selected="false">' + t[1] + "</button>"; }).join("");
  var hash = (location.hash || "").replace("#", ""); if (TABS.some(function (t) { return t[0] === hash; })) state.tab = hash;
  window.__state = state; window.__set = set;
  render();
})();
