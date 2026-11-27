# Blueprint v2 (proposal for #82)

**Status: applied** (#82). This is now the default blueprint, `skills/clinical-cme/templates/blueprint.md`
and `blueprint.json`, with the decision points and aspect importance per sub-topic; weights
there are the shares below scaled so that the largest, 14%, is 1.0. The retired ids stay listed,
marked `(retired)`, so that old ledgers keep resolving them. An existing learner moves onto it
through `settings --blueprint` and a mapping (`references/state_schema.md` §9).

144 diseases and 347 sub-topics in 16 areas, for the two-level blueprint of #81: **the
disease returns on schedule; the sub-topic rotates and is recorded.**

- **Skeleton**: the ABIM Internal Medicine certification blueprint (general), for breadth. This
  is our own classification informed by it, not a copy.
- **What is correct**: European guidelines (rule 2 of `references/standards.md`). Decision
  points (two to five per sub-topic, each with the guideline it rests on) are written by the
  builder and are not listed here (they are in the template).
- **Areas**: the existing area codes are kept; `DERM`, `PSYCH`, `GERI` and `WH` are new.
  Allergy and immunology sit in `RHEUM`, eye and ENT in `GEN`, oncology in `HEME`;
  `TOX` and `EMRG` are one area (`TOX`).
- **IDs**: every existing disease ID is kept. *(new)* marks a new disease. Sub-topics are the
  disease ID plus a letter (`CARD-03a`).
- **Weights**: the share column is the starting weight, from ABIM's published percentages
  (areas ABIM does not have are set from hospital practice); the learner's emphasis applies on
  top. Where a sub-topic also appears in the ABIM *Internal Medicine: Inpatient* blueprint,
  its importance per task decides which aspect is tested most often.
- **Approved by the learner**: cardiology (format and grain), 2026-11-27. The other areas
  follow the same format; the decision points were delegated to the builder (#82).

| Area | Share | Diseases | Sub-topics |
|---|---|---|---|
| CARD Cardiology | 14% | 15 | 48 |
| HEME Haematology & Oncology | 11% | 14 | 38 |
| ID Infectious Disease | 9% | 15 | 34 |
| PULM Pulmonary & Critical Care | 9% | 13 | 31 |
| GI Gastroenterology & Hepatology | 9% | 12 | 31 |
| ENDO Endocrinology | 8% | 11 | 28 |
| RHEUM Rheumatology, Allergy & Immunology | 7% | 9 | 22 |
| RENAL Nephrology & Electrolytes | 7% | 9 | 23 |
| NEURO Neurology | 6% | 7 | 20 |
| GEN General Hospital Medicine | 6% | 11 | 19 |
| TOX Emergencies & Toxicology | 3% | 5 | 10 |
| PSYCH Psychiatry | 3% | 6 | 10 |
| GERI Geriatrics | 3% | 5 | 10 |
| DERM Dermatology | 2% | 5 | 8 |
| WH Women's Health | 2% | 4 | 8 |
| PERIOP Perioperative Medicine | 2% | 3 | 7 |
| **Total** | | **144** | **347** |

The first estimate was about 110 diseases; the count is 144 because the four new areas and the
splits add many small ones. Several have a single angle; the engine treats a disease with one
sub-topic as today's topic.

## CARD Cardiology

- **CARD-01 Acute coronary syndrome**: a) Recognition and triage · b) Reperfusion and timing of the invasive strategy · c) Antithrombotic therapy · d) Complications and care after infarction
- **CARD-09 Chronic coronary disease and chest pain** *(new)*: a) Work-up of stable chest pain · b) Antianginal and preventive therapy · c) Troponin rise without plaque rupture (type 2 infarction, MINOCA, spasm)
- **CARD-02 Heart failure**: a) Acute decompensation: relieving congestion · b) HFrEF: starting and sequencing therapy · c) HFpEF and mildly reduced EF · d) Precipitants, deterioration and shock
- **CARD-10 Cardiomyopathies** *(new)*: a) Hypertrophic · b) Dilated, including tachycardia- and alcohol-related · c) Restrictive and infiltrative; cor pulmonale
- **CARD-03 Atrial fibrillation**: a) Stroke prevention decision · b) Rate versus rhythm control and cardioversion · c) Antithrombotic combinations after PCI or ACS · d) New AF in acute illness or after surgery
- **CARD-04 Arrhythmias and conduction disease**: a) Bradycardia, AV block and pacing · b) Narrow-complex tachycardia · c) Wide-complex tachycardia and QT prolongation · d) Cardiac arrest and care after resuscitation
- **CARD-11 Syncope** *(new, from CARD-04)*: a) Initial evaluation and risk stratification · b) Reflex syncope and orthostatic hypotension · c) Cardiac syncope work-up
- **CARD-05 Valvular heart disease**: a) Aortic stenosis · b) Regurgitant lesions and mitral stenosis · c) Prosthetic valves
- **CARD-12 Infective endocarditis** *(new, from CARD-05; ID-05 points here)*: a) Diagnosis and imaging · b) Antimicrobial therapy, including oral step-down · c) Surgery, complications, prophylaxis, device infection
- **CARD-06 Hypertension** *(widened from hypertensive emergency)*: a) Hypertensive emergency · b) Raised blood pressure in the inpatient without organ damage · c) Chronic hypertension: diagnosis and targets · d) Secondary and resistant hypertension
- **CARD-07 Pericardial disease and myocarditis**: a) Acute and recurrent pericarditis · b) Effusion, tamponade, constriction · c) Myocarditis, including immune-checkpoint-inhibitor myocarditis
- **CARD-08 Pulmonary embolism** *(PULM-06 merges here)*: a) Diagnostic strategy · b) Risk stratification and reperfusion · c) Anticoagulant choice and duration
- **CARD-13 Aortic and peripheral vascular disease** *(new)*: a) Acute aortic syndromes · b) Aneurysm, peripheral arterial disease, acute limb ischaemia · c) Carotid disease
- **CARD-14 Lipids and cardiovascular prevention** *(new)*: a) Risk estimation and targets · b) Statin intolerance and add-on therapy
- **CARD-15 Adult congenital disease and murmurs** *(new)*: a) Septal defects, PFO, bicuspid valve · b) Evaluating a murmur

