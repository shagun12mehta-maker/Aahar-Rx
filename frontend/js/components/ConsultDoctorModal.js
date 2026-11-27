import { AlertIcon, CloseIcon, ExternalLinkIcon, ShieldIcon, VideoIcon } from "../icons.js";
import { AudioReminderPlayer } from "./AudioReminderPlayer.js";

const { useEffect, useState } = window.React;
const html = window.htm.bind(window.React.createElement);

export function ConsultDoctorModal({
  isOpen,
  onClose,
  t,
  lang,
  medication,
  resolvedFoods,
  primaryInteraction,
  uxVoiceAlerts,
}) {
  const [doctorShareConsent, setDoctorShareConsent] = useState(false);
  const [inCallView, setInCallView] = useState(false);
  const [callSeconds, setCallSeconds] = useState(0);

  useEffect(() => {
    if (!isOpen) {
      setDoctorShareConsent(false);
      setInCallView(false);
      setCallSeconds(0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!inCallView) return undefined;
    const timer = setInterval(() => setCallSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [inCallView]);

  if (!isOpen || !primaryInteraction) return null;
  const rule = primaryInteraction.rule;
  const dropPct = rule.absorption_impact?.bioavailability_drop_pct ?? 0;
  const durationLabel = `${String(Math.floor(callSeconds / 60)).padStart(2, "0")}:${String(
    callSeconds % 60
  ).padStart(2, "0")}`;

  return html`
    <div
      class="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="consult-modal-title"
    >
      <div class="modal-panel">
        <div class="modal-header">
          <div>
            <div class="tag high" style=${{ marginBottom: "8px" }}>
              ${rule.severity} | ${rule.rule_id}
            </div>
            <h2 id="consult-modal-title" class="screen-title" style=${{ fontSize: "22px" }}>
              ${inCallView ? t.consult.doctor_view_title : t.consult.popup_title}
            </h2>
            <p class="screen-sub">${t.consult.popup_sub}</p>
          </div>
          <button
            type="button"
            class="btn"
            aria-label=${t.consult.end_call}
            onClick=${onClose}
          >
            <span class="icon-box"><${CloseIcon} /></span>
            <span>${inCallView ? t.consult.end_call : t.consult.dismiss}</span>
          </button>
        </div>

        ${!inCallView
          ? html`
              <div class="alert-banner">
                <div class="alert-banner-title">
                  <span class="icon-box" style=${{ color: "var(--semantic-high)" }}><${AlertIcon} /></span>
                  <span>${medication.brand_name} — ${rule.drug_class}</span>
                </div>
                <p style=${{ margin: 0, fontSize: "var(--text-sm)" }}>
                  ${rule.biochemical_mechanism}
                </p>
                <div class="stat-meta mono">
                  Impact: ${dropPct > 0 ? `-${dropPct}%` : `+${Math.abs(dropPct)}%`} | Safe gap: ${rule.safe_time_gap_hours.before_food_hours}h before / ${rule.safe_time_gap_hours.after_food_hours}h after
                </div>
              </div>

              <div class="consent-box ${doctorShareConsent ? "" : "pending"}">
                <div class="card-title" style=${{ fontSize: "var(--text-base)" }}>
                  <span class="icon-box"><${ShieldIcon} /></span>
                  <span>DPDP Act 2023 — Separate Doctor Report Consent</span>
                </div>
                <label class="check-row">
                  <input
                    type="checkbox"
                    checked=${doctorShareConsent}
                    onChange=${(e) => setDoctorShareConsent(e.target.checked)}
                  />
                  <span style=${{ fontSize: "var(--text-sm)", fontWeight: 500 }}>
                    ${t.consult.consent_label}
                  </span>
                </label>
              </div>

              <${AudioReminderPlayer}
                ruleId="ALERT-HIGH-RISK"
                lang=${lang}
                voiceScripts=${uxVoiceAlerts}
                t=${t}
                title=${t.consult.listen_alert}
              />

              <div class="btn-row" style=${{ justifyContent: "flex-end" }}>
                <button type="button" class="btn" onClick=${onClose}>
                  ${t.consult.dismiss}
                </button>
                <button
                  type="button"
                  class="btn btn-primary"
                  disabled=${!doctorShareConsent}
                  onClick=${() => setInCallView(true)}
                >
                  <span class="icon-box" style=${{ color: "#ffffff" }}><${VideoIcon} /></span>
                  <span>${t.consult.open_call}</span>
                </button>
              </div>
            `
          : html`
              <div class="equal-grid-2">
                <div class="video-stage">
                  <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span class="tag safe mono">${t.consult.video_frame_label}</span>
                    <span class="tag mono">${durationLabel}</span>
                  </div>
                  <div class="video-placeholder">
                    <div class="icon-box" style=${{ width: "36px", height: "36px", color: "var(--accent)" }}>
                      <${VideoIcon} />
                    </div>
                    <div style=${{ fontWeight: 500 }}>${t.consult.doctor_account}</div>
                    <div class="stat-meta">${t.consult.dose_safety_rule}</div>
                  </div>
                  <div class="stat-meta mono">
                    WebRTC / Jitsi demo channel ready (anonymous test clinician ID)
                  </div>
                </div>

                <div class="card" style=${{ backgroundColor: "var(--bg-page)" }}>
                  <div class="card-title" style=${{ fontSize: "var(--text-base)" }}>
                    ${t.consult.report_title}
                  </div>
                  <div class="item-list">
                    <div class="list-row">
                      <span class="stat-meta">Medication</span>
                      <span class="mono" style=${{ fontWeight: 500 }}>
                        ${medication.brand_name} (${(medication.active_salts || []).join(", ")})
                      </span>
                    </div>
                    <div class="list-row">
                      <span class="stat-meta">Conflicting dish</span>
                      <span style=${{ fontWeight: 500 }}>
                        ${resolvedFoods.map((f) => f.display_name).join(", ")}
                      </span>
                    </div>
                    <div class="list-row">
                      <span class="stat-meta">Bioavailability delta</span>
                      <span class="mono" style=${{ color: "var(--semantic-high)", fontWeight: 600 }}>
                        -${dropPct}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <div class="field-label" style=${{ marginBottom: "4px" }}>IFCT 2017 Evidence Shared with Clinician</div>
                    <table class="evidence-table">
                      <tbody>
                        ${(rule.ifct_evidence || []).map((ev, i) => html`
                          <tr key=${i}>
                            <td>${ev.food}</td>
                            <td class="stat-meta">${ev.primary_nutrient}</td>
                            <td class="num">${ev.value}</td>
                          </tr>
                        `)}
                      </tbody>
                    </table>
                  </div>
                  <div class="stat-meta">${t.consult.dose_safety_rule}</div>
                </div>
              </div>
            `}
      </div>
    </div>
  `;
}
