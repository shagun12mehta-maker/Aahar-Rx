# Aahar-Rx Smart Scan (Member 1) — Accuracy Benchmark Report

> Generated UTC: `2026-11-26T14:27:03.412820+00:00`  
> Safety Notice: Aahar-Rx provides timing and dietary guidance only. It never advises skipping, altering, or replacing prescribed medication dosages. Consult your doctor or pharmacist before making any change to your treatment plan.

## 1. Day 1 OCR Engine Research Comparison (Raw vs OpenCV Preprocessed)

| OCR Engine | Raw Strip Salt Accuracy | Enhanced (CLAHE + Illumination Flatten) Accuracy | Mean Raw Latency (ms) | Mean Enhanced Latency (ms) |
| --- | ---: | ---: | ---: | ---: |
| `rapidocr_paddle_ppocr` | 8/8 (100.0%) | 8/8 (100.0%) | 850.6 | 652.5 |
| `windows_media_ocr` | 7/8 (87.5%) | 7/8 (87.5%) | 1008.8 | 1090.5 |

*Note: `TesseractOcrEngine` is implemented and supported in code; local `tesseract.exe` binary was not installed on this machine, so live comparisons ran on `rapidocr_paddle_ppocr` (PaddleOCR PP-OCRv4 ONNX) and `windows_media_ocr`.*

## 2. Day 4 End-to-End 17-Strip Smart Scan Benchmark

- **Recoverable Strip Salt Accuracy**: **14/14 (100.0%)**
- **Regional Brand Recovery**: **2/2**
- **Unreadable Photo Rejection (Retry Gate)**: **3/3 (100.0%)**

| Case ID | Condition | Quality Gate | Resolved Brand | Resolved Salts | Conf | Latency (ms) |
| --- | --- | --- | --- | --- | ---: | ---: |
| `01_thyronorm_clean` | clean | PASS | Thyronorm | Levothyroxine Sodium | 0.97 | 653.53 |
| `02_glycomet_curved_foil` | curved_foil | PASS | Glycomet | Metformin Hydrochloride | 0.97 | 642.62 |
| `03_shelcal_glare` | glare_hotspot | PASS | Shelcal | Calcium Carbonate, Cholecalciferol (Vitamin D3) | 0.97 | 712.71 |
| `04_ciplox_low_contrast` | low_contrast_foil | PASS | Ciplox | Ciprofloxacin | 0.97 | 610.14 |
| `05_orofer_dark_foil` | dark_metallic_foil | PASS | Ferrous Ascorbate (Generic / Salt Match) | Ferrous Ascorbate, Folic Acid | 0.93 | 658.73 |
| `06_warf_rotated_90` | rotated_90 | PASS | Warf | Warfarin Sodium | 0.97 | 653.67 |
| `07_atorva_rotated_180` | rotated_180 | PASS | Atorva | Atorvastatin | 0.97 | 846.36 |
| `08_telma_clean` | clean | PASS | Telma | Telmisartan | 0.97 | 817.44 |
| `09_pan40_curved` | curved_foil | PASS | Pan 40 | Pantoprazole Sodium | 0.97 | 903.22 |
| `10_augmentin_clean` | clean | PASS | Augmentin | Amoxicillin, Clavulanic Acid | 0.97 | 1019.78 |
| `11_thyroup_regional` | regional_brand_curved | PASS | Thyroup | Levothyroxine Sodium | 0.97 | 876.46 |
| `12_ferro_xt_regional_glare` | regional_glare | PASS | Ferro-XT | Ferrous Ascorbate, Folic Acid | 0.97 | 631.18 |
| `13_lasix_generic_salt` | back_of_strip_salt | PASS | Furosemide (Generic / Salt Match) | Furosemide | 0.93 | 1131.93 |
| `14_amlong_low_light_recoverable` | dim_stage_light | PASS | Amlong | Amlodipine Besylate | 0.97 | 672.71 |
| `15_fail_severe_blur` | severe_blur_reject | RETRY | - | - | 0.0 | 34.58 |
| `16_fail_severe_dark` | severe_dark_reject | RETRY | - | - | 0.0 | 33.85 |
| `17_fail_severe_glare` | severe_glare_reject | RETRY | - | - | 0.0 | 47.8 |

## 3. Day 5 Meal Vision, Mandatory Confirmation & Member 2 Integration Checks

- **Thyroid + Morning Chai with Milk**: `{"scenario": "Thyroid + Morning Chai with Milk", "resolved_salts": ["Levothyroxine Sodium"], "nutrients_flagged": ["caffeine", "calcium", "tannins_polyphenols"], "matched_member2_rules": ["RULE-THY-001"]}`
- **Warfarin (90deg rotated) + Indian Thali (Palak + Dal + Curd)**: `{"scenario": "Warfarin (90deg rotated) + Indian Thali (Palak + Dal + Curd)", "resolved_salts": ["Warfarin Sodium"], "nutrients_flagged": ["calcium", "high_fiber", "iron", "oxalates", "phytates", "potassium", "vitamin_k"], "matched_member2_rules": ["RULE-BLD-004"]}`
- **Shaky / Blurred Meal Photo Retry**: `{"scenario": "Shaky / Blurred Meal Photo Retry", "retry_required": true, "retry_guidance": ["Photo looks blurry. Hold the camera steady 15-20 cm away and tap the screen to focus before capturing."]}`

## 4. Pitch Visual Assets Generated

- `reports/before_after_strip_recovery.png`
- `reports/meal_confirmation_flow_visual.png`