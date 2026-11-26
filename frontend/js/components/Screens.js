import {
  ActivityIcon,
  AlertIcon,
  ClockIcon,
  ConfirmIcon,
  DownloadIcon,
  PrintIcon,
  QrIcon,
  ScanIcon,
  SearchIcon,
  ShieldIcon,
} from "../icons.js";
import {
  PRESET_SCANS,
  buildQrPassPayload,
  findDefaultRuleForMedication,
  formatTimeDelta,
  getFoodDisplayName,
} from "../clinicalEngine.js";
import { AbsorptionChart } from "./AbsorptionChart.js";
import { AudioReminderPlayer } from "./AudioReminderPlayer.js";

const { useMemo, useState } = window.React;
const html = window.htm.bind(window.React.createElement);

function QrSvg({ payloadString }) {
  const svgData = useMemo(() => {
    if (!window.qrcode) return null;
    const qr = window.qrcode(0, "M");
    qr.addData(payloadString);
    qr.make();
    const count = qr.getModuleCount();
    const cells = [];
    for (let r = 0; r < count; r += 1) {
      for (let c = 0; c < count; c += 1) {
        if (qr.isDark(r, c)) {
          cells.push(`M${c},${r}h1v1h-1z`);
        }
      }
    }
    return {
      count,
      pathD: cells.join(""),
    };
  }, [payloadString]);

  if (!svgData) {
    return html`<div class="stat-meta mono">QR module initializing</div>`;
  }

  const quiet = 2;
  const vbSize = svgData.count + quiet * 2;
  return html`
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox=${`-${quiet} -${quiet} ${vbSize} ${vbSize}`}
      shape-rendering="crispEdges"
      role="img"
      aria-label="Aahar-Rx QR Health Pass"
    >
      <rect x=${-quiet} y=${-quiet} width=${vbSize} height=${vbSize} fill="#ffffff" />
      <path d=${svgData.pathD} fill="#1f1b16" />
    </svg>
  `;
}

export function ScanScreen({
  t,
  lang,
  consented,
  onToggleConsent,
  brands,
  scanState,
  onSelectPreset,
  onSelectManualBrand,
  onChangeDoseTime,
  onChangeMealSlot,
  onProceedToConfirm,
  bridgeOnline,
  onUploadFileScan,
}) {
  const [query, setQuery] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);

  const filteredBrands = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return brands.slice(0, 4);
    return brands
      .filter((b) => {
        const hay = [
          b.brand_name,
          ...(b.brand_aliases || []),
          ...(b.active_salts || []),
          ...(b.salt_aliases || []),
        ]
          .join(" ")
          .toLowerCase();
        return hay.includes(q);
      })
      .slice(0, 6);
  }, [query, brands]);

  async function handleFileChange(kind, event) {
    const file = event.target.files?.[0];
    if (!file || !consented) return;
    setUploadBusy(true);
    try {
      await onUploadFileScan(kind, file);
    } finally {
      setUploadBusy(false);
      event.target.value = "";
    }
  }

  return html`
    <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-24)" }}>
      <div class="screen-header">
        <div>
          <h1 class="screen-title">${t.scan.heading}</h1>
          <p class="screen-sub">${t.scan.subheading}</p>
        </div>
        <span class="tag ${bridgeOnline ? "safe" : ""}">
          <span class="status-dot ${bridgeOnline ? "" : "warn"}" />
          <span>${bridgeOnline ? t.scan.live_bridge_hint : t.scan.client_mode_hint}</span>
        </span>
      </div>

      <section class="consent-box ${consented ? "" : "pending"}" aria-label=${t.consent.title}>
        <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <div class="card-title" style=${{ fontSize: "var(--text-base)" }}>
            <span class="icon-box"><${ShieldIcon} /></span>
            <span>${t.consent.title}</span>
          </div>
          <span class="tag ${consented ? "safe" : "moderate"}">
            ${consented ? t.consent.status_granted : t.consent.status_required}
          </span>
        </div>
        <p style=${{ margin: 0, fontSize: "var(--text-sm)", color: "var(--text-secondary)" }}>
          ${t.consent.body}
        </p>
        <label class="check-row">
          <input
            type="checkbox"
            checked=${consented}
            onChange=${(e) => onToggleConsent(e.target.checked)}
          />
          <span style=${{ fontWeight: 500, fontSize: "var(--text-sm)" }}>${t.consent.checkbox}</span>
        </label>
      </section>

      <div class="card">
        <div class="card-title">
          <span class="icon-box"><${ScanIcon} /></span>
          <span>${t.scan.preset_label}</span>
        </div>
        <div class="preset-grid">
          ${PRESET_SCANS.map((preset) => {
            const label = t.scan.presets[preset.id] || preset.id;
            const active = scanState.activePresetId === preset.id;
            return html`
              <button
                key=${preset.id}
                type="button"
                class="preset-btn ${active ? "selected" : ""}"
                onClick=${() => onSelectPreset(preset.id)}
              >
                <span class="preset-title">${label}</span>
                <span class="preset-meta mono">
                  ${preset.doseTimeHHMM} | ${preset.qualityOk ? "PASS" : "RETRY"}
                </span>
              </button>
            `;
          })}
        </div>
      </div>

      <div class="equal-grid-2">
        <div class="card">
          <div class="card-title">
            <span class="icon-box"><${ScanIcon} /></span>
            <span>${t.scan.strip_section}</span>
          </div>
          <img
            class="sample-strip-preview"
            src=${scanState.stripPreviewUrl}
            alt=${scanState.medication?.brand_name || "Medicine strip"}
          />
          <div class="btn-row">
            <label class="btn ${consented ? "" : "disabled"}" style=${{ position: "relative" }}>
              <span>${t.scan.upload_strip}</span>
              <input
                type="file"
                accept="image/*"
                disabled=${!consented || uploadBusy}
                onChange=${(e) => handleFileChange("strip", e)}
                style=${{ position: "absolute", inset: 0, opacity: 0, cursor: consented ? "pointer" : "not-allowed" }}
              />
            </label>
          </div>
          <div class="field">
            <label class="field-label" for="brand-search">${t.scan.search_placeholder}</label>
            <div style=${{ position: "relative", display: "flex", alignItems: "center" }}>
              <span class="icon-box" style=${{ position: "absolute", left: "12px", pointerEvents: "none" }}>
                <${SearchIcon} />
              </span>
              <input
                id="brand-search"
                class="input"
                style=${{ paddingLeft: "36px" }}
                type="text"
                value=${query}
                onInput=${(e) => setQuery(e.target.value)}
                placeholder=${t.scan.search_placeholder}
              />
            </div>
          </div>
          <div class="item-list">
            ${filteredBrands.map((b) => {
              const selected = scanState.medication?.brand_id === b.brand_id;
              return html`
                <button
                  key=${b.brand_id}
                  type="button"
                  class="list-row list-row-button ${selected ? "selected" : ""}"
                  style=${selected ? { borderColor: "var(--accent)", backgroundColor: "var(--accent-tint)" } : {}}
                  onClick=${() => onSelectManualBrand(b)}
                >
                  <div>
                    <div style=${{ fontWeight: 500, fontSize: "var(--text-sm)" }}>${b.brand_name}</div>
                    <div class="stat-meta">${(b.active_salts || []).join(", ")}</div>
                  </div>
                  <span class="tag mono">${b.common_strengths?.[0] || b.drug_class}</span>
                </button>
              `;
            })}
          </div>
        </div>

        <div class="card">
          <div class="card-title">
            <span class="icon-box"><${ClockIcon} /></span>
            <span>${t.scan.meal_section}</span>
          </div>
          <img
            class="sample-strip-preview"
            src=${scanState.mealPreviewUrl}
            alt="Meal capture preview"
          />
          <div class="btn-row">
            <label class="btn ${consented ? "" : "disabled"}" style=${{ position: "relative" }}>
              <span>${t.scan.upload_meal}</span>
              <input
                type="file"
                accept="image/*"
                disabled=${!consented || uploadBusy}
                onChange=${(e) => handleFileChange("meal", e)}
                style=${{ position: "absolute", inset: 0, opacity: 0, cursor: consented ? "pointer" : "not-allowed" }}
              />
            </label>
          </div>
          <div class="equal-grid-2">
            <div class="field">
              <label class="field-label" for="dose-time">${t.scan.dose_time_label}</label>
              <input
                id="dose-time"
                class="input mono"
                type="time"
                value=${scanState.doseTimeHHMM}
                onChange=${(e) => onChangeDoseTime(e.target.value)}
              />
            </div>
            <div class="field">
              <label class="field-label" for="meal-slot">${t.scan.meal_slot_label}</label>
              <select
                id="meal-slot"
                class="select"
                value=${scanState.mealSlot}
                onChange=${(e) => onChangeMealSlot(e.target.value)}
              >
                ${Object.entries(t.meal_slots).map(
                  ([slotKey, slotLabel]) => html`<option key=${slotKey} value=${slotKey}>${slotLabel}</option>`
                )}
              </select>
            </div>
          </div>

          <div style=${{ marginTop: "auto", paddingTop: "var(--space-12)" }}>
            <button
              type="button"
              class="btn btn-primary"
              style=${{ width: "100%" }}
              disabled=${!consented || uploadBusy}
              onClick=${onProceedToConfirm}
            >
              <span class="icon-box" style=${{ color: "#ffffff" }}><${ConfirmIcon} /></span>
              <span>${t.scan.run_scan}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function ConfirmScreen({
  t,
  lang,
  foods,
  scanState,
  resolvedFoods,
  onToggleMilk,
  onRemoveFood,
  onAddFood,
  onConfirmBundle,
  onBackToScan,
}) {
  const [selectedAddFood, setSelectedAddFood] = useState(foods?.[0]?.canonical_food_id || "chai_with_milk");
  const hasChai = scanState.foodIds.includes("chai_with_milk");

  return html`
    <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-24)" }}>
      <div class="screen-header">
        <div>
          <h1 class="screen-title">${t.confirm.heading}</h1>
          <p class="screen-sub">${t.confirm.subheading}</p>
        </div>
        <span class="tag ${scanState.confirmedByUser ? "safe" : "moderate"}">
          ${scanState.confirmedByUser ? t.confirm.confirmed_badge : t.confirm.pending_badge}
        </span>
      </div>

      ${!scanState.qualityOk
        ? html`
            <div class="alert-banner" role="alert">
              <div class="alert-banner-title">
                <span class="icon-box" style=${{ color: "var(--semantic-high)" }}><${AlertIcon} /></span>
                <span>${t.confirm.quality_retry}</span>
              </div>
              <p style=${{ margin: 0, fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>
                ${scanState.retryGuidance || t.confirm.retry_guidance}
              </p>
              <div class="btn-row">
                <button type="button" class="btn btn-primary" onClick=${onBackToScan}>
                  ${t.confirm.retry_action}
                </button>
              </div>
            </div>
          `
        : html`
            <div class="list-row" style=${{ backgroundColor: "var(--bg-card)" }}>
              <div style=${{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span class="status-dot" />
                <span style=${{ fontWeight: 500, fontSize: "var(--text-sm)" }}>${t.confirm.quality_pass}</span>
              </div>
              <span class="tag safe mono">DPDP: raw_images_retained = false</span>
            </div>
          `}

      <div class="split-grid">
        <div class="card">
          <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px" }}>
            <h2 class="card-title">${t.confirm.meal_card_title}</h2>
            <span class="stat-meta mono">${resolvedFoods.length} items</span>
          </div>

          <div class="item-list">
            ${resolvedFoods.map((item) => {
              const name = getFoodDisplayName(item, lang);
              return html`
                <div key=${item.canonical_food_id} class="list-row">
                  <div style=${{ minWidth: 0 }}>
                    <div style=${{ fontWeight: 500 }}>${name}</div>
                    <div class="stat-meta mono">
                      ${(item.interfering_nutrients || []).join(", ") || "low-risk"}
                    </div>
                  </div>
                  <div class="btn-row" style=${{ gap: "8px" }}>
                    <span class="tag">${item.portion_hint || "1 serving"}</span>
                    ${resolvedFoods.length > 1
                      ? html`
                          <button
                            type="button"
                            class="btn"
                            style=${{ minHeight: "32px", padding: "4px 10px" }}
                            onClick=${() => onRemoveFood(item.canonical_food_id)}
                          >
                            Remove
                          </button>
                        `
                      : null}
                  </div>
                </div>
              `;
            })}
          </div>

          ${hasChai
            ? html`
                <div class="audio-box">
                  <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                    <div>
                      <div style=${{ fontWeight: 500, fontSize: "var(--text-sm)" }}>${t.confirm.milk_toggle}</div>
                      <div class="stat-meta">
                        ${scanState.milkInChai ? t.confirm.milk_on : t.confirm.milk_off}
                      </div>
                    </div>
                    <button
                      type="button"
                      class="btn ${scanState.milkInChai ? "btn-primary" : ""}"
                      onClick=${() => onToggleMilk(!scanState.milkInChai)}
                    >
                      ${scanState.milkInChai ? "Milk: ON" : "Milk: OFF"}
                    </button>
                  </div>
                </div>
              `
            : null}

          <div class="field">
            <label class="field-label" for="add-food-select">${t.confirm.add_dish}</label>
            <div style=${{ display: "flex", gap: "8px" }}>
              <select
                id="add-food-select"
                class="select"
                value=${selectedAddFood}
                onChange=${(e) => setSelectedAddFood(e.target.value)}
              >
                ${foods.map(
                  (f) => html`
                    <option key=${f.canonical_food_id} value=${f.canonical_food_id}>
                      ${getFoodDisplayName(f, lang)}${lang === "en" ? "" : ` (${f.display_name})`}
                    </option>
                  `
                )}
              </select>
              <button type="button" class="btn" onClick=${() => onAddFood(selectedAddFood)}>
                ${t.confirm.add_button}
              </button>
            </div>
          </div>
        </div>

        <div class="card">
          <h2 class="card-title">${t.confirm.med_card_title}</h2>
          <div class="list-row" style=${{ backgroundColor: "var(--bg-page)", flexDirection: "column", alignItems: "flex-start" }}>
            <div style=${{ fontSize: "20px", fontWeight: 600 }}>${scanState.medication.brand_name}</div>
            <div class="stat-meta">${(scanState.medication.active_salts || []).join(" + ")}</div>
          </div>
          <div class="item-list">
            <div class="list-row">
              <span class="stat-meta">${t.confirm.med_strength}</span>
              <span class="mono" style=${{ fontWeight: 500 }}>${scanState.medication.strength_text || "Standard"}</span>
            </div>
            <div class="list-row">
              <span class="stat-meta">${t.confirm.med_class}</span>
              <span class="tag">${scanState.medication.drug_class}</span>
            </div>
            <div class="list-row">
              <span class="stat-meta">${t.scan.dose_time_label}</span>
              <span class="mono" style=${{ fontWeight: 500 }}>${scanState.doseTimeHHMM}</span>
            </div>
          </div>

          <button
            type="button"
            class="btn btn-primary"
            style=${{ width: "100%", marginTop: "var(--space-8)" }}
            onClick=${onConfirmBundle}
          >
            <span class="icon-box" style=${{ color: "#ffffff" }}><${ConfirmIcon} /></span>
            <span>${t.confirm.confirm_cta}</span>
          </button>
        </div>
      </div>
    </div>
  `;
}

export function TimetableScreen({
  t,
  lang,
  scanState,
  interactions,
  selectedSwaps,
  onSelectSwap,
  voiceScripts,
  onOpenCurve,
  onOpenQrPass,
}) {
  const primary = interactions[0] || null;
  const primaryRule = primary?.rule || null;
  const beforeH = primaryRule?.safe_time_gap_hours?.before_food_hours ?? 0;
  const afterH = primaryRule?.safe_time_gap_hours?.after_food_hours ?? 0;
  const dropPct = primaryRule?.absorption_impact?.bioavailability_drop_pct ?? 0;
  const doseHour = Number((scanState.doseTimeHHMM || "07:00").split(":")[0]);
  const blockedSpan = Math.max(1, Math.round(beforeH));
  const safeStartHHMM = formatTimeDelta(scanState.doseTimeHHMM, beforeH);

  return html`
    <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-24)" }}>
      <div class="screen-header">
        <div>
          <h1 class="screen-title">${t.timetable.heading}</h1>
          <p class="screen-sub">${t.timetable.subheading}</p>
        </div>
        <div class="btn-row">
          <button type="button" class="btn" onClick=${() => onOpenCurve(primaryRule?.rule_id)}>
            <span class="icon-box"><${ActivityIcon} /></span>
            <span>${t.timetable.open_curve}</span>
          </button>
          <button type="button" class="btn btn-primary" onClick=${onOpenQrPass}>
            <span class="icon-box" style=${{ color: "#ffffff" }}><${QrIcon} /></span>
            <span>${t.nav.qr_pass}</span>
          </button>
        </div>
      </div>

      <div class="stats-row">
        <div class="card card-compact">
          <span class="stat-label">${t.timetable.summary_conflicts}</span>
          <span class="stat-value ${interactions.length ? "danger" : "accent"}">${interactions.length}</span>
          <span class="stat-meta">${scanState.medication.brand_name}</span>
        </div>
        <div class="card card-compact">
          <span class="stat-label">${t.timetable.summary_safe_gap}</span>
          <span class="stat-value mono">${beforeH}h / ${afterH}h</span>
          <span class="stat-meta">${beforeH} ${t.timetable.before_food}</span>
        </div>
        <div class="card card-compact">
          <span class="stat-label">${t.timetable.summary_impact}</span>
          <span class="stat-value ${dropPct ? "danger" : ""} mono">
            ${dropPct > 0 ? `-${dropPct}%` : dropPct < 0 ? `+${Math.abs(dropPct)}%` : "0%"}
          </span>
          <span class="stat-meta">${primaryRule?.interaction_type || "Standard"}</span>
        </div>
      </div>

      ${primaryRule
        ? html`
            <div class="card">
              <div style=${{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
                <div>
                  <div class="card-title">${t.timetable.dose_at}: <span class="mono">${scanState.doseTimeHHMM}</span></div>
                  <div class="stat-meta">
                    ${t.timetable.safe_window}: <strong class="mono">${safeStartHHMM}+</strong>
                  </div>
                </div>
                <span class="tag ${primaryRule.severity === "HIGH" ? "high" : "moderate"}">
                  ${t.severity[primaryRule.severity] || primaryRule.severity}
                </span>
              </div>

              <div class="timeline-track" role="img" aria-label="24-hour dose and safe food timeline">
                ${Array.from({ length: 24 }, (_, hour) => {
                  const isDose = hour === doseHour;
                  const diff = (hour - doseHour + 24) % 24;
                  const isRestricted = !isDose && beforeH > 0 && diff > 0 && diff <= blockedSpan;
                  return html`
                    <div
                      key=${hour}
                      class="timeline-slot mono ${isDose ? "dose" : isRestricted ? "restricted" : ""}"
                      title=${`${String(hour).padStart(2, "0")}:00`}
                    >
                      ${String(hour).padStart(2, "0")}
                    </div>
                  `;
                })}
              </div>

              <div class="btn-row" style=${{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                <span class="tag safe">${t.timetable.dose_at} (${scanState.doseTimeHHMM})</span>
                <span class="tag high">${t.timetable.avoid_until} ${safeStartHHMM}</span>
                <span class="tag">${t.timetable.safe_window} (${safeStartHHMM}+)</span>
              </div>
            </div>

            <div class="split-grid">
              <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-16)" }}>
                ${interactions.map(({ rule, hitFoods }) => {
                  const selectedIdx = selectedSwaps[rule.rule_id] || 0;
                  return html`
                    <article key=${rule.rule_id} class="card">
                      <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                        <div>
                          <div class="card-title">${rule.drug_class}</div>
                          <div class="stat-meta mono">
                            ${rule.rule_id} | ${hitFoods.map((f) => getFoodDisplayName(f, lang)).join(", ")}
                          </div>
                        </div>
                        <span class="tag ${rule.severity === "HIGH" ? "high" : "moderate"}">
                          ${t.severity[rule.severity] || rule.severity}
                        </span>
                      </div>

                      <div>
                        <div class="field-label">${t.timetable.mechanism_label}</div>
                        <p style=${{ margin: "4px 0 0", fontSize: "var(--text-sm)", color: "var(--text-secondary)" }}>
                          ${rule.biochemical_mechanism}
                        </p>
                      </div>

                      <div>
                        <div class="field-label" style=${{ marginBottom: "8px" }}>${t.timetable.swaps_label}</div>
                        <div class="item-list">
                          ${(rule.ghar_ki_rasoi_swaps || []).map((swap, idx) => html`
                            <button
                              key=${idx}
                              type="button"
                              class="swap-card ${selectedIdx === idx ? "selected" : ""}"
                              onClick=${() => onSelectSwap(rule.rule_id, idx)}
                            >
                              <div style=${{ fontWeight: 500, fontSize: "var(--text-sm)", color: "var(--accent)" }}>
                                ${t.timetable.swap_use}: ${swap.substitute}
                              </div>
                              <div class="stat-meta">
                                ${t.timetable.swap_culprit}: ${swap.culprit}
                              </div>
                              <div class="stat-meta">${swap.dietary_rationale}</div>
                            </button>
                          `)}
                        </div>
                      </div>

                      <div>
                        <div class="field-label" style=${{ marginBottom: "4px" }}>${t.timetable.ifct_label}</div>
                        <table class="evidence-table">
                          <thead>
                            <tr>
                              <th>Food</th>
                              <th>Nutrient</th>
                              <th style=${{ textAlign: "right" }}>IFCT value</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${(rule.ifct_evidence || []).map((ev, eIdx) => html`
                              <tr key=${eIdx}>
                                <td>${ev.food}</td>
                                <td class="stat-meta">${ev.primary_nutrient}</td>
                                <td class="num">${ev.value}</td>
                              </tr>
                            `)}
                          </tbody>
                        </table>
                      </div>
                    </article>
                  `;
                })}
              </div>

              <div class="card">
                <${AudioReminderPlayer}
                  ruleId=${primaryRule.rule_id}
                  lang=${lang}
                  voiceScripts=${voiceScripts}
                  t=${t}
                />
              </div>
            </div>
          `
        : html`
            <div class="card">
              <div class="card-title">${t.timetable.no_conflict}</div>
              <p class="screen-sub">${t.brand.blind_notice}</p>
            </div>
          `}
    </div>
  `;
}

export function AbsorptionCurveScreen({
  t,
  lang,
  rules,
  pkProfiles,
  selectedRuleId,
  onSelectRule,
  voiceScripts,
}) {
  const activeRule = rules.find((r) => r.rule_id === selectedRuleId) || rules[0];
  const profile = pkProfiles[activeRule.rule_id];
  const isElevation = profile.curve_mode === "elevation_toxicity";
  const dropVal = profile.bioavailability_drop_pct;
  const shiftLabel = dropVal > 0 ? `-${dropVal.toFixed(1)}%` : `+${Math.abs(dropVal).toFixed(1)}%`;

  return html`
    <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-24)" }}>
      <div class="screen-header">
        <div>
          <h1 class="screen-title">${t.curve.heading}</h1>
          <p class="screen-sub">${t.curve.subheading}</p>
        </div>
        <span class="tag mono">${activeRule.rule_id}</span>
      </div>

      <div class="rule-pill-row" role="tablist" aria-label="Drug class absorption curve selector">
        ${rules.map((r) => {
          const active = r.rule_id === activeRule.rule_id;
          return html`
            <button
              key=${r.rule_id}
              type="button"
              role="tab"
              aria-selected=${active}
              class="rule-pill ${active ? "active" : ""}"
              onClick=${() => onSelectRule(r.rule_id)}
            >
              ${r.active_salts[0]}
            </button>
          `;
        })}
      </div>

      <div class="split-grid">
        <div class="card">
          <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <div>
              <h2 class="card-title">${activeRule.active_salts.join(" / ")}</h2>
              <div class="stat-meta">${activeRule.drug_class} — ${activeRule.interaction_type}</div>
            </div>
            <span class="tag ${activeRule.severity === "HIGH" ? "high" : "moderate"}">
              ${t.severity[activeRule.severity] || activeRule.severity}
            </span>
          </div>

          <${AbsorptionChart} profile=${profile} t=${t} />

          <p style=${{ margin: 0, fontSize: "var(--text-sm)", color: "var(--text-secondary)" }}>
            ${isElevation ? t.curve.elevation_note : t.curve.drop_note}
          </p>
        </div>

        <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-16)" }}>
          <div class="card">
            <div class="item-list">
              <div class="list-row">
                <span class="stat-meta">${t.curve.metric_drop}</span>
                <span class="mono" style=${{ fontWeight: 600, color: "var(--semantic-high)" }}>${shiftLabel}</span>
              </div>
              <div class="list-row">
                <span class="stat-meta">${t.curve.metric_tmax}</span>
                <span class="mono" style=${{ fontWeight: 500 }}>
                  ${profile.baseline_tmax_hours}h to ${profile.interfered_tmax_hours}h (+${profile.t_max_delay_hours}h)
                </span>
              </div>
              <div class="list-row">
                <span class="stat-meta">${t.curve.metric_gap}</span>
                <span class="mono" style=${{ fontWeight: 500 }}>
                  ${activeRule.safe_time_gap_hours.before_food_hours}h / ${activeRule.safe_time_gap_hours.after_food_hours}h
                </span>
              </div>
              <div class="list-row">
                <span class="stat-meta">12h AUC shift</span>
                <span class="mono" style=${{ fontWeight: 500 }}>
                  ${profile.auc_change_pct > 0 ? `+${profile.auc_change_pct}%` : `${profile.auc_change_pct}%`}
                </span>
              </div>
            </div>
          </div>

          <div class="card">
            <${AudioReminderPlayer}
              ruleId=${activeRule.rule_id}
              lang=${lang}
              voiceScripts=${voiceScripts}
              t=${t}
              title=${t.curve.listen_walkthrough}
            />
          </div>
        </div>
      </div>
    </div>
  `;
}

export function QrHealthPassScreen({
  t,
  lang,
  scanState,
  interactions,
  selectedSwaps,
  voiceScripts,
  bundleId,
}) {
  const [showJson, setShowJson] = useState(false);

  const payloadObj = useMemo(
    () =>
      buildQrPassPayload({
        bundleId,
        lang,
        medication: scanState.medication,
        doseTimeHHMM: scanState.doseTimeHHMM,
        interactions,
        selectedSwaps,
        disclaimer: t.brand.blind_notice,
      }),
    [bundleId, lang, scanState, interactions, selectedSwaps, t]
  );

  const payloadString = useMemo(() => JSON.stringify(payloadObj), [payloadObj]);
  const primaryRule = interactions[0]?.rule || null;

  function downloadSvg() {
    if (!window.qrcode) return;
    const qr = window.qrcode(0, "M");
    qr.addData(payloadString);
    qr.make();
    const count = qr.getModuleCount();
    const quiet = 2;
    const size = count + quiet * 2;
    let paths = "";
    for (let r = 0; r < count; r += 1) {
      for (let c = 0; c < count; c += 1) {
        if (qr.isDark(r, c)) paths += `M${c},${r}h1v1h-1z`;
      }
    }
    const svgText = `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="-${quiet} -${quiet} ${size} ${size}"><rect x="-${quiet}" y="-${quiet}" width="${size}" height="${size}" fill="#ffffff"/><path d="${paths}" fill="#1f1b16"/></svg>`;
    const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `aahar-rx-pass-${bundleId}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return html`
    <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-24)" }}>
      <div class="screen-header">
        <div>
          <h1 class="screen-title">${t.qr.heading}</h1>
          <p class="screen-sub">${t.qr.subheading}</p>
        </div>
        <div class="btn-row no-print">
          <button type="button" class="btn" onClick=${downloadSvg}>
            <span class="icon-box"><${DownloadIcon} /></span>
            <span>${t.qr.download_svg}</span>
          </button>
          <button type="button" class="btn btn-primary" onClick=${() => window.print()}>
            <span class="icon-box" style=${{ color: "#ffffff" }}><${PrintIcon} /></span>
            <span>${t.qr.print_pass}</span>
          </button>
        </div>
      </div>

      <section class="qr-pass-specimen" aria-label="1-Click QR Health Pass">
        <div class="qr-frame">
          <${QrSvg} payloadString=${payloadString} />
          <span class="mono" style=${{ fontSize: "11px", color: "var(--text-muted)" }}>
            ${bundleId}
          </span>
        </div>

        <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-16)", minWidth: 0 }}>
          <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap", borderBottom: "1px solid var(--border-hairline)", paddingBottom: "var(--space-12)" }}>
            <div>
              <div style=${{ fontSize: "20px", fontWeight: 600 }}>${payloadObj.med}</div>
              <div class="stat-meta">${payloadObj.salts.join(", ")}</div>
            </div>
            <div class="signature-rule mono">
              <span>${scanState.doseTimeHHMM}</span>
              <span>|</span>
              <span>${payloadObj.safe_after}+ safe</span>
            </div>
          </div>

          <div class="item-list">
            <div class="list-row">
              <span class="stat-meta">${t.qr.timing_rule}</span>
              <span class="mono" style=${{ fontWeight: 500 }}>
                ${payloadObj.gap_h} (before / after)
              </span>
            </div>
            <div class="list-row">
              <span class="stat-meta">${t.qr.recommended_swaps}</span>
              <span style=${{ fontWeight: 500, textAlign: "right" }}>
                ${payloadObj.swaps.length ? payloadObj.swaps.join(" | ") : t.timetable.no_conflict}
              </span>
            </div>
          </div>

          <div class="stat-meta mono">${t.qr.dpdp_footer}</div>
          <p style=${{ margin: 0, fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
            ${t.brand.blind_notice}
          </p>
        </div>
      </section>

      <div class="split-grid no-print">
        <div class="card">
          ${primaryRule
            ? html`
                <${AudioReminderPlayer}
                  ruleId=${primaryRule.rule_id}
                  lang=${lang}
                  voiceScripts=${voiceScripts}
                  t=${t}
                  title=${t.qr.speak_pass}
                />
              `
            : html`<div class="stat-meta">${t.qr.generate_note}</div>`}
        </div>

        <div class="card">
          <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span class="card-title" style=${{ fontSize: "var(--text-base)" }}>${t.qr.toggle_json}</span>
            <button type="button" class="btn" onClick=${() => setShowJson((v) => !v)}>
              ${showJson ? "Hide JSON" : "Show JSON"}
            </button>
          </div>
          ${showJson
            ? html`
                <pre class="mono" style=${{
                  margin: 0,
                  padding: "12px",
                  backgroundColor: "var(--bg-page)",
                  border: "1px solid var(--border-hairline)",
                  borderRadius: "var(--radius-control)",
                  fontSize: "12px",
                  overflowX: "auto",
                }}>${JSON.stringify(payloadObj, null, 2)}</pre>
              `
            : html`<p class="stat-meta" style=${{ margin: 0 }}>${t.qr.generate_note}</p>`}
        </div>
      </div>
    </div>
  `;
}

export { findDefaultRuleForMedication };
