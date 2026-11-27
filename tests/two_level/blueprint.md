<!-- A two-level sample for the tests (issue #81): the default blueprint with sub-topics under a few
     topics, CARD-04 retired into CARD-11, and CARD-12 new. Synthetic, frozen. -->

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

This default blueprint suits a hospitalist or general internist and is adapted from the
SHM Core Competencies in Hospital Medicine and the ABIM Internal Medicine certification
blueprint. For other specialties, the setup step drafts an equivalent blueprint in the
same format for you to check.

---

## A. Cardiology  (weight: high)
- CARD-01  Acute coronary syndrome (STEMI/NSTEMI/UA)
- CARD-02  Acute decompensated heart failure (HFrEF / HFpEF)
- CARD-03  Atrial fibrillation & rate/rhythm control, anticoagulation
  - CARD-03a  Stroke prevention decision  (aspects: management high, testing low)
    - Whether a score of one on the risk score calls for anticoagulation
    - Anticoagulation after an intracranial bleed
  - CARD-03b  Rate versus rhythm control and cardioversion  (aspects: management high, disposition medium)
    - Cardioversion without anticoagulation: the 24-hour window
  - CARD-03c  Antithrombotic combinations after PCI or ACS  (aspects: management high)
    - Length of triple therapy
    - Which antiplatelet stays with the anticoagulant
- CARD-05  Valvular disease & infective endocarditis
  - CARD-05a  Aortic stenosis
    - Timing of valve replacement in the asymptomatic patient
  - CARD-05b  Regurgitant lesions and mitral stenosis
- CARD-06  Hypertensive emergency/urgency
- CARD-07  Pericardial disease, myocarditis
- CARD-08  Venous thromboembolism — PE (see also PULM/HEME)
- CARD-11  Syncope and arrhythmias
- CARD-12  Infective endocarditis
  - CARD-12a  Diagnosis and imaging  (aspects: diagnosis high, testing high)
    - Repeat echocardiography after a negative first study
  - CARD-12b  Antimicrobial therapy, including oral step-down  (aspects: management high)
    - Criteria for oral step-down
  - CARD-12c  Surgery and complications

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
  - GI-02a  Diagnosis, severity, fluids and feeding
  - GI-02b  Complications and finding the cause
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
  - ENDO-06a  Hypercalcaemia
    - Bisphosphonate or denosumab in renal failure
  - ENDO-06b  Phaeochromocytoma

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
