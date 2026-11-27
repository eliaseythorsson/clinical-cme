# Blueprint citations check, 2026-11-27 (issue #89)

Follow-up to the three earlier passes on the default blueprint
(`plugins/clinical-cme/skills/clinical-cme/templates/blueprint.md`, with `blueprint.json` regenerated from it by
`cme.py blueprint-md`). It covers the 138 citations those passes did not confirm.

**Result:** 128 current, 5 corrected, 5 uncertain. 53 were searched in this pass (about one
or two searches each, starting with the most-used and those most likely to have a new edition).
The other 85 were not searched one by one: no newer edition is known for them, and the rolling
sweep at preparation (#90) will check them first. Authors and checkers still verify the evidence
for every round.

**Corrections applied** (each tag changed wherever it appears):

- `NICE NG89 2019` → `NICE NG89 2018, updated 2025`
- `EGS 2020` → `EGS 2025` (6th edition)
- `EADO cSCC 2023` → `EADO cSCC 2026`
- `ECCO infections 2021` → `ECCO infections 2026`
- `ESsCD coeliac 2019` → `ESsCD coeliac 2025`

**CARD-02c label.** The ESC HF 2026 guideline drops the mildly reduced category: an LVEF of
41 to 49% now counts as HFrEF, and HFpEF means an LVEF of 50% or more
([ESC press release](https://www.escardio.org/news/press/press-releases/major-changes-made-to-the-esc-guidelines-on-heart-failure/)).
The label changes from "HFpEF and mildly reduced EF" to "HFpEF and the former mildly reduced EF
range". The id and decision points stay the same, and the fourth point already describes the
new rule. The same label is changed in `docs/blueprint-v2.md`.

**Uncertain** (tags kept for now):

- Two EU driving directives: the recast Directive (EU) 2025/2205 has been adopted but is not yet
  transposed.
- ERS/ATS NIV 2017: ATS alone published a 2026 guideline on noninvasive respiratory support.
- The two CPOC perioperative diabetes tags: the year of the latest edition could not be confirmed.

| Citation | Uses | Verdict | Basis | Note | Source |
|---|---|---|---|---|---|
| NICE NG89 2019 | 4 | corrected | searched | -> `NICE NG89 2018, updated 2025`. Published 2018; latest substantive change Sept 2025 (risk assessment after 12 h in A&E) | [link](https://www.nice.org.uk/guidance/ng89/chapter/update-information) |
| BSG IDA 2021 | 4 | current | searched | Current; BSG marks it due for update 2026 (2025 BSG/ACPGBI FIT guideline complements it) | [link](https://www.bsg.org.uk/clinical-resource/guidelines-iron-deficiency-anaemia-in-adults) |
| NICE NG234 2023 | 3 | current | not searched | No newer edition known; not individually searched this pass |  |
| IWGDF/IDSA 2023 | 3 | current | searched | 2027 update in development (due May 2027); 2023 is current | [link](https://iwgdfguidelines.org/guidelines-2027/) |
| EULAR infections 2022 | 3 | current | searched | 2022 EULAR screening/prophylaxis recommendations are the latest | [link](https://research.manchester.ac.uk/en/publications/2022-eular-recommendations-for-screening-and-prophylaxis-of-chron/) |
| ESE/Endocrine Society glucocorticoid-induced adrenal insufficiency 2024 | 3 | current | not searched | No newer edition known; not individually searched this pass |  |
| EADV bullous pemphigoid 2022 | 3 | current | searched | Updated S2k guideline 2022 is the latest | [link](https://pubmed.ncbi.nlm.nih.gov/35766904/) |
| NICE NG141 2019 | 2 | current | searched | No update found | [link](https://www.nice.org.uk/NG141) |
| JBDS/CPOC perioperative 2023 | 2 | uncertain | searched | CPOC diabetes guideline exists (2021, revised 2022); could not confirm a 2023 JBDS/CPOC edition | [link](https://cpoc.org.uk/guidelines-resources-guidelines-resources/guideline-diabetes) |
| IDSA infectious diarrhoea 2017 | 2 | current | searched | No newer IDSA guideline found | [link](https://pmc.ncbi.nlm.nih.gov/articles/PMC5848254) |
| FPM Opioids Aware | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESO TIA 2021 | 2 | current | searched | ESO guideline list shows 2021 as latest | [link](https://pubmed.ncbi.nlm.nih.gov/34414299) |
| ESCP diverticular disease 2020 | 2 | current | searched | No newer ESCP guideline found | [link](https://www.escp.eu.com/members/resources/resources-search/diverticular-disease) |
| ERS/ATS COPD exacerbations 2017 | 2 | current | searched | No newer joint guideline found | [link](https://www.guidelinecentral.com/guideline/7220/) |
| ERS HFNC 2022 | 2 | current | searched | No newer ERS HFNC guideline found | [link](https://pubmed.ncbi.nlm.nih.gov/34649974/) |
| EMA valproate SmPC | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| DRESS international consensus 2024 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| ATS OHS 2019 | 2 | current | searched | No newer ATS OHS guideline found | [link](https://thoracic.org/statements/guideline-implementation-tools/eval-and-mgmt-of-ohs.php) |
| WHO Global Patient Safety Action Plan 2021-2030 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| UEG/EMCG microscopic colitis 2021 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| PG Delphi criteria 2018 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG232 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| MHRA paracetamol 2012 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| Lyon 2.0 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| JBDS steroids 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| International PCOS guideline 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ICFSR frailty 2019 | 1 | current | searched | No newer ICFSR frailty guideline found | [link](https://pubmed.ncbi.nlm.nih.gov/31641726/) |
| GRADE diagnostic tests 2020 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| Fleischner 2017 | 1 | current | searched | No newer Fleischner nodule guideline found | [link](https://pubmed.ncbi.nlm.nih.gov/28240562/) |
| EWGSOP2 2019 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EU Directive 2006/126/EC, Annex III | 1 | uncertain | searched | Still in force, but recast Directive (EU) 2025/2205 has been adopted; national transposition pending. Revisit when it applies | [link](https://eur-lex.europa.eu/eli/dir/2025/2205/oj) |
| ESPEN nutrition and hydration in dementia 2024 | 1 | current | searched | Update 2024 is the latest | [link](https://cris.fau.de/publications/322803415) |
| ESO tenecteplase expedited recommendation 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESO PFO 2024 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESNM/UEG constipation 2020 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESHRE premature ovarian insufficiency 2024 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESAIC postoperative delirium 2024 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ERS/ATS non-invasive ventilation 2017 | 1 | uncertain | searched | No joint ERS/ATS update, but ATS alone issued a noninvasive respiratory support guideline (AJRCCM, June 2026); scope vs 2017 not confirmed | [link](https://connect.uclahealth.org/dom/2026/06/30/noninvasive-respiratory-support-for-adult-patients-with-acute-respiratory-failure-an-official-american-thoracic-society-clinical-practice-guideline/) |
| EMHG 2020 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ECTS denosumab discontinuation 2021 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EASL PBC 2025 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EANM/SNMMI FDG-PET infection 2013 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EAACI beta-lactam hypersensitivity 2020 | 1 | current | searched | No newer EAACI beta-lactam position paper found (2025 EAACI item is a biomarker task-force report) | [link](https://pubmed.ncbi.nlm.nih.gov/31749148/) |
| CCB poisoning expert consensus 2017 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| BSH thrombophilia 2022 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ASGE colonic pseudo-obstruction 2020 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| AAO-HNS sudden hearing loss 2019 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| AACT/EAPCCT single-dose charcoal position 2005 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ADA Standards of Care 2026 | 4 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG31 2015 | 3 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG225 2022 | 3 | current | not searched | No newer edition known; not individually searched this pass |  |
| EFNS Wernicke 2010 | 3 | current | searched | No EAN replacement found | [link](https://www.qxmd.com/r/20642790) |
| SfE emergency hypocalcaemia 2016 | 2 | current | searched | No newer SfE emergency guidance found | [link](https://pubmed.ncbi.nlm.nih.gov/32022081) |
| NICE low back pain NG59 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG217 2022 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE CG178 2014 | 2 | current | searched | Still active (2025 exceptional surveillance, no replacement) | [link](https://www.nice.org.uk/guidance/cg178) |
| EULAR infection screening points to consider 2022 | 2 | current | searched | Same 2022 EULAR document | [link](https://research.manchester.ac.uk/en/publications/2022-eular-recommendations-for-screening-and-prophylaxis-of-chron/) |
| ESVS chronic venous disease 2022 | 2 | current | searched | ESVS page still lists 2022 as current | [link](https://esvs.org/?p=331091) |
| ESID diagnostic criteria 2019 | 2 | current | searched | 2019 working definitions still the latest found | [link](https://discovery-pp.ucl.ac.uk/id/eprint/10068520) |
| EAPC dementia white paper 2014 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| EAACI/ENDA drug provocation testing 2024 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| Council of the EU cancer screening 2022 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| ACCP perioperative antithrombotic 2022 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| STOPPFrail v2 2021 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| SNAP regimen | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG42 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG128 2019 | 1 | current | searched | Updated since (2022 ICH blood pressure, 2025 links) but the thromboprophylaxis point is unchanged since 2019 | [link](https://www.nice.org.uk/guidance/ng128/chapter/Update-information) |
| NICE NG116 2018 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE CG173 2020 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| Lugano 2014 | 1 | current | searched | Still reprinted unchanged in NCCN 2026 | [link](https://geiselmed.dartmouth.edu/radiology/wp-content/uploads/sites/47/2026/01/Lugano-Response-Criteria-2026.pdf) |
| Icelandic Legal Competence Act 71/1997 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| Hunter criteria 2003 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| GRADE 2011 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EXTRIP salicylates 2015 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ETA amiodarone 2018 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESMO survivorship 2022 | 1 | current | searched | 2022 expert consensus statements are the latest | [link](https://pubmed.ncbi.nlm.nih.gov/35963481/) |
| ESCEO knee osteoarthritis 2019 | 1 | current | searched | No newer ESCEO algorithm found | [link](https://pubmed.ncbi.nlm.nih.gov/31126594/) |
| EAPC advance care planning 2017 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EAN/PNS CIDP 2021 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| Choosing Wisely SHM 2013 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| Bárány Society vestibular neuritis criteria 2022 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| AAO-HNS epistaxis 2020 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| UK TOXBASE | 9 | current | not searched | No newer edition known; not individually searched this pass |  |
| Icelandic Patients' Rights Act 74/1997 | 3 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG5 2015 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG202 2021 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE CG113 2011 | 2 | current | searched | Still active; latest changes 2024 (presentational) and 2026 (link) | [link](https://www.nice.org.uk/guidance/CG113/chapter/update-information) |
| Fifth International Workshop on primary hyperparathyroidism 2022 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| EXTRIP methanol 2015 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| ETA subclinical hypothyroidism 2013 | 2 | current | searched | ETA 2025 guideline covers LT4 therapy of hypothyroidism generally, not subclinical disease | [link](https://eprints.ncl.ac.uk/309310) |
| ESVS carotid 2023 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESPEN geriatrics 2022 | 2 | current | searched | No newer edition found | [link](https://ueaeprints.uea.ac.uk/id/eprint/67392/) |
| ESE immune checkpoint inhibitor endocrinopathies 2022 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| ERS chronic cough 2020 | 2 | current | searched | No newer ERS guideline found | [link](https://publications.ersnet.org/content/erj/55/1/1901136) |
| EADO melanoma diagnostics 2024 | 2 | current | searched | Part 1 Diagnostics, Update 2024 is the latest | [link](https://melanoma.org.au/paper/european-consensus-based-interdisciplinary-guideline-for-melanoma-part-1-diagnostics-update-2024-2/) |
| DSM-5-TR 2022 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| CHCC dermatologic addendum 2018 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| BSG chronic diarrhoea 2018 | 2 | current | searched | 3rd edition still current on BSG site | [link](https://www.bsg.org.uk/clinical-resource/bsg-guidelines-chronic-diarrhoea) |
| ASAS-EULAR axSpA 2022 | 2 | current | not searched | No newer edition known; not individually searched this pass |  |
| WHO TB module 3 2025 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| UK multidisciplinary consensus on GLP-1 RA and SGLT2i (Anaesthesia) 2025 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| STOPPFall 2021 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| RCP NEWS2 2017 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE heavy menstrual bleeding NG88 2018 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE NG27 2015 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE CG91 2009 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE CG185 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| NICE CG143 2012 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| MASCC/ESMO antiemesis 2023 | 1 | current | searched | ESMO page lists 2023 update | [link](https://esmo.org/guidelines/supportive-and-palliative-care/prevention-of-chemotherapy-and-radiotherapy-induced-nausea-and-vomiting) |
| KDIGO transplant recipient 2009 | 1 | current | searched | No newer recipient guideline found (2020 KDIGO covers candidates) | [link](https://pubmed.ncbi.nlm.nih.gov/19845597/) |
| JBDS Diabetes at the Front Door 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| IWGDF 2023 | 1 | current | searched | As above | [link](https://iwgdfguidelines.org/guidelines-2027/) |
| IIH UK consensus 2018 | 1 | current | searched | No newer UK consensus found | [link](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6166610/) |
| ICHD-3 2018 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| Global cryptococcosis 2024 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| GIRFT national suspected CES pathway 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| European trauma bleeding 2023 | 1 | current | searched | Sixth edition (2023) is the latest | [link](https://link.springer.com/article/10.1186/s13054-023-04327-7) |
| EXTRIP ethylene glycol 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EULAR/ACR myositis classification 2017 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EULAR fibromyalgia 2016 | 1 | current | searched | No newer EULAR recommendations found | [link](https://pubmed.ncbi.nlm.nih.gov/27377815/) |
| EU Directive 2014/85/EU | 1 | uncertain | searched | Amends 2006/126/EC Annex III; same status as above (Directive (EU) 2025/2205 adopted) | [link](https://eur-lex.europa.eu/eli/dir/2025/2205/oj) |
| ESsCD coeliac 2019 | 1 | corrected | searched | -> `ESsCD coeliac 2025`. ESsCD 2025 updated guidelines (UEG Journal) replace 2019 | [link](https://pure.amsterdamumc.nl/en/publications/european-society-for-the-study-of-coeliac-disease-2025-updated-gu/) |
| ESO-ESMINT thrombectomy 2019, expedited update 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESO secondary prevention 2022 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESO CeAD 2021 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ESMO dyspnoea 2020 | 1 | current | searched | ESMO page lists 2020 as current | [link](https://www.esmo.org/guidelines/supportive-and-palliative-care/dyspnoea-in-advanced-cancer-patients) |
| ESGE small-bowel 2022 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ERS/EACTS MPE 2018 | 1 | current | searched | No newer ERS/EACTS statement found | [link](https://pubmed.ncbi.nlm.nih.gov/30054348/) |
| ENETS functioning pancreatic NET 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| EGS 2020 | 1 | corrected | searched | -> `EGS 2025`. EGS Terminology and Guidelines 6th edition (2025) replaces the 5th (2020) | [link](https://www.medthority.com/guidelines/glaucoma/european-glaucoma-society---terminology-and-guidelines-for-glaucoma-6th-edition) |
| ECCO infections 2021 | 1 | corrected | searched | -> `ECCO infections 2026`. Updated ECCO infections-in-IBD guideline, J Crohns Colitis 2026 (announced Dec 2025) | [link](https://ecco-ibd.eu/publications/news/issues/2025/volume-20-issue-4/new-ecco-guidelines-on-opportunistic-infections-in-ibd-2025-update) |
| EANO-ESMO brain metastases 2021 | 1 | current | searched | ESMO page lists 2021 as current | [link](https://www.esmo.org/guidelines/neuro-oncology/brain-metastasis-from-solid-tumours) |
| EADO cSCC 2023 | 1 | corrected | searched | -> `EADO cSCC 2026`. EADO/EDF invasive cSCC guideline 'Update 2026' (Eur J Cancer, May 2026) updates the 2023 version | [link](https://guidelines.edf.one//uploads/attachments/cmqj4slax3esoqtjrjdsl8de3-stratigos-dessinioti-ejc-cscc-2026-part1.pdf) |
| CPOC perioperative diabetes 2022 | 1 | uncertain | searched | Same guideline as above; year of latest revision not confirmed from the CPOC page | [link](https://cpoc.org.uk/guidelines-resources-guidelines-resources/guideline-diabetes) |
| BTS bronchiectasis 2019 | 1 | current | searched | Latest BTS guideline (ERS has a 2025 guideline, a different body) | [link](https://www.respiratoryfutures.org.uk/health-condition-resources/bronchiectasis/british-thoracic-society-guideline-for-bronchiectasis-in-adults) |
| BAP catatonia 2023 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| ACR/EULAR RA classification 2010 | 1 | current | not searched | No newer edition known; not individually searched this pass |  |
| AAO-HNS BPPV 2017 | 1 | current | searched | 2017 update still the latest; 2026 news items are a study, not a new guideline | [link](https://www.entnet.org/resource/aao-hnsf-updated-cpg-bppv-press-release-fact-sheet/) |
