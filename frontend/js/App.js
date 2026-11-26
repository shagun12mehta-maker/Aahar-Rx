import {
  ActivityIcon,
  ClockIcon,
  ConfirmIcon,
  LeafMarkIcon,
  QrIcon,
  ScanIcon,
  TypeSizeIcon,
} from "./icons.js";
import {
  PRESET_SCANS,
  findDefaultRuleForMedication,
  matchInteractionsForPatient,
  resolveFoodItems,
} from "./clinicalEngine.js";
import {
  AbsorptionCurveScreen,
  ConfirmScreen,
  QrHealthPassScreen,
  ScanScreen,
  TimetableScreen,
} from "./components/Screens.js";

const { useEffect, useMemo, useState } = window.React;
const html = window.htm.bind(window.React.createElement);

function App() {
  const [bundleData, setBundleData] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [lang, setLang] = useState("en");
  const [elderlyMode, setElderlyMode] = useState(false);
  const [activeTab, setActiveTab] = useState("scan");
  const [consented, setConsented] = useState(true);
  const [bridgeOnline, setBridgeOnline] = useState(false);

  const [scanState, setScanState] = useState(null);
  const [selectedSwaps, setSelectedSwaps] = useState({});
  const [selectedRuleId, setSelectedRuleId] = useState("RULE-THY-001");
  const [bundleId] = useState("AHR-2026-THY1");

  useEffect(() => {
    async function loadAll() {
      try {
        const [i18nRes, rulesRes, pkRes, voiceRes] = await Promise.all([
          fetch("./data/i18n.json"),
          fetch("./data/rules_bundle.json"),
          fetch("./data/pk_profiles.json"),
          fetch("./data/voice_scripts.json"),
        ]);
        const [i18n, rulesBundle, pkProfiles, voiceScripts] = await Promise.all([
          i18nRes.json(),
          rulesRes.json(),
          pkRes.json(),
          voiceRes.json(),
        ]);

        const brandLookup = Object.fromEntries(
          (rulesBundle.brands || []).map((b) => [b.brand_id, b])
        );
        const foodLookup = Object.fromEntries(
          (rulesBundle.foods || []).map((f) => [f.canonical_food_id, f])
        );
        const defaultPreset = PRESET_SCANS[0];
        const defaultMed = brandLookup[defaultPreset.brandId] || rulesBundle.brands[0];

        setBundleData({
          i18n,
          rules: rulesBundle.rules,
          brands: rulesBundle.brands,
          foods: rulesBundle.foods,
          brandLookup,
          foodLookup,
          pkProfiles,
          voiceScripts,
        });
        setScanState({
          activePresetId: defaultPreset.id,
          medication: { ...defaultMed, strength_text: defaultPreset.strengthText },
          foodIds: [...defaultPreset.detectedFoodIds],
          milkInChai: true,
          doseTimeHHMM: defaultPreset.doseTimeHHMM,
          mealSlot: defaultPreset.mealSlot,
          qualityOk: true,
          retryGuidance: "",
          stripPreviewUrl: defaultPreset.stripSample,
          mealPreviewUrl: defaultPreset.mealSample,
          confirmedByUser: true,
        });

        try {
          const h = await fetch("./api/health");
          if (h.ok) {
            const payload = await h.json();
            if (payload && payload.bridge === "member1_smart_scan") {
              setBridgeOnline(true);
            }
          }
        } catch {
          setBridgeOnline(false);
        }
      } catch (err) {
        setLoadError(String(err));
      }
    }
    loadAll();
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    function onKeyDown(e) {
      if (e.target && ["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;
      const tabMap = { "1": "scan", "2": "confirm", "3": "timetable", "4": "curve", "5": "qr" };
      if (tabMap[e.key]) {
        setActiveTab(tabMap[e.key]);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const t = bundleData?.i18n?.[lang] || bundleData?.i18n?.en || null;

  const resolvedFoods = useMemo(() => {
    if (!bundleData || !scanState) return [];
    return resolveFoodItems(scanState.foodIds, bundleData.foodLookup, scanState.milkInChai);
  }, [bundleData, scanState]);

  const interactions = useMemo(() => {
    if (!bundleData || !scanState) return [];
    return matchInteractionsForPatient(scanState.medication, resolvedFoods, bundleData.rules);
  }, [bundleData, scanState, resolvedFoods]);

  if (loadError) {
    return html`<div class="main-content"><div class="alert-banner">${loadError}</div></div>`;
  }

  if (!bundleData || !t || !scanState) {
    return html`<div class="main-content"><p class="screen-sub">Loading Aahar-Rx workspace</p></div>`;
  }

  function applyPreset(presetId) {
    const p = PRESET_SCANS.find((item) => item.id === presetId);
    if (!p) return;
    const med = bundleData.brandLookup[p.brandId] || bundleData.brands[0];
    setScanState({
      activePresetId: p.id,
      medication: { ...med, strength_text: p.strengthText },
      foodIds: [...p.detectedFoodIds],
      milkInChai: true,
      doseTimeHHMM: p.doseTimeHHMM,
      mealSlot: p.mealSlot,
      qualityOk: p.qualityOk,
      retryGuidance: p.qualityOk ? "" : t.confirm.retry_guidance,
      stripPreviewUrl: p.stripSample,
      mealPreviewUrl: p.mealSample,
      confirmedByUser: false,
    });
    const rule = findDefaultRuleForMedication(med, bundleData.rules);
    if (rule) setSelectedRuleId(rule.rule_id);
  }

  function selectManualBrand(brandEntry) {
    setScanState((prev) => ({
      ...prev,
      medication: { ...brandEntry, strength_text: brandEntry.common_strengths?.[0] || null },
      qualityOk: true,
      retryGuidance: "",
      confirmedByUser: false,
    }));
    const rule = findDefaultRuleForMedication(brandEntry, bundleData.rules);
    if (rule) setSelectedRuleId(rule.rule_id);
  }

  async function handleFileUpload(kind, file) {
    const localUrl = URL.createObjectURL(file);
    setScanState((prev) => ({
      ...prev,
      ...(kind === "strip" ? { stripPreviewUrl: localUrl } : { mealPreviewUrl: localUrl }),
      confirmedByUser: false,
    }));

    if (!bridgeOnline) {
      setActiveTab("confirm");
      return;
    }

    const buf = await file.arrayBuffer();
    const res = await fetch(`./api/local-scan/${kind}?meal_slot=${encodeURIComponent(scanState.mealSlot)}`, {
      method: "POST",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: buf,
    });
    if (!res.ok) return;
    const data = await res.json();

    if (kind === "strip") {
      if (data.retry_required) {
        setScanState((prev) => ({
          ...prev,
          qualityOk: false,
          retryGuidance: (data.retry_guidance || []).join(" "),
        }));
      } else if (data.medications && data.medications.length > 0) {
        const med = data.medications[0];
        setScanState((prev) => ({
          ...prev,
          medication: med,
          qualityOk: true,
          retryGuidance: "",
        }));
        const rule = findDefaultRuleForMedication(med, bundleData.rules);
        if (rule) setSelectedRuleId(rule.rule_id);
      }
    } else if (kind === "meal") {
      if (data.retry_required) {
        setScanState((prev) => ({
          ...prev,
          qualityOk: false,
          retryGuidance: (data.retry_guidance || []).join(" "),
        }));
      } else if (data.detected_food_ids && data.detected_food_ids.length > 0) {
        setScanState((prev) => ({
          ...prev,
          foodIds: data.detected_food_ids,
          qualityOk: true,
          retryGuidance: "",
        }));
      }
    }
    setActiveTab("confirm");
  }

  const navItems = [
    { id: "scan", label: t.nav.scan, icon: ScanIcon, key: "1" },
    { id: "confirm", label: t.nav.confirm, icon: ConfirmIcon, key: "2" },
    { id: "timetable", label: t.nav.timetable, icon: ClockIcon, key: "3" },
    { id: "curve", label: t.nav.curve, icon: ActivityIcon, key: "4" },
    { id: "qr", label: t.nav.qr_pass, icon: QrIcon, key: "5" },
  ];

  const primaryRule = interactions[0]?.rule || findDefaultRuleForMedication(scanState.medication, bundleData.rules);

  return html`
    <div class="app-shell ${elderlyMode ? "elderly-mode" : ""}">
      <aside class="left-rail" aria-label="Primary Navigation">
        <div>
          <div class="brand-lockup">
            <div class="brand-wordmark">
              <span class="brand-mark"><${LeafMarkIcon} /></span>
              <span>${t.brand.name}</span>
            </div>
            <div class="brand-sub">${t.brand.tagline}</div>
          </div>

          <div class="nav-desktop">
            <p class="rail-section-label">${t.nav.scan} / ${t.nav.qr_pass}</p>
            <nav class="nav-list">
              ${navItems.map((item) => {
                const active = activeTab === item.id;
                const locked = !scanState.confirmedByUser && (item.id === "timetable" || item.id === "qr");
                return html`
                  <button
                    key=${item.id}
                    type="button"
                    class="nav-item ${active ? "active" : ""}"
                    disabled=${locked}
                    onClick=${() => setActiveTab(item.id)}
                  >
                    <span class="nav-item-main">
                      <span class="icon-box"><${item.icon} /></span>
                      <span>${item.label}</span>
                    </span>
                    <span class="keycap">${item.key}</span>
                  </button>
                `;
              })}
            </nav>
          </div>
        </div>

        <div class="rail-controls">
          <div>
            <div class="field-label" style=${{ marginBottom: "6px" }}>${t.nav.language}</div>
            <div class="lang-segmented" role="group" aria-label=${t.nav.language}>
              ${[
                { code: "en", label: "EN" },
                { code: "hi", label: "हिन्दी" },
                { code: "mr", label: "मराठी" },
              ].map((opt) => html`
                <button
                  key=${opt.code}
                  type="button"
                  class="lang-btn ${lang === opt.code ? "active" : ""}"
                  onClick=${() => setLang(opt.code)}
                >
                  ${opt.label}
                </button>
              `)}
            </div>
          </div>

          <button
            type="button"
            class="toggle-btn ${elderlyMode ? "active" : ""}"
            aria-pressed=${elderlyMode}
            onClick=${() => setElderlyMode((v) => !v)}
          >
            <span style=${{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span class="icon-box"><${TypeSizeIcon} /></span>
              <span>${elderlyMode ? t.nav.elderly_on : t.nav.elderly_mode}</span>
            </span>
            <span class="mono" style=${{ fontSize: "11px" }}>${elderlyMode ? "18px" : "15px"}</span>
          </button>

          <div class="stat-meta">${t.brand.dpdp_badge}</div>
        </div>
      </aside>

      <div class="workspace-wrap">
        <header class="topbar">
          <div class="timing-signature">
            <span class="signature-rule mono">
              <span class="status-dot ${interactions.length ? "danger" : ""}" />
              <span>${scanState.medication.brand_name} ${scanState.doseTimeHHMM}</span>
              ${primaryRule
                ? html`<span>| ${primaryRule.safe_time_gap_hours.before_food_hours}h before / ${primaryRule.safe_time_gap_hours.after_food_hours}h after</span>`
                : null}
            </span>
            <span>${(scanState.medication.active_salts || []).join(" + ")}</span>
          </div>
          <span class="tag ${scanState.confirmedByUser ? "safe" : "moderate"}">
            ${scanState.confirmedByUser ? t.confirm.confirmed_badge : t.confirm.pending_badge}
          </span>
        </header>

        <main class="main-content">
          ${activeTab === "scan"
            ? html`
                <${ScanScreen}
                  t=${t}
                  lang=${lang}
                  consented=${consented}
                  onToggleConsent=${setConsented}
                  brands=${bundleData.brands}
                  scanState=${scanState}
                  onSelectPreset=${applyPreset}
                  onSelectManualBrand=${selectManualBrand}
                  onChangeDoseTime=${(val) => setScanState((p) => ({ ...p, doseTimeHHMM: val }))}
                  onChangeMealSlot=${(val) => setScanState((p) => ({ ...p, mealSlot: val }))}
                  onProceedToConfirm=${() => setActiveTab("confirm")}
                  bridgeOnline=${bridgeOnline}
                  onUploadFileScan=${handleFileUpload}
                />
              `
            : null}

          ${activeTab === "confirm"
            ? html`
                <${ConfirmScreen}
                  t=${t}
                  lang=${lang}
                  foods=${bundleData.foods}
                  scanState=${scanState}
                  resolvedFoods=${resolvedFoods}
                  onToggleMilk=${(flag) => setScanState((p) => ({ ...p, milkInChai: flag, confirmedByUser: false }))}
                  onRemoveFood=${(fid) =>
                    setScanState((p) => ({
                      ...p,
                      foodIds: p.foodIds.filter((id) => id !== fid),
                      confirmedByUser: false,
                    }))
                  }
                  onAddFood=${(fid) =>
                    setScanState((p) => ({
                      ...p,
                      foodIds: p.foodIds.includes(fid) ? p.foodIds : [...p.foodIds, fid],
                      confirmedByUser: false,
                    }))
                  }
                  onConfirmBundle=${() => {
                    setScanState((p) => ({ ...p, confirmedByUser: true }));
                    setActiveTab("timetable");
                  }}
                  onBackToScan=${() => setActiveTab("scan")}
                />
              `
            : null}

          ${activeTab === "timetable"
            ? html`
                <${TimetableScreen}
                  t=${t}
                  lang=${lang}
                  scanState=${scanState}
                  interactions=${interactions}
                  selectedSwaps=${selectedSwaps}
                  onSelectSwap=${(rid, idx) => setSelectedSwaps((prev) => ({ ...prev, [rid]: idx }))}
                  voiceScripts=${bundleData.voiceScripts}
                  onOpenCurve=${(rid) => {
                    if (rid) setSelectedRuleId(rid);
                    setActiveTab("curve");
                  }}
                  onOpenQrPass=${() => setActiveTab("qr")}
                />
              `
            : null}

          ${activeTab === "curve"
            ? html`
                <${AbsorptionCurveScreen}
                  t=${t}
                  lang=${lang}
                  rules=${bundleData.rules}
                  pkProfiles=${bundleData.pkProfiles}
                  selectedRuleId=${selectedRuleId}
                  onSelectRule=${setSelectedRuleId}
                  voiceScripts=${bundleData.voiceScripts}
                />
              `
            : null}

          ${activeTab === "qr"
            ? html`
                <${QrHealthPassScreen}
                  t=${t}
                  lang=${lang}
                  scanState=${scanState}
                  interactions=${interactions}
                  selectedSwaps=${selectedSwaps}
                  voiceScripts=${bundleData.voiceScripts}
                  bundleId=${bundleId}
                />
              `
            : null}
        </main>

        <footer class="disclaimer-footer">
          <span>${t.brand.blind_notice}</span>
          <span class="mono">EN / HI / MR | Member 3 UI</span>
        </footer>
      </div>

      <nav class="mobile-nav" aria-label="Mobile Navigation">
        ${navItems.map((item) => {
          const active = activeTab === item.id;
          const locked = !scanState.confirmedByUser && (item.id === "timetable" || item.id === "qr");
          return html`
            <button
              key=${item.id}
              type="button"
              class="mobile-nav-btn ${active ? "active" : ""}"
              disabled=${locked}
              onClick=${() => setActiveTab(item.id)}
            >
              <span class="icon-box"><${item.icon} /></span>
              <span>${item.label}</span>
            </button>
          `;
        })}
      </nav>
    </div>
  `;
}

const root = window.ReactDOM.createRoot(document.getElementById("root"));
root.render(html`<${App} />`);