## HEME Haematology & Oncology

- **HEME-01 Anaemia**: a) Approach in the inpatient · b) Iron deficiency and anaemia of chronic disease · c) Macrocytic and megaloblastic anaemia
- **HEME-09 Haemolytic anaemia** *(was untracked)*: a) Autoimmune haemolysis · b) Non-immune haemolysis (G6PD, mechanical, microangiopathic approach)
- **HEME-02 Thrombocytopenia and thrombotic microangiopathy**: a) Approach and immune thrombocytopenia · b) Heparin-induced thrombocytopenia · c) TTP, HUS and complement-mediated TMA · d) Disseminated intravascular coagulation
- **HEME-03 Anticoagulation and reversal**: a) Choosing and monitoring an anticoagulant · b) Major bleeding and reversal · c) Anticoagulation in renal failure, extremes of weight, interactions
- **HEME-04 Venous thrombosis**: a) Deep vein thrombosis: diagnosis and treatment · b) Cancer-associated and unusual-site thrombosis · c) Thrombophilia testing and antiphospholipid syndrome
- **HEME-06 Transfusion**: a) Thresholds and choice of product · b) Transfusion reactions
- **HEME-07 Sickle cell disease and haemoglobinopathies**: a) Vaso-occlusive crisis and acute chest syndrome · b) Thalassaemia and long-term complications
- **HEME-10 Leukaemia and myelodysplasia** *(new)*: a) Acute leukaemia: recognition and emergencies · b) Chronic leukaemias · c) Myelodysplasia and unexplained cytopenia
- **HEME-11 Lymphoma and plasma cell disorders** *(new)*: a) Lymphoma: presentation and staging · b) Myeloma and monoclonal gammopathy
- **HEME-12 Myeloproliferative neoplasms** *(new)*: a) Polycythaemia, thrombocythaemia, myelofibrosis · b) Leucocytosis and eosinophilia: approach
- **HEME-05 Oncological emergencies**: a) Tumour lysis syndrome · b) Cord compression and brain metastases · c) Superior vena cava obstruction and malignant effusions · d) Hypercalcaemia and hyponatraemia of malignancy
- **HEME-08 Febrile neutropenia** *(ID-08's neutropenic fever points here)*: a) Risk stratification and empirical therapy · b) Persistent fever, neutropenic enterocolitis, invasive fungal infection
- **HEME-13 Solid tumours for the internist** *(new)*: a) Suspected cancer and unknown primary: work-up · b) Lung, breast, prostate, colorectal: staging and principles · c) Screening and prevention
- **HEME-14 Complications of cancer treatment** *(new)*: a) Immune-checkpoint-inhibitor toxicity · b) Chemotherapy toxicity (cardiac, neuropathy, emesis) · c) Survivorship and late effects

## ID Infectious Disease

- **ID-01 Sepsis: source and empirical antibiotics**: a) Recognition and finding the source · b) Empirical choice and resistance risk · c) De-escalation and duration
- **ID-02 Skin and soft tissue infection**: a) Cellulitis and abscess · b) Necrotising infection · c) Diabetic foot infection
- **ID-03 Urinary tract infection**: a) Cystitis, pyelonephritis, asymptomatic bacteriuria · b) Catheter-associated and complicated infection, prostatitis
- **ID-04 Central nervous system infection**: a) Bacterial meningitis · b) Encephalitis · c) Brain and epidural abscess
- **ID-05 Bloodstream and line infection** *(was "Endocarditis", now CARD-12)*: a) Staphylococcus aureus bacteraemia · b) Catheter-related infection and candidaemia
- **ID-06 Clostridioides difficile**: a) Diagnosis and first episode · b) Recurrence and fulminant disease
- **ID-07 Bone and joint infection**: a) Septic arthritis · b) Osteomyelitis, vertebral and prosthetic infection
- **ID-08 Fever syndromes**: a) Fever of unknown origin · b) Fever in the returning traveller
- **ID-09 HIV**: a) New diagnosis and timing of antiretroviral therapy · b) Opportunistic infections and prophylaxis · c) Immune reconstitution and long-term complications
- **ID-10 Healthcare-associated and resistant organisms**: a) Treating resistant organisms (ESBL, carbapenemase producers, MRSA, VRE) · b) Infection control and post-exposure prophylaxis
- **ID-11 Invasive fungal infection** *(was untracked)*: a) Aspergillosis and other moulds · b) Candida and cryptococcus
- **ID-12 Tuberculosis** *(new)*: a) Diagnosis and isolation · b) Treatment and latent infection
- **ID-13 Abdominal and hepatobiliary infection** *(new)*: a) Intra-abdominal infection and abscess · b) Viral hepatitis: acute presentation and exposure
- **ID-14 Sexually transmitted and genital infection** *(new)*: a) Syphilis · b) Urethritis, pelvic infection, genital ulcers
- **ID-15 Prevention and the immunocompromised host** *(new)*: a) Adult immunisation · b) Infection on immunosuppressants and after transplant

## PULM Pulmonary & Critical Care

- **PULM-01 Pneumonia**: a) Community-acquired: severity and empirical therapy · b) Hospital-acquired and ventilator-associated · c) Non-resolving pneumonia, aspiration, complications
- **PULM-02 COPD**: a) Exacerbation · b) Non-invasive ventilation and respiratory failure · c) Stable disease: treatment
- **PULM-03 Asthma**: a) Acute severe asthma · b) Long-term treatment and mimics
- **PULM-04 Respiratory failure and ventilation**: a) Hypoxaemic failure and oxygen delivery · b) Hypercapnic failure · c) ARDS and ventilator basics
- **PULM-05 Pleural disease**: a) Effusion: work-up · b) Parapneumonic effusion and empyema · c) Pneumothorax
- **PULM-06** *(retired: merged into CARD-08 Pulmonary embolism)*
- **PULM-07 Septic shock: resuscitation**: a) Fluids and vasopressors · b) Corticosteroids, adjuncts, source control
- **PULM-08 Shock**: a) Telling the types apart · b) Cardiogenic and obstructive shock · c) Hypovolaemic and haemorrhagic shock
- **PULM-09 Pulmonary hypertension** *(new)*: a) Recognition and classification · b) The decompensated right ventricle
- **PULM-10 Interstitial lung disease and sarcoidosis** *(new)*: a) Approach to diffuse lung disease · b) Specific diseases (fibrosis, hypersensitivity, connective tissue, drug) and acute exacerbation
- **PULM-11 Nodules, lung cancer and haemoptysis** *(new)*: a) The pulmonary nodule and suspected cancer · b) Haemoptysis
- **PULM-12 Sleep and hypoventilation** *(new)*: a) Obstructive sleep apnoea · b) Obesity hypoventilation and neuromuscular failure
- **PULM-13 Bronchiectasis and chronic cough** *(new)*: a) Bronchiectasis and cystic fibrosis in adults · b) Chronic cough and breathlessness: approach
- **PULM-14 Critical care for the ward physician** *(new)*: a) Recognising deterioration and escalation · b) Sedation, analgesia and life after intensive care

## GI Gastroenterology & Hepatology

- **GI-01 Gastrointestinal bleeding**: a) Upper, non-variceal · b) Variceal · c) Lower and obscure
- **GI-02 Pancreatitis**: a) Acute: diagnosis, severity, fluids and feeding · b) Complications and finding the cause · c) Chronic pancreatitis
- **GI-03 Cirrhosis**: a) Ascites and spontaneous bacterial peritonitis · b) Kidney injury and hepatorenal syndrome · c) Varices and portal hypertension · d) Decompensation, transplant referral, liver cancer surveillance
- **GI-07 Hepatic encephalopathy**: a) Diagnosis and precipitants · b) Treatment and prevention
- **GI-04 Acute liver failure and acute liver injury**: a) Recognition and referral · b) Drug-induced injury · c) Alcohol-related hepatitis
- **GI-08 Chronic liver disease** *(new)*: a) Abnormal liver tests and steatotic liver disease · b) Chronic viral hepatitis · c) Autoimmune, cholestatic and metabolic liver disease
- **GI-05 Inflammatory bowel disease**: a) Acute severe colitis · b) Crohn's disease: complications · c) Maintenance therapy and its risks
- **GI-06 Bowel obstruction and ischaemia**: a) Obstruction, ileus, pseudo-obstruction · b) Mesenteric ischaemia and ischaemic colitis
- **GI-09 Biliary disease** *(new)*: a) Gallstones and cholecystitis · b) Bile duct stones and cholangitis
- **GI-10 Oesophagus and stomach** *(new)*: a) Reflux, Barrett's, dysphagia · b) Peptic ulcer, Helicobacter, dyspepsia
- **GI-11 Diarrhoea and malabsorption** *(new)*: a) Acute diarrhoea in hospital and community · b) Chronic diarrhoea: coeliac disease, microscopic colitis, irritable bowel
- **GI-12 Colon** *(new)*: a) Colorectal cancer screening and polyps · b) Diverticular disease and constipation

## ENDO Endocrinology

- **ENDO-01 Hyperglycaemic emergencies**: a) Diagnosis: DKA, HHS, euglycaemic ketoacidosis · b) Fluids, insulin and potassium · c) Resolution, transition and the precipitant
- **ENDO-02 Inpatient glycaemic management**: a) Targets and insulin regimens · b) Steroids, feeding and procedures · c) Hypoglycaemia
- **ENDO-07 Diabetes: long-term management** *(new)*: a) Choice of glucose-lowering drug by comorbidity · b) Complications and screening · c) Type 1 and atypical diabetes
- **ENDO-03 Thyroid emergencies**: a) Thyroid storm · b) Myxoedema coma
- **ENDO-08 Thyroid disease** *(new)*: a) Hyperthyroidism and thyroiditis · b) Hypothyroidism and thyroid tests in illness · c) Nodules and cancer
- **ENDO-04 Adrenal insufficiency**: a) Diagnosis · b) Crisis, stress dosing and steroid withdrawal
- **ENDO-09 Adrenal excess and adrenal masses** *(new)*: a) Cushing's syndrome · b) Primary aldosteronism and endocrine hypertension · c) Incidentaloma and phaeochromocytoma
- **ENDO-06 Calcium and bone** *(was "Pheochromocytoma, hypercalcemia of malignancy")*: a) Hypercalcaemia · b) Osteoporosis and metabolic bone disease
- **ENDO-05 Pituitary and water balance**: a) Apoplexy and hypopituitarism · b) Pituitary tumours and hyperprolactinaemia · c) Arginine vasopressin deficiency and resistance
- **ENDO-10 Gonadal endocrinology** *(new)*: a) Male hypogonadism · b) Polycystic ovary syndrome and amenorrhoea
- **ENDO-11 Hypoglycaemia without diabetes and endocrine tumours** *(new)*: a) Hypoglycaemia in the non-diabetic · b) Neuroendocrine tumours and multiple endocrine syndromes

## RHEUM Rheumatology, Allergy & Immunology

- **RHEUM-01 Crystal arthritis and the acute joint**: a) The acute hot joint: approach · b) Gout flare: treatment with comorbidity and interactions · c) Urate lowering and flare prophylaxis; CPPD
- **RHEUM-02 Vasculitis**: a) Giant cell arteritis and polymyalgia · b) ANCA-associated vasculitis · c) Other vasculitides
- **RHEUM-03 Lupus and antiphospholipid syndrome**: a) Flare and organ involvement · b) Pregnancy, drugs and drug-induced lupus
- **RHEUM-04 Anaphylaxis and drug hypersensitivity** *(EMRG-01 points here)*: a) Anaphylaxis · b) Drug allergy and penicillin allergy assessment · c) Urticaria and angioedema
- **RHEUM-05 Rheumatoid arthritis** *(new)*: a) Diagnosis and systemic disease · b) Complications of DMARDs and biologics
- **RHEUM-06 Spondyloarthritis** *(new)*: a) Axial disease and inflammatory back pain · b) Psoriatic, reactive and enteropathic arthritis
- **RHEUM-07 Connective tissue disease** *(new)*: a) Systemic sclerosis and Raynaud's · b) Myositis · c) Sjögren's, adult Still's and overlap syndromes
- **RHEUM-08 Regional musculoskeletal problems** *(new)*: a) Back pain and its red flags · b) Osteoarthritis, soft tissue and fibromyalgia
- **RHEUM-09 Immunodeficiency** *(new)*: a) Antibody deficiency and recurrent infection · b) Secondary immunodeficiency

## RENAL Nephrology & Electrolytes

- **RENAL-01 Acute kidney injury**: a) Approach: pre-renal, intrinsic, obstructive · b) Tubular, interstitial and embolic causes · c) Cardiorenal and volume decisions
- **RENAL-02 Sodium**: a) Hyponatraemia: diagnosis · b) Hyponatraemia: treatment and overcorrection · c) Hypernatraemia
- **RENAL-03 Potassium**: a) Hyperkalaemia · b) Hypokalaemia and its work-up
- **RENAL-04 Acid-base**: a) Metabolic acidosis · b) Metabolic alkalosis · c) Respiratory and mixed disturbances
- **RENAL-05 Calcium, phosphate, magnesium**: a) Hypocalcaemia · b) Phosphate and magnesium
- **RENAL-06 Chronic kidney disease**: a) Progression and complications · b) Dialysis: indications and emergencies · c) Prescribing in kidney disease; the transplant recipient
- **RENAL-07 Rhabdomyolysis and toxic injury**: a) Rhabdomyolysis · b) Contrast and nephrotoxic drugs
- **RENAL-08 Glomerular disease** *(new)*: a) Nephritic syndrome and rapidly progressive disease · b) Nephrotic syndrome · c) Haematuria and proteinuria: work-up
- **RENAL-09 Stones and urology for the internist** *(new)*: a) Kidney stones · b) Retention, prostate disease, incontinence

## NEURO Neurology

- **NEURO-01 Ischaemic stroke and TIA**: a) Hyperacute care and reperfusion · b) TIA and secondary prevention · c) Stroke unit care and complications
- **NEURO-02 Intracranial haemorrhage**: a) Intracerebral haemorrhage · b) Subarachnoid haemorrhage
- **NEURO-03 Seizures**: a) First and provoked seizures · b) Status epilepticus · c) Antiseizure drugs and interactions
- **NEURO-04 Encephalopathy**: a) Approach to the confused or drowsy patient · b) Toxic and metabolic causes, including drug-induced hyperammonaemia
- **NEURO-05 Acute weakness**: a) Guillain-Barré syndrome · b) Myasthenia gravis and crisis · c) Spinal cord syndromes
- **NEURO-06 Headache: dangerous causes**: a) Thunderclap headache · b) Cervical artery dissection and venous sinus thrombosis · c) Raised pressure, giant cell arteritis, infection · d) Primary headache in hospital
- **NEURO-07 Movement, cognition and neuropathy** *(new)*: a) Parkinson's disease in hospital · b) Dementia: evaluation · c) Peripheral neuropathy and dizziness

## GEN General Hospital Medicine

- **GEN-03 Delirium**: a) Prevention and non-drug care · b) Drug treatment and its risks
- **GEN-04 Pain and opioids**: a) Acute pain with comorbidity · b) Opioid stewardship, conversion and dependence
- **GEN-05 Alcohol and substance withdrawal**: a) Alcohol withdrawal · b) Wernicke's and nutritional complications · c) Opioid and stimulant withdrawal
- **GEN-06 Nutrition**: a) Refeeding syndrome · b) Enteral and parenteral feeding decisions
- **GEN-07 Thromboprophylaxis**: a) Medical inpatients: who and how · b) Special populations
- **GEN-08 Palliative and end-of-life care**: a) Goals of care and capacity · b) Symptom control at the end of life
- **GEN-09 Transitions of care**: a) Discharge safety and medicines reconciliation
- **GEN-10 Diagnostic reasoning** *(meta-skill; no sub-topics)*
- **GEN-11 Safety, value and evidence**: a) Patient safety and high-value care · b) Reading tests and studies; ethics
- **GEN-12 Fluid therapy**: a) Maintenance and resuscitation fluids
- **GEN-13 Eye and ENT for the internist** *(new)*: a) Red eye and acute visual loss · b) Vertigo, epistaxis, hearing loss

## TOX Emergencies & Toxicology (TOX and EMRG merged)

- **TOX-01 Poisoning**: a) Paracetamol · b) Salicylate, tricyclic and other common poisonings · c) Toxic alcohols and the unknown overdose
- **TOX-02 Drug-induced hyperthermia**: a) Serotonin syndrome · b) Neuroleptic malignant syndrome and malignant hyperthermia
- **TOX-03 Environmental emergencies**: a) Hypothermia · b) Heat illness, carbon monoxide, altitude
- **EMRG-02 Acute agitation**: a) Rapid tranquillisation and QT risk · b) The agitated patient: finding the cause
- **TOX-04 Opioid and sedative overdose** *(new)*: a) Recognition, antidotes and observation
- **EMRG-01** *(retired: anaphylaxis is RHEUM-04a)*

