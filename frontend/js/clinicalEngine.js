export const PRESET_SCANS = [
  {
    id: "thyroid_chai",
    brandId: "thyronorm",
    strengthText: "50 mcg",
    expiryDate: "2027-08",
    tabletCount: 30,
    doseTimeHHMM: "07:00",
    mealSlot: "early_morning_empty_stomach",
    stripSample: "./samples/01_thyronorm_clean.png",
    mealSample: "./samples/morning_chai_with_milk.png",
    qualityOk: true,
    detectedFoodIds: ["chai_with_milk"],
  },
  {
    id: "iron_palak",
    brandId: "orofer_xt",
    strengthText: "100 mg",
    expiryDate: "2027-02",
    tabletCount: 10,
    doseTimeHHMM: "13:00",
    mealSlot: "lunch",
    stripSample: "./samples/05_orofer_dark_foil.png",
    mealSample: "./samples/thali_palak_dal_curd.png",
    qualityOk: true,
    detectedFoodIds: ["palak_spinach", "chai_with_milk", "dal_lentils"],
  },
  {
    id: "antibiotic_chaas",
    brandId: "ciplox",
    strengthText: "500 mg",
    expiryDate: "2027-09",
    tabletCount: 10,
    doseTimeHHMM: "13:30",
    mealSlot: "lunch",
    stripSample: "./samples/04_ciplox_low_contrast.png",
    mealSample: "./samples/thali_palak_dal_curd.png",
    qualityOk: true,
    detectedFoodIds: ["buttermilk_chaas", "curd_dahi"],
  },
  {
    id: "warfarin_saag",
    brandId: "warf",
    strengthText: "5 mg",
    expiryDate: "2027-10",
    tabletCount: 30,
    doseTimeHHMM: "20:00",
    mealSlot: "dinner",
    stripSample: "./samples/06_warf_rotated_90.png",
    mealSample: "./samples/thali_palak_dal_curd.png",
    qualityOk: true,
    detectedFoodIds: ["sarson_ka_saag", "green_chutney"],
  },
  {
    id: "amlodipine_mosambi",
    brandId: "amlong",
    strengthText: "5 mg",
    expiryDate: "2028-01",
    tabletCount: 15,
    doseTimeHHMM: "09:00",
    mealSlot: "breakfast",
    stripSample: "./samples/14_amlong_low_light_recoverable.png",
    mealSample: "./samples/morning_chai_with_milk.png",
    qualityOk: true,
    detectedFoodIds: ["mosambi_sweet_lime_juice"],
  },
  {
    id: "blur_retry",
    brandId: "thyronorm",
    strengthText: "50 mcg",
    expiryDate: null,
    tabletCount: null,
    doseTimeHHMM: "07:00",
    mealSlot: "early_morning_empty_stomach",
    stripSample: "./samples/15_fail_severe_blur.png",
    mealSample: "./samples/meal_severe_blur.png",
    qualityOk: false,
    detectedFoodIds: ["chai_with_milk"],
  },
];

export const SEED_MEDICINE_BOX = [
  {
    id: "box-thyronorm-seed",
    brand_name: "Thyronorm",
    strength_text: "50 mcg",
    active_salts: ["Levothyroxine Sodium"],
    expiry_date: "2027-08",
    initial_count: 30,
    remaining_tablets: 18,
    doses_per_day: 1,
  },
  {
    id: "box-warf-low-stock",
    brand_name: "Warf",
    strength_text: "5 mg",
    active_salts: ["Warfarin Sodium"],
    expiry_date: "2027-10",
    initial_count: 30,
    remaining_tablets: 3,
    doses_per_day: 1,
  },
  {
    id: "box-orofer-exp-soon",
    brand_name: "Orofer-XT",
    strength_text: "100 mg",
    active_salts: ["Ferrous Ascorbate", "Folic Acid"],
    expiry_date: "2027-01",
    initial_count: 10,
    remaining_tablets: 6,
    doses_per_day: 1,
  },
];

export function formatTimeDelta(hhmm, deltaHours) {
  const [hStr, mStr] = (hhmm || "07:00").split(":");
  const baseMinutes = Number(hStr) * 60 + Number(mStr);
  const deltaMinutes = Math.round(Number(deltaHours || 0) * 60);
  const total = ((baseMinutes + deltaMinutes) % 1440 + 1440) % 1440;
  const hh = String(Math.floor(total / 60)).padStart(2, "0");
  const mm = String(total % 60).padStart(2, "0");
  return `${hh}:${mm}`;
}

