<!-- The default blueprint before issue #82 (one level, 81 topics), frozen for the tests: most of
     them plan on a fresh ledger with it. The shipped default is templates/blueprint.md. -->

# Curriculum Blueprint — Hospital / Internal Medicine

The map of what can be tested. Each session samples topics from here; your performance
against it is kept in `learner_ledger.json`.

**Format the skill relies on**
- Each domain is a `##` heading ending in `(weight: high | medium | low)` or a number.
  Weights are sampling priorities for new topics; your scores, due dates, gaps and
  self-ratings override them over time.
- Each topic is a bullet starting with a stable ID: `- CODE-NN  Topic label`. The part
  before the hyphen is the domain code. The ledger refers to these IDs, so never renumber:
  add new topics with new IDs, and retire old ones by marking them `(retired)`.
- Cross-references such as "(see HEME-04)" are fine.
- Optional second level: a topic (the disease, which returns on schedule) may list its
  sub-topics (which rotate and are recorded) as bullets indented under it, each starting
  with its own stable ID, the topic's ID plus a letter: `  - CODE-NNa  Sub-topic label`,
  optionally ending in `(aspects: management high, testing low)`. Bullets indented under a
  sub-topic, without an ID, are its decision points: the author's list to draw on, never
  scheduled. A topic without sub-topics works as a one-level topic.

This default blueprint suits a hospitalist or general internist and is adapted from the
SHM Core Competencies in Hospital Medicine and the ABIM Internal Medicine certification
blueprint. For other specialties, the setup step drafts an equivalent blueprint in the
same format for you to check.

---

## A. Cardiology  (weight: high)
- CARD-01  Acute coronary syndrome (STEMI/NSTEMI/UA)
- CARD-02  Acute decompensated heart failure (HFrEF / HFpEF)
- CARD-03  Atrial fibrillation & rate/rhythm control, anticoagulation
- CARD-04  Bradyarrhythmias & tachyarrhythmias, syncope
- CARD-05  Valvular disease & infective endocarditis
- CARD-06  Hypertensive emergency/urgency
- CARD-07  Pericardial disease, myocarditis
- CARD-08  Venous thromboembolism — PE (see also PULM/HEME)

## B. Pulmonary & Critical Care  (weight: high)
- PULM-01  Community- & hospital-acquired pneumonia
- PULM-02  COPD exacerbation
- PULM-03  Asthma exacerbation
- PULM-04  Acute respiratory failure, ARDS, mechanical ventilation basics
- PULM-05  Pleural effusion / empyema
- PULM-06  Pulmonary embolism (management)
- PULM-07  Sepsis & septic shock
- PULM-08  Shock differentiation & resuscitation

## C. Infectious Disease  (weight: high)
- ID-01  Sepsis source identification & empiric antibiotics / stewardship
- ID-02  Skin & soft tissue infections, necrotizing fasciitis
- ID-03  UTI / pyelonephritis / catheter-associated
- ID-04  Meningitis & encephalitis
- ID-05  Endocarditis (see CARD-05)
- ID-06  C. difficile infection
- ID-07  Bone & joint infection (osteomyelitis, septic arthritis)
- ID-08  Fever of unknown origin, febrile neutropenia
- ID-09  HIV inpatient issues & opportunistic infection
- ID-10  Healthcare-associated / MDRO, antibiotic selection

## D. Nephrology & Acid-Base/Electrolytes  (weight: high)
- RENAL-01  Acute kidney injury (pre/intra/post-renal)
- RENAL-02  Hyponatremia / hypernatremia
- RENAL-03  Potassium disorders
- RENAL-04  Acid-base disorders (mixed disturbances)
- RENAL-05  Calcium / phosphate / magnesium disorders
- RENAL-06  CKD inpatient management, indications for dialysis
- RENAL-07  Rhabdomyolysis, contrast nephropathy

## E. Gastroenterology & Hepatology  (weight: medium)
- GI-01  Upper & lower GI bleeding
- GI-02  Acute pancreatitis
- GI-03  Cirrhosis & its complications (ascites, SBP, HRS, varices)
- GI-04  Acute liver failure, drug-induced liver injury
- GI-05  Inflammatory bowel disease flare
- GI-06  Bowel obstruction, ischemia
- GI-07  Hepatic encephalopathy

## F. Endocrinology  (weight: medium)
- ENDO-01  DKA & hyperosmolar hyperglycemic state
- ENDO-02  Inpatient glycemic management
- ENDO-03  Thyroid storm & myxedema coma
- ENDO-04  Adrenal insufficiency / crisis
- ENDO-05  Pituitary emergencies, SIADH (see RENAL-02)
- ENDO-06  Pheochromocytoma, hypercalcemia of malignancy

## G. Hematology & Oncology  (weight: medium)
- HEME-01  Anemia workup (inpatient)
- HEME-02  Thrombocytopenia, HIT, TTP/HUS
- HEME-03  Anticoagulation & reversal, DOAC management
- HEME-04  VTE prophylaxis & treatment
- HEME-05  Oncologic emergencies (tumor lysis, cord compression, SVC, hypercalcemia)
- HEME-06  Transfusion medicine & reactions
- HEME-07  Sickle cell crisis
- HEME-08  Febrile neutropenia (see ID-08)

## H. Neurology  (weight: medium)
- NEURO-01  Acute ischemic stroke & TIA
- NEURO-02  Intracranial hemorrhage
- NEURO-03  Seizure & status epilepticus
- NEURO-04  Altered mental status / delirium
- NEURO-05  Acute weakness (GBS, myasthenic crisis, cord)
- NEURO-06  Headache — dangerous causes

## I. Rheumatology & Immunology  (weight: low)
- RHEUM-01  Acute mono/polyarthritis, crystal arthropathy
- RHEUM-02  Systemic vasculitis, GCA
- RHEUM-03  SLE flare & complications
- RHEUM-04  Anaphylaxis, drug hypersensitivity

## J. General & Perioperative Hospital Medicine  (weight: high)
- GEN-01  Perioperative risk assessment & medical consultation
- GEN-02  Perioperative anticoagulation / antiplatelet bridging
- GEN-03  Delirium prevention & management (see NEURO-04)
- GEN-04  Pain management & opioid stewardship
- GEN-05  Alcohol withdrawal & substance use
- GEN-06  Nutrition, refeeding syndrome
- GEN-07  Venous thromboembolism prophylaxis (see HEME-04)
- GEN-08  Palliative & end-of-life care, goals of care
- GEN-09  Transitions of care, discharge safety, readmission
- GEN-10  Diagnostic reasoning & cognitive bias (meta-skill; good for CPC essays)
- GEN-11  Patient safety, quality improvement, high-value care
- GEN-12  Fluid & electrolyte therapy, maintenance fluids

## K. Emergencies / Toxicology  (weight: medium)
- TOX-01  Common poisonings & antidotes (acetaminophen, salicylate, TCA, etc.)
- TOX-02  Serotonin syndrome / NMS / malignant hyperthermia
- TOX-03  Environmental (hypothermia, hyperthermia)
- EMRG-01 Anaphylaxis (see RHEUM-04)
- EMRG-02 Acute agitation, behavioral emergency
