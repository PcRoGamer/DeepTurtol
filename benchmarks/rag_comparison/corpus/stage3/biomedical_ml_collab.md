# Biomedical ML Collaboration: Few-Shot Rare Disease Diagnosis

**Project:** Chen–Watson Joint Initiative
**PIs:** Prof. Sarah Chen (Computer Science) and Dr. Emily Watson (Biomedical Engineering)
**Team:** Alex Kim, Priya Sharma, Marcus Johnson
**Status:** Two papers in preparation (as of April 2026)

---

## 1. Background

The diagnosis of rare skin conditions from dermoscopy images is a significant clinical challenge. There are approximately 3,000 known dermatological conditions, but the vast majority are seen fewer than 10 times in a typical dermatologist's career. This data scarcity makes it impossible to apply standard deep learning approaches that require hundreds or thousands of labeled examples per class.

## 2. Collaboration Model

This project represents a model for interdisciplinary collaboration between computer science and biomedical engineering:

- **Prof. Sarah Chen** brings expertise in few-shot learning, meta-learning, and the ASA (Adaptive Sparse Attention) framework. Her contributions include the algorithmic design, attention mechanism innovations, and theoretical analysis.
- **Dr. Emily Watson** provides clinical domain expertise, the dermoscopy image dataset, and clinical validation. Her BME 305 course (where Prof. Chen delivers guest lectures) provides a natural pipeline of students interested in medical AI.
- **Alex Kim** contributes expertise in efficient attention and sparse optimization, implementing the ASA-inspired components.
- **Priya Sharma** contributes meta-learning expertise from her literature review (see research_essay_few_shot.md) and capstone project (see capstone_ml_medical.md).
- **Marcus Johnson** provides medical image processing expertise and handles the data pipeline.

## 3. Dataset

The team has curated a dataset of **1,200 dermoscopy images** spanning **15 dermatological conditions**:

| Condition | # Images | Rarity |
|-----------|----------|--------|
| Melanoma | 150 | Common |
| Basal cell carcinoma | 120 | Common |
| Dermatofibroma | 95 | Moderate |
| Psoriasis | 90 | Moderate |
| Lichen planus | 85 | Moderate |
| Pemphigus vulgaris | 72 | Rare |
| Cutaneous T-cell lymphoma | 65 | Rare |
| Dermatomyositis | 60 | Rare |
| Bullous pemphigoid | 58 | Rare |
| Scleroderma | 55 | Very rare |
| Morphea | 52 | Very rare |
| Vitiligo (atypical) | 48 | Very rare |
| Lupus erythematosus (cutaneous) | 45 | Very rare |
| Porphyria cutanea tarda | 42 | Very rare |
| Hailey-Hailey disease | 43 | Very rare |

The dataset has been de-identified and approved by the university IRB (Protocol #2025-0847).

## 4. Technical Approach

The technical approach builds on Priya Sharma's capstone work (see capstone_ml_medical.md):

1. **Prototypical Networks** with cross-attention refinement.
2. **ASA-inspired sparsity** to regularize attention in the few-shot regime.
3. **Transfer learning** from ImageNet-pretrained ResNet-18 as the embedding backbone.
4. **Test-time augmentation** (horizontal flip, color jitter) to boost few-shot accuracy.

### Key Results (Preliminary)

- **5-shot accuracy:** 73.5% (vs. 68.2% baseline ProtoNet)
- **10-shot accuracy:** 77.8%
- **1-shot accuracy:** 58.3%
- **AUROC for rare vs. common conditions:** 0.81

## 5. Publications in Preparation

### Paper 1: "Sparse Attention for Few-Shot Medical Image Classification"
- **Focus:** Algorithmic contributions — ASA-inspired attention for Prototypical Networks.
- **Target venue:** MICCAI 2027 (Medical Image Computing).
- **Lead authors:** Priya Sharma, Sarah Chen.

### Paper 2: "A Curated Dermoscopy Dataset for Few-Shot Learning Research"
- **Focus:** Dataset paper — description, benchmarking, clinical validation.
- **Target venue:** Scientific Data (Nature).
- **Lead authors:** Emily Watson, Marcus Johnson, Sarah Chen.

## 6. Future Directions

1. **Multi-center validation:** Partner with hospitals in 3 other cities.
2. **Clinical decision support:** Integrate the model into Dr. Watson's clinical workflow.
3. **Active learning:** Use model uncertainty to guide which images to label next.
4. **Extension to histopathology:** Apply few-shot learning to microscopic tissue images.

## 7. Acknowledgments

Funded by the National Science Foundation (Grant #IIS-2024567) and the University's Interdisciplinary Research Initiative.

---

*See also: prof_chen_research.md, capstone_ml_medical.md, alex_kim_notes.md, watson_biomed_notes.md.*
