import { AlertIcon, ExternalLinkIcon, PackageIcon } from "../icons.js";
import { buildPharmacyReorderLinks, computeMedicineBoxMetrics } from "../clinicalEngine.js";
import { AudioReminderPlayer } from "./AudioReminderPlayer.js";

const html = window.htm.bind(window.React.createElement);

export function MedicineBoxScreen({
  t,
  lang,
  medicineBox,
  onTakeDose,
  uxVoiceAlerts,
}) {
  const enriched = medicineBox.map((item) => ({
    ...item,
    metrics: computeMedicineBoxMetrics(item),
    links: buildPharmacyReorderLinks(item),
  }));

  const lowStockCount = enriched.filter((x) => x.metrics.isLowStock).length;
  const expiringCount = enriched.filter((x) => x.metrics.isExpiringSoon).length;

  return html`
    <div style=${{ display: "flex", flexDirection: "column", gap: "var(--space-24)" }}>
      <div class="screen-header">
        <div>
          <h1 class="screen-title">${t.med_box.heading}</h1>
          <p class="screen-sub">${t.med_box.subheading}</p>
        </div>
        <span class="tag mono">${enriched.length} strips</span>
      </div>

      <div class="stats-row">
        <div class="card card-compact">
          <span class="stat-label">${t.med_box.total_strips}</span>
          <span class="stat-value">${enriched.length}</span>
          <span class="stat-meta">Home inventory</span>
        </div>
        <div class="card card-compact">
          <span class="stat-label">${t.med_box.low_stock_count}</span>
          <span class="stat-value ${lowStockCount > 0 ? "danger" : "accent"}">${lowStockCount}</span>
          <span class="stat-meta">Trigger at 3 days left</span>
        </div>
        <div class="card card-compact">
          <span class="stat-label">${t.med_box.expiring_count}</span>
          <span class="stat-value ${expiringCount > 0 ? "danger" : ""}">${expiringCount}</span>
          <span class="stat-meta">Expiry monitor</span>
        </div>
      </div>

      ${lowStockCount > 0 || expiringCount > 0
        ? html`
            <div class="alert-banner" role="alert">
              <div class="alert-banner-title">
                <span class="icon-box" style=${{ color: "var(--semantic-high)" }}><${AlertIcon} /></span>
                <span>${t.med_box.low_stock_alert}</span>
              </div>
              <div class="stat-meta">
                ${enriched
                  .filter((x) => x.metrics.isLowStock || x.metrics.isExpiringSoon)
                  .map((x) => `${x.brand_name} (${x.remaining_tablets} left | EXP ${x.expiry_date || "Manual"})`)
                  .join("  |  ")}
              </div>
            </div>
          `
        : null}

      <div class="split-grid">
        <div class="item-list" style=${{ gap: "var(--space-12)" }}>
          ${enriched.map((item) => {
            const m = item.metrics;
            const statusClass = m.isLowStock ? "high" : m.isExpiringSoon ? "moderate" : "safe";
            const statusLabel = m.isLowStock
              ? t.med_box.low_stock_badge
              : m.isExpiringSoon
              ? t.med_box.expiry_soon_badge
              : t.med_box.healthy_badge;

            return html`
              <article key=${item.id} class="card">
                <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
                  <div>
                    <div class="card-title">
                      <span class="icon-box"><${PackageIcon} /></span>
                      <span>${item.brand_name}${item.strength_text ? ` ${item.strength_text}` : ""}</span>
                    </div>
                    <div class="stat-meta">${(item.active_salts || []).join(", ")}</div>
                  </div>
                  <span class="tag ${statusClass}">${statusLabel}</span>
                </div>

                <div class="stats-row">
                  <div class="list-row" style=${{ flexDirection: "column", alignItems: "flex-start" }}>
                    <span class="stat-meta">${t.med_box.tablets_left}</span>
                    <span class="mono" style=${{ fontWeight: 600 }}>
                      ${item.remaining_tablets} / ${item.initial_count}
                    </span>
                  </div>
                  <div class="list-row" style=${{ flexDirection: "column", alignItems: "flex-start" }}>
                    <span class="stat-meta">${t.med_box.days_left}</span>
                    <span class="mono" style=${{ fontWeight: 600, color: m.isLowStock ? "var(--semantic-high)" : "var(--text-primary)" }}>
                      ${m.daysRemaining}d
                    </span>
                  </div>
                  <div class="list-row" style=${{ flexDirection: "column", alignItems: "flex-start" }}>
                    <span class="stat-meta">${t.med_box.expiry_title}</span>
                    <span class="mono" style=${{ fontWeight: 600 }}>
                      ${item.expiry_date || "Not set"}
                    </span>
                  </div>
                </div>

                <div class="btn-row">
                  <button
                    type="button"
                    class="btn btn-primary"
                    disabled=${item.remaining_tablets <= 0}
                    onClick=${() => onTakeDose(item.id)}
                  >
                    ${t.med_box.take_dose_btn}
                  </button>
                  <a
                    class="btn"
                    style=${{ textDecoration: "none" }}
                    href=${item.links.oneMgUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span class="icon-box"><${ExternalLinkIcon} /></span>
                    <span>${t.med_box.reorder_1mg}</span>
                  </a>
                  <a
                    class="btn"
                    style=${{ textDecoration: "none" }}
                    href=${item.links.pharmeasyUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span class="icon-box"><${ExternalLinkIcon} /></span>
                    <span>${t.med_box.reorder_pharmeasy}</span>
                  </a>
                </div>
              </article>
            `;
          })}
        </div>

        <div class="card">
          <${AudioReminderPlayer}
            ruleId="ALERT-REFILL"
            lang=${lang}
            voiceScripts=${uxVoiceAlerts}
            t=${t}
            title=${t.med_box.listen_refill}
          />
          <p class="stat-meta" style=${{ margin: 0 }}>
            ${t.med_box.note_search_link}
          </p>
        </div>
      </div>
    </div>
  `;
}