export function formatTimeMinutes(hhmm, deltaMinutes) {
  return formatTimeDelta(hhmm, deltaMinutes / 60.0);
}

export function getFoodDisplayName(foodEntry, lang) {
  if (!foodEntry) return "";
  if (lang === "hi" && foodEntry.hindi_name) return foodEntry.hindi_name;
  if (lang === "mr" && foodEntry.marathi_name) return foodEntry.marathi_name;
  return foodEntry.display_name;
}

export function resolveFoodItems(foodIds, foodLookup, milkInChai) {
  return foodIds
    .map((id) => foodLookup[id])
    .filter(Boolean)
    .map((entry) => {
      if (entry.canonical_food_id === "chai_with_milk" && milkInChai === false) {
        const blackTea = foodLookup.black_tea;
        return {
          ...entry,
          effective_id: "black_tea",
          contains_milk: false,
          display_name: blackTea ? blackTea.display_name : "Black Tea (No Milk)",
          hindi_name: blackTea ? blackTea.hindi_name : entry.hindi_name,
          marathi_name: blackTea ? blackTea.marathi_name : entry.marathi_name,
          interfering_nutrients: blackTea ? blackTea.interfering_nutrients : ["tannins_polyphenols", "caffeine"],
          member2_culprit_labels: ["Black Tea (Tannins)"],
        };
      }
      return { ...entry, effective_id: entry.canonical_food_id };
    });
}

export function matchInteractionsForPatient(medication, resolvedFoods, rules) {
  if (!medication || !rules || !rules.length) return [];
  const medSalts = (medication.active_salts || []).map((s) => s.toLowerCase());
  const foodLabels = [];
  for (const item of resolvedFoods) {
    for (const lbl of item.member2_culprit_labels || []) {
      foodLabels.push({ label: lbl, food: item });
    }
    foodLabels.push({ label: item.display_name, food: item });
  }

  const matched = [];
  for (const rule of rules) {
    const ruleSalts = (rule.active_salts || []).map((s) => s.toLowerCase());
    const saltHit = medSalts.some((ms) =>
      ruleSalts.some((rs) => ms.includes(rs) || rs.includes(ms))
    );
    if (!saltHit) continue;

    const culprits = (rule.culprit_indian_foods || []).map((c) => c.toLowerCase());
    const hitFoods = [];
    const seen = new Set();
    for (const { label, food } of foodLabels) {
      const low = label.toLowerCase();
      if (culprits.some((c) => c.includes(low) || low.includes(c))) {
        if (!seen.has(food.effective_id || food.canonical_food_id)) {
          seen.add(food.effective_id || food.canonical_food_id);
          hitFoods.push(food);
        }
      }
    }

    if (hitFoods.length > 0) {
      matched.push({ rule, hitFoods });
    }
  }
  return matched;
}

export function findDefaultRuleForMedication(medication, rules) {
  if (!medication || !rules) return rules?.[0] || null;
  const medSalts = (medication.active_salts || []).map((s) => s.toLowerCase());
  return (
    rules.find((rule) =>
      (rule.active_salts || []).some((rs) =>
        medSalts.some((ms) => ms.includes(rs.toLowerCase()) || rs.toLowerCase().includes(ms))
      )
    ) || rules[0] || null
  );
}

export function buildSmartDailySchedule({
  medication,
  doseTimeHHMM,
  breakfastHHMM,
  lunchHHMM,
  dinnerHHMM,
  lateShiftMinutes,
  primaryRule,
  t,
}) {
  const beforeH = primaryRule?.safe_time_gap_hours?.before_food_hours ?? 1.0;
  const shiftedBreakfast = formatTimeMinutes(breakfastHHMM || "08:30", lateShiftMinutes || 0);
  const shiftedDose = lateShiftMinutes > 0 && Number((doseTimeHHMM || "07:00").split(":")[0]) < 11
    ? formatTimeMinutes(doseTimeHHMM, lateShiftMinutes)
    : doseTimeHHMM;
  const safeGapEnd = formatTimeDelta(shiftedDose, beforeH);

  return [
    {
      id: "alarm-dose",
      time: shiftedDose,
      baseTime: doseTimeHHMM,
      shifted: lateShiftMinutes > 0 && shiftedDose !== doseTimeHHMM,
      kind: "dose",
      label: `${t.scheduler.pill_event}: ${medication.brand_name}`,
    },
    {
      id: "alarm-gap-clear",
      time: safeGapEnd,
      baseTime: formatTimeDelta(doseTimeHHMM, beforeH),
      shifted: lateShiftMinutes > 0 && shiftedDose !== doseTimeHHMM,
      kind: "safe",
      label: t.scheduler.gap_end_event,
    },
    {
      id: "alarm-breakfast",
      time: shiftedBreakfast,
      baseTime: breakfastHHMM,
      shifted: lateShiftMinutes > 0,
      kind: "meal",
      label: t.scheduler.breakfast_label,
    },
    {
      id: "alarm-lunch",
      time: lunchHHMM || "13:30",
      baseTime: lunchHHMM || "13:30",
      shifted: false,
      kind: "meal",
      label: t.scheduler.lunch_label,
    },
    {
      id: "alarm-dinner",
      time: dinnerHHMM || "20:30",
      baseTime: dinnerHHMM || "20:30",
      shifted: false,
      kind: "meal",
      label: t.scheduler.dinner_label,
    },
  ];
}

export function computeMedicineBoxMetrics(item, nowDate = new Date("2026-11-27T00:00:00Z")) {
  const remaining = Math.max(0, Number(item.remaining_tablets || 0));
  const perDay = Math.max(1, Number(item.doses_per_day || 1));
  const daysRemaining = Math.floor(remaining / perDay);

  let monthsToExpiry = 99;
  if (item.expiry_date && /^\d{4}-\d{2}$/.test(item.expiry_date)) {
    const [yr, mo] = item.expiry_date.split("-").map(Number);
    monthsToExpiry = (yr - nowDate.getUTCFullYear()) * 12 + (mo - (nowDate.getUTCMonth() + 1));
  }
  const isLowStock = daysRemaining <= 3;
  const isExpiringSoon = monthsToExpiry <= 3;
  return { daysRemaining, monthsToExpiry, isLowStock, isExpiringSoon };
}

export function buildPharmacyReorderLinks(item) {
  const q = encodeURIComponent(
    `${item.brand_name || ""} ${item.strength_text || ""}`.trim()
  );
  return {
    oneMgUrl: `https://www.1mg.com/search/all?name=${q}`,
    pharmeasyUrl: `https://pharmeasy.in/search/all?name=${q}`,
  };
}

export function buildQrPassPayload({
  bundleId,
  lang,
  medication,
  doseTimeHHMM,
  interactions,
  selectedSwaps,
}) {
  const safeRule = interactions[0]?.rule || null;
  const beforeH = safeRule?.safe_time_gap_hours?.before_food_hours ?? 1.0;
  const afterH = safeRule?.safe_time_gap_hours?.after_food_hours ?? 2.0;
  const earliestMeal = formatTimeDelta(doseTimeHHMM, beforeH);
  const nextSafeDoseAfterMeal = formatTimeDelta(doseTimeHHMM, afterH);

  const swaps = interactions
    .map((item) => {
      const chosen = selectedSwaps[item.rule.rule_id] || 0;
      return (
        item.rule.ghar_ki_rasoi_swaps?.[chosen]?.substitute ||
        item.rule.ghar_ki_rasoi_swaps?.[0]?.substitute ||
        ""
      );
    })
    .filter(Boolean);

  return {
    schema: "aahar-rx.health-pass.v1",
    pass_id: bundleId,
    lang,
    med: `${medication.brand_name}${medication.strength_text ? " " + medication.strength_text : ""}`,
    salts: medication.active_salts,
    dose: doseTimeHHMM,
    safe_after: earliestMeal,
    gap_h: `${beforeH}/${afterH}`,
    alt_hhmm: nextSafeDoseAfterMeal,
    rules: interactions.map((i) => i.rule.rule_id),
    swaps: swaps.slice(0, 2),
    raw_images_retained: false,
    note: "Timing guidance only; do not alter dose without doctor advice.",
  };
}
