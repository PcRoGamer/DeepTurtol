# BME 305: Biomedical Signal Processing — Guest Lecture Notes

**Guest Lecturer:** Prof. Sarah Chen (Computer Science)
**Host Instructor:** Dr. Emily Watson (Biomedical Engineering)
**Date:** March 18, 2026
**Topic:** AI-Assisted Medical Diagnosis: Few-Shot Learning in Medicine

---

## 1. Introduction

Dr. Watson introduced me (Prof. Chen) by explaining that medical diagnosis is often a **pattern recognition task** — but one where the number of examples per condition can be very small. This is the fundamental challenge that few-shot learning addresses.

## 2. Why Few-Shot Learning Matters in Medicine

In clinical practice:
- A dermatologist may see **fewer than 10 cases** of a rare skin condition in their career.
- A radiologist encountering a rare tumor subtype may have **only 3–5 reference cases** from their training.
- New diseases (like COVID-19 in early 2020) require rapid model development with **extremely limited data**.

Standard deep learning requires hundreds to thousands of labeled examples. This creates a fundamental mismatch between what algorithms need and what medicine provides.

### The Data Scarcity Problem

| Domain | Typical labeled examples | Needed for standard DL |
|--------|-------------------------|----------------------|
| Common skin conditions | 100–500 | ✓ Sufficient |
| Rare skin conditions | 20–80 | ✗ Insufficient |
| Rare tumors | 5–30 | ✗ Insufficient |
| Emerging diseases | 0–50 | ✗ Insufficient |

## 3. Few-Shot Learning: The Core Idea

Few-shot learning aims to **learn to learn** — the model is trained not to classify specific images, but to **generalize from few examples at test time**. The key insight is that the model uses its pre-existing knowledge (learned from many examples of other conditions) to rapidly adapt to new conditions.

### Prototypical Networks

The approach our collaboration uses (see biomedical_ml_collab.md):

1. **Encode** each support image into a 64-dimensional embedding using a pretrained ResNet-18.
2. **Compute a prototype** for each class as the mean of its support embeddings.
3. **Classify** a query image by finding the nearest prototype.

With 5 examples per class (5-shot), our system achieves **73.5% accuracy** across 15 dermatological conditions.

### Cross-Attention Enhancement

Standard Prototypical Networks treat each support example independently when computing prototypes. Our innovation (developed in Prof. Chen's CS 301 capstone project, see capstone_ml_medical.md) adds **cross-attention** between support examples:

- Each support embedding attends to other support embeddings in the same class.
- This captures **within-class variation** (e.g., different presentations of the same disease).
- We apply **sparse attention** (inspired by Prof. Chen's ASA framework) to prevent overfitting.

## 4. Clinical Applications

### 4.1 Dermoscopy

Our primary application is classifying skin lesions from dermoscopy images. We have curated a dataset of 1,200 images across 15 conditions, ranging from common (melanoma) to very rare (Hailey-Hailey disease).

### 4.2 Potential Extensions

- **Histopathology:** Few-shot classification of tissue samples from biopsies.
- **Radiology:** Identifying rare findings in chest X-rays or MRI scans.
- **Ophthalmology:** Detecting rare retinal conditions from fundus images.

## 5. Interactive Demo

I demonstrated a live few-shot classification system using our trained model:

1. Showed 5 support images of each of 3 conditions.
2. Fed in a query image the model had never seen.
3. The model correctly classified it in <100ms.
4. Showed attention heatmaps highlighting which support images the model focused on.

Student questions:
- "How does the model handle images that don't match any known condition?"
  → We are developing **uncertainty estimation** to flag out-of-distribution inputs.
- "Could this work with non-image data, like lab results?"
  → Yes, few-shot learning applies to any modality. The key is the embedding space.

## 6. Collaboration Opportunities

I encouraged BME 305 students interested in AI-assisted diagnosis to:
1. **Take CS 201** (Prof. Liu's Introduction to ML) as an elective.
2. **Contact Dr. Watson** about research opportunities in the biomedical ML collaboration.
3. **Attend CS 490 seminar** (Prof. Chen's Advanced Topics) for exposure to cutting-edge ML research.

## 7. Connection to Course Sequence

This lecture connects to several courses in the ML sequence:

- **CS 201 (Prof. Liu):** ResNet architectures, transfer learning, and image classification fundamentals taught in CS 201 are the building blocks of few-shot medical imaging.
- **MATH 205 (Prof. Rodriguez):** Eigenvalue theory and dimensionality reduction underpin the embedding spaces used in Prototypical Networks.
- **STAT 210 (Prof. Brown):** Bayesian inference provides the theoretical framework for understanding why few-shot learning works — it is a form of rapid Bayesian updating.
- **CS 301 (Prof. Chen):** Transformer attention and sparse attention mechanisms directly power our cross-attention prototype refinement.

## 8. Acknowledgments

This work is supported by NSF Grant #IIS-2024567 and the University's Interdisciplinary Research Initiative. The dermoscopy dataset was curated by Alex Kim, Priya Sharma, and Marcus Johnson under IRB Protocol #2025-0847.

---

*Prof. Chen's office: Engineering Building Room 312. Dr. Watson's office: BME Building Room 205.*