## PSYCH Psychiatry *(new area)*

- **PSYCH-01 Depression and suicide risk**: a) Depression in the medically ill · b) Suicide risk assessment
- **PSYCH-02 Psychosis and bipolar disorder**: a) Recognition on the medical ward · b) Adverse effects of psychotropic drugs (QT, metabolic, lithium)
- **PSYCH-03 Anxiety and functional disorders**: a) Anxiety, panic and post-traumatic stress · b) Somatic symptom and functional neurological disorder
- **PSYCH-04 Substance use disorder**: a) Long-term treatment and harm reduction
- **PSYCH-05 Eating disorders**: a) Medical complications and safe refeeding
- **PSYCH-06 Capacity and sleep**: a) Capacity, consent and detention · b) Insomnia in hospital

## GERI Geriatrics *(new area)*

- **GERI-01 Falls**: a) Assessment after a fall · b) Prevention, including medicines
- **GERI-02 Dementia in hospital**: a) Behavioural symptoms · b) Decisions in advanced dementia
- **GERI-03 Polypharmacy**: a) Deprescribing · b) Prescribing in frailty
- **GERI-04 Frailty and function**: a) Comprehensive assessment and frailty · b) Hip fracture and rehabilitation
- **GERI-05 Geriatric syndromes**: a) Incontinence and constipation · b) Swallowing, nutrition and pressure injury

## DERM Dermatology *(new area)*

- **DERM-01 Drug eruptions and skin emergencies**: a) Benign rash versus DRESS, SJS and TEN · b) Erythroderma and blistering disease
- **DERM-02 Inflammatory skin disease**: a) Eczema and psoriasis in the inpatient
- **DERM-03 Skin signs of systemic disease**: a) Purpura and vasculitic rash · b) Erythema nodosum, pyoderma and other reactive rashes
- **DERM-04 Skin lesions and cancer**: a) The suspicious lesion
- **DERM-05 Wounds and ulcers**: a) Leg ulcers · b) Pressure injury

## WH Women's Health *(new area)*

- **WH-01 Medical disorders in pregnancy**: a) Hypertension and pre-eclampsia · b) Thrombosis, heart and endocrine disease in pregnancy · c) Prescribing in pregnancy and breastfeeding
- **WH-02 Menopause and contraception**: a) Menopausal hormone therapy · b) Contraception with medical comorbidity
- **WH-03 Gynaecological presentations for the internist**: a) Abnormal bleeding and pelvic pain · b) Breast problems
- **WH-04 Osteoporosis in women** *(see ENDO-06b)*: a) Screening and treatment decisions

## PERIOP Perioperative Medicine

- **PERIOP-01 Risk assessment**: a) Cardiac risk and testing · b) Pulmonary and other risk · c) Managing regular medicines
- **PERIOP-02 Anticoagulants and antiplatelets around surgery**: a) Interrupting and bridging anticoagulation · b) Antiplatelets and stents
- **PERIOP-03 Medical complications after surgery** *(new)*: a) Post-operative AF, myocardial injury and delirium · b) Co-managing the surgical patient

## Changes to existing IDs

| ID | Change |
|---|---|
| CARD-04 | syncope moves to CARD-11 |
| CARD-05 | endocarditis moves to CARD-12 |
| CARD-06 | widened from hypertensive emergency to hypertension |
| PULM-06 | retired; merged into CARD-08 |
| ID-05 | was "Endocarditis (see CARD-05)"; now bloodstream and line infection |
| ID-08 | febrile neutropenia moves to HEME-08 |
| ENDO-06 | phaeochromocytoma moves to ENDO-09c; now calcium and bone |
| EMRG-01 | retired; anaphylaxis is RHEUM-04a |
| EMRG-02 | kept, in the merged TOX area |
| HEME-09, ID-11 | tested but not in the old blueprint; now listed |
| GEN-01, GEN-02 | in the default template only; they are PERIOP-01 and PERIOP-02 |
