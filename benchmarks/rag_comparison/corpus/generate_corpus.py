#!/usr/bin/env python3
"""Generate the 20-document education corpus for the RAG comparison benchmark."""

import json
import os
from pathlib import Path
from datetime import datetime

CORPUS_DIR = Path(__file__).parent

DOCUMENTS = [
    # ── Stage 1 (5 docs) ──────────────────────────────────────────────
    {
        "filename": "cs301_syllabus.md",
        "stage": "stage1",
        "category": "course_material",
        "content": """# CS 301: Advanced Machine Learning — Spring 2026

**Instructor:** Prof. Sarah Chen
**Office Hours:** Tuesdays 2:00–4:00 PM, Room 312 Engineering Building
**Lectures:** Mon/Wed/Fri 10:00–10:50 AM, Auditorium B
**Teaching Assistants:** Alex Kim, Priya Sharma

## Prerequisites

- **CS 201: Introduction to Machine Learning** (Prof. James Liu) — a solid grounding in regression, classification, and basic neural networks is expected.
- **MATH 205: Linear Algebra** (Prof. Maria Rodriguez) — matrix decompositions, eigenvalue theory, and vector-space geometry are used throughout the course.
- **STAT 210: Probability and Statistical Inference** (Prof. Thomas Brown) — probability distributions, Bayesian reasoning, and hypothesis testing form the statistical backbone of modern ML.

## Course Description

This course explores advanced topics in machine learning with a focus on transformer architectures, attention mechanisms, and reinforcement learning. Students will implement core algorithms from scratch, read and critique recent research papers, and complete a capstone project in small teams.

## Topics

1. **Backpropagation and Optimization** — automatic differentiation, SGD variants, Adam, learning-rate scheduling.
2. **Transformer Architectures** — self-attention, multi-head attention, positional encoding, layer normalization.
3. **Efficient Attention** — sparse attention patterns, linear attention approximations, Prof. Chen's Adaptive Sparse Attention (ASA) framework.
4. **Few-Shot and Meta-Learning** — Prototypical Networks, MAML, matching networks, and connections to few-shot medical imaging (see Prof. Chen's research profile).
5. **Reinforcement Learning** — MDPs, policy gradients, PPO, and applications in robotics.
6. **Generative Models** — VAEs, GANs, diffusion models, and attention-based sequence generation.
7. **Ethics and Safety** — bias, fairness, interpretability, and responsible deployment.

## Assessment

| Component          | Weight |
|--------------------|--------|
| Homework (4 sets)  | 40%    |
| Midterm Exam       | 15%    |
| Paper Reviews (3)  | 10%    |
| Capstone Project   | 35%    |

## Required Textbook

- Goodfellow, I., Bengio, Y., and Courville, A. *Deep Learning*. MIT Press, 2016.

## Connections to Other Courses

This course builds directly on the foundational material from Prof. James Liu's CS 201. The mathematical tools from MATH 205 (linear algebra) and the statistical reasoning from STAT 210 are essential for understanding the theoretical underpinnings of the algorithms we study. Students who have not completed these prerequisites should consult with the instructor before enrolling.

## Contact

For questions, email s.chen@university.edu or visit office hours.
"""
    },
    {
        "filename": "prof_chen_research.md",
        "stage": "stage1",
        "category": "research_essay",
        "content": """# Research Profile: Prof. Sarah Chen

## Background

Prof. Sarah Chen received her Ph.D. in Computer Science from the Massachusetts Institute of Technology in 2018 under the supervision of Prof. David Park. Her doctoral dissertation, *"Efficient Attention Mechanisms for High-Dimensional Data,"* introduced foundational ideas that later evolved into the Adaptive Sparse Attention (ASA) framework now used across several research groups.

Before MIT, Prof. Chen completed her B.S. in Computer Science at Stanford University, where she developed an early interest in the intersection of machine learning and healthcare.

## Research Interests

Prof. Chen's research spans three interconnected areas:

### 1. Sparse Attention and Efficient Transformers

Her signature contribution is the **Adaptive Sparse Attention (ASA)** mechanism, which dynamically selects which token relationships to model, reducing the quadratic complexity of standard self-attention to near-linear in practice. ASA has been applied to natural language processing, genomics, and medical image analysis. Key publications:

- Chen, S. et al. "Adaptive Sparse Attention for Scalable Transformers." *NeurIPS 2022*.
- Chen, S. and Park, D. "Sub-Linear Attention via Learned Sparsity Patterns." *ICML 2023*.

### 2. Few-Shot Learning

Prof. Chen's group has made significant contributions to few-shot classification, particularly in the context of Prototypical Networks with cross-attention refinement. Her current students Alex Kim, Priya Sharma, and Marcus Johnson are collaborating on few-shot medical image classification — a project that bridges sparse attention and few-shot learning in a clinically meaningful setting.

### 3. Medical Imaging with AI

In collaboration with Dr. Emily Watson (Department of Biomedical Engineering), Prof. Chen's lab is applying few-shot learning methods to rare disease diagnosis from dermoscopy images. The team has curated a dataset of 1,200 images spanning 15 dermatological conditions, and two papers are currently in preparation (see the biomedical collaboration notes for details).

## Lab Members

| Name             | Role          | Focus Area                          |
|------------------|---------------|--------------------------------------|
| Alex Kim         | Ph.D. Student | Sparse attention, ASA optimization   |
| Priya Sharma     | Ph.D. Student | Few-shot learning, meta-learning     |
| Marcus Johnson   | M.S. Student  | Medical imaging, Prototypical Nets   |

## Teaching

Prof. Chen teaches CS 301 (Advanced Machine Learning) and regularly co-supervises capstone projects in the CS department. She also delivers guest lectures in Dr. Emily Watson's BME 305 course on AI-assisted medical diagnosis.

## Collaborations

- **Prof. Maria Rodriguez** (Mathematics) — tensor decomposition methods for analyzing attention weight matrices.
- **Prof. James Liu** (Computer Science) — bridging introductory and advanced ML curricula; federated PCA for privacy-preserving student data analysis.
- **Dr. Emily Watson** (Biomedical Engineering) — few-shot rare disease diagnosis and clinical AI.
"""
    },
    {
        "filename": "math205_notes.md",
        "stage": "stage1",
        "category": "course_material",
        "content": """# MATH 205: Linear Algebra — Lecture Notes (Weeks 1–4)

**Instructor:** Prof. Maria Rodriguez
**Semester:** Spring 2026
**Room:** Mathematics Hall, Room 201

---

## Week 1: Systems of Linear Equations and Matrices

A *system of linear equations* is a collection of one or more linear equations involving the same variables. For example:

    2x + 3y − z = 1
    x −  y + 2z = 3
    3x + 2y +  z = 4

We represent such systems using an **augmented matrix**:

    [2   3  -1 | 1]
    [1  -1   2 | 3]
    [3   2   1 | 4]

**Gaussian elimination** transforms this matrix into *row echelon form* using elementary row operations:
1. Swap two rows.
2. Multiply a row by a nonzero scalar.
3. Add a multiple of one row to another.

A matrix is in **reduced row echelon form (RREF)** when every leading entry is 1 and is the only nonzero entry in its column. The RREF of a matrix is unique and directly reveals the solution set.

## Week 2: Matrix Operations and Inverses

The **product** of an *m×n* matrix *A* and an *n×p* matrix *B* is an *m×p* matrix *C* where:

    C_ij = Σ_k A_ik · B_kj

Key properties:
- Matrix multiplication is **associative** but **not commutative** in general.
- *A(B + C) = AB + AC* (distributive).
- *(AB)^T = B^T A^T* (transpose of a product).

A square matrix *A* is **invertible** if there exists *A⁻¹* such that *A A⁻¹ = I*. The **determinant** determines invertibility: *A* is invertible if and only if det(*A*) ≠ 0.

## Week 3: Vector Spaces

A **vector space** over ℝ is a set *V* equipped with vector addition and scalar multiplication satisfying closure, associativity, commutativity, identity, and distributivity axioms.

Important examples: ℝⁿ, the space of *m×n* matrices, the space of polynomials of degree ≤ n.

A **subspace** is a subset closed under addition and scalar multiplication. The **column space** and **null space** of a matrix *A* are fundamental subspaces.

**Basis and dimension:** A basis is a linearly independent spanning set. The dimension is the number of vectors in any basis.

### Connection to Machine Learning

Understanding vector spaces is critical for PCA (Principal Component Analysis), which finds low-dimensional subspaces that capture maximum variance. In Prof. Chen's CS 301, PCA appears in the context of efficient attention — projecting high-dimensional key and value matrices into lower-dimensional spaces to reduce compute. The SVD (Singular Value Decomposition), which we cover in Week 4, provides the computational backbone for PCA.

## Week 4: Eigenvalues and Eigenvectors

For a square matrix *A*, a scalar λ is an **eigenvalue** and a nonzero vector **v** is an **eigenvector** if:

    A **v** = λ **v**

The **characteristic polynomial** det(*A* − λ*I*) = 0 yields the eigenvalues. The **eigenspace** for λ is the null space of (*A* − λ*I*).

**Diagonalization:** If *A* has *n* linearly independent eigenvectors, then *A = PDP⁻¹* where *D* is diagonal. This dramatically simplifies matrix powers: *A^k = P D^k P⁻¹*.

**Spectral theorem:** A real symmetric matrix has real eigenvalues and orthogonal eigenvectors. This guarantees PCA works — the covariance matrix is symmetric, so its eigenvectors (principal components) are orthogonal.

## Assignments and Assessment

- Weekly problem sets (collaborative, due Fridays)
- Two midterm exams (Weeks 6 and 11)
- Final project: computational essay on an application of linear algebra

## Office Hours

Prof. Rodriguez: Mondays and Wednesdays, 1:00–2:30 PM, Math Building Room 410.
"""
    },
    {
        "filename": "homework1_solutions.md",
        "stage": "stage1",
        "category": "homework",
        "content": """# CS 301 — Homework 1: Solutions

**Author:** Alex Kim
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Due:** February 6, 2026

---

## Problem 1: Backpropagation Through a Two-Layer Network (25 pts)

Consider a two-layer fully connected network with ReLU activation:

    h = ReLU(W₁x + b₁)
    ŷ = W₂h + b₂

The loss is L = ½‖ŷ − y‖².

### Part (a): Derive the gradients

Using the chain rule:

    ∂L/∂b₂ = ŷ − y
    ∂L/∂W₂ = (ŷ − y) hᵀ
    ∂L/∂h  = W₂ᵀ (ŷ − y)
    ∂L/∂b₁ = diag(ReLU'(W₁x + b₁)) · W₂ᵀ (ŷ − y)
    ∂L/∂W₁ = [diag(ReLU'(W₁x + b₁)) · W₂ᵀ (ŷ − y)] xᵀ

where ReLU'(z) = 1 if z > 0 and 0 otherwise.

### Part (b): Implement in NumPy (10 pts)

```python
import numpy as np

def forward(x, W1, b1, W2, b2):
    z1 = W1 @ x + b1
    h = np.maximum(0, z1)        # ReLU
    y_hat = W2 @ h + b2
    return z1, h, y_hat

def backward(x, y, z1, h, y_hat, W2):
    m = x.shape[1]
    dy = (y_hat - y) / m
    dW2 = dy @ h.T
    db2 = np.sum(dy, axis=1, keepdims=True)
    dh = W2.T @ dy
    dz1 = dh * (z1 > 0).astype(float)  # ReLU gradient
    dW1 = dz1 @ x.T
    db1 = np.sum(dz1, axis=1, keepdims=True)
    return dW1, db1, dW2, db2
```

---

## Problem 2: Transformer Attention Complexity (25 pts)

### Part (a): Computational complexity

Given a sequence of length *n* and embedding dimension *d*, standard scaled dot-product attention computes:

    Q = XW_Q,  K = XW_K,  V = XW_V      — each O(n·d²)
    Scores = QKᵀ / √d                     — O(n²·d)
    Attn = softmax(Scores) V               — O(n²·d)

**Total: O(n²·d)**, dominated by the *n²* attention score computation when *n > d*.

### Part (b): Memory complexity

The attention matrix (n × n) requires **O(n²)** space. For n = 8192 and float32, that is approximately 256 MB — prohibitive for very long sequences.

### Part (c): Sparsity

Prof. Chen's ASA framework reduces effective complexity to O(n·k·d) where k ≪ n is the average number of attended positions per query. This is a key topic we will explore later in the semester.

---

## Problem 3: SGD Convergence (25 pts)

### Part (a): Learning rate decay

For convex objectives with Lipschitz-continuous gradients (constant L), choosing η_t = 1/(Lt) gives:

    E[f(x_T)] − f(x*) ≤ ‖x₁ − x*‖² · L / (2T)

which converges at rate O(1/T).

### Part (b): Mini-batch SGD

With batch size b, the variance of the stochastic gradient estimate decreases as O(1/b), trading off per-iteration cost for variance reduction. An optimal batch size balances gradient computation cost against convergence speed.

---

## Problem 4: Conceptual Questions (25 pts)

### Part (a): Why does batch normalization help training?

Batch normalization standardizes activations within each mini-batch, reducing **internal covariate shift**. This allows higher learning rates, acts as a mild regularizer, and smooths the loss landscape.

### Part (b): Residual connections

Skip connections in ResNets mitigate the **vanishing gradient** problem in deep networks. They create a direct path for gradient flow, enabling training of networks with hundreds of layers.

---

*References: Goodfellow et al., Deep Learning, Chapters 6–8; Vaswani et al., "Attention Is All You Need," NeurIPS 2017.*
"""
    },
    {
        "filename": "stat210_notes.md",
        "stage": "stage1",
        "category": "course_material",
        "content": """# STAT 210: Probability and Statistical Inference — Key Concepts

**Instructor:** Prof. Thomas Brown
**Semester:** Spring 2026
**Department of Statistics**

---

## 1. Probability Axioms (Kolmogorov)

A probability measure P on a sample space Ω satisfies:

1. **Non-negativity:** P(A) ≥ 0 for all events A ⊆ Ω.
2. **Normalization:** P(Ω) = 1.
3. **Countable additivity:** For disjoint events A₁, A₂, …:
   P(∪ᵢ Aᵢ) = Σᵢ P(Aᵢ).

These three axioms generate the entire edifice of probability theory.

### Conditional Probability and Bayes' Theorem

P(A|B) = P(A ∩ B) / P(B), provided P(B) > 0.

**Bayes' Theorem:**

    P(θ|D) = P(D|θ) P(θ) / P(D)

This is the foundation of Bayesian inference. The **posterior** P(θ|D) is proportional to the **likelihood** P(D|θ) times the **prior** P(θ). As data accumulates, the posterior concentrates around the true parameter value, a property known as **posterior consistency**.

## 2. Random Variables and Distributions

A random variable X is a measurable function from Ω to ℝ. The **cumulative distribution function (CDF)** F(x) = P(X ≤ x) fully characterizes the distribution.

### Common Distributions

| Distribution | Support | Mean | Variance | Use Case |
|---|---|---|---|---|
| Bernoulli(p) | {0, 1} | p | p(1−p) | Binary outcomes |
| Binomial(n, p) | {0,…,n} | np | np(1−p) | Count of successes |
| Normal(μ, σ²) | ℝ | μ | σ² | Continuous data, CLT |
| Exponential(λ) | [0, ∞) | 1/λ | 1/λ² | Waiting times |
| Beta(α, β) | [0, 1] | α/(α+β) | αβ/((α+β)²(α+β+1)) | Prior for probabilities |

### The Normal Distribution

The **Central Limit Theorem** states that the sum of n independent, identically distributed random variables with finite mean μ and variance σ² converges in distribution to N(nμ, nσ²) as n → ∞. This underpins much of classical statistical inference.

## 3. Bayesian Inference

In Bayesian statistics, parameters are treated as random variables with prior distributions. After observing data D, we update our beliefs:

    Posterior ∝ Likelihood × Prior

### Conjugate Priors

When the posterior belongs to the same family as the prior, the prior is called **conjugate**. Examples:
- Beta prior + Bernoulli/Binomial likelihood → Beta posterior
- Normal prior + Normal likelihood (known variance) → Normal posterior
- Gamma prior + Poisson likelihood → Gamma posterior

### Connection to Machine Learning

Bayesian inference connects directly to several ML concepts:
- **Regularization:** A Gaussian prior on weights corresponds to L2 (ridge) regularization. A Laplace prior corresponds to L1 (lasso) regularization.
- **Few-shot learning:** Prof. Chen's work on few-shot learning in CS 301 uses a Bayesian perspective — each new class provides a small number of observations, and the model must rapidly update its beliefs. The Prototypical Networks approach can be viewed as computing a posterior mean over class prototypes.
- **Model selection:** Bayesian model comparison via marginal likelihood (evidence) naturally penalizes model complexity (Occam's razor).

## 4. Hypothesis Testing

We test H₀ (null hypothesis) against H₁ (alternative) using a test statistic T. The **p-value** is the probability of observing a result at least as extreme as the data, assuming H₀ is true.

Key concepts:
- **Type I error** (false positive): Rejecting H₀ when it is true. Probability α.
- **Type II error** (false negative): Failing to reject H₀ when H₁ is true. Probability β.
- **Power** = 1 − β: probability of correctly rejecting a false null.

## 5. Maximum Likelihood Estimation

Given data D = {x₁, …, xₙ} assumed i.i.d., the **MLE** maximizes:

    θ̂_MLE = argmax_θ Πᵢ p(xᵢ|θ) = argmax_θ Σᵢ log p(xᵢ|θ)

Properties: consistency, asymptotic normality, efficiency.

---

*Prof. Brown's office hours: Tuesdays and Thursdays, 3:00–4:30 PM, Statistics Building Room 215.*
"""
    },

    # ── Stage 2 (5 docs) ──────────────────────────────────────────────
    {
        "filename": "cs201_syllabus.md",
        "stage": "stage2",
        "category": "course_material",
        "content": """# CS 201: Introduction to Machine Learning — Fall 2025

**Instructor:** Prof. James Liu
**Office Hours:** Mondays 1:00–3:00 PM, Room 210 Engineering Building
**Lectures:** Tue/Thu 9:30–10:45 AM, Room 105 Auditorium

## Prerequisites

- **MATH 205: Linear Algebra** (Prof. Maria Rodriguez) — essential for understanding matrix operations in neural networks and PCA.
- **STAT 210: Probability and Statistical Inference** (Prof. Thomas Brown) — foundational for understanding loss functions, regularization, and probabilistic models.

These prerequisites are **strictly enforced**. Students without credit in both courses should obtain a waiver from the instructor.

## Course Description

An accessible, project-oriented introduction to machine learning. Students will learn core supervised and unsupervised methods, build models using scikit-learn and PyTorch, and complete three programming projects culminating in a final project.

## Topics

1. **Introduction and Data Exploration** — data wrangling, visualization, train/test splits, cross-validation.
2. **Linear Models** — linear regression, logistic regression, softmax, gradient descent.
3. **Regularization** — ridge, lasso, elastic net; connections to Bayesian priors (see STAT 210 notes by Prof. Brown).
4. **Decision Trees and Ensemble Methods** — random forests, gradient boosting, XGBoost.
5. **Neural Networks and Backpropagation** — perceptrons, MLPs, automatic differentiation.
6. **Unsupervised Learning** — k-means, hierarchical clustering, PCA (connections to MATH 205 eigenvalue theory).
7. **Model Evaluation** — precision, recall, F1, ROC curves, confusion matrices.
8. **Ethics in ML** — fairness, interpretability, responsible AI.

## Assessment

| Component              | Weight |
|------------------------|--------|
| Homework (5 sets)      | 30%    |
| Programming Projects   | 40%    |
| Final Exam             | 20%    |
| Participation          | 10%    |

## Course Relationship to CS 301

CS 201 is a **direct prerequisite** for CS 301 (Advanced Machine Learning, taught by Prof. Sarah Chen). Students who complete CS 201 will be well-prepared for the transformer architectures, attention mechanisms, and advanced optimization topics in CS 301.

## Notable Past Projects

- **Sentiment Analysis Pipeline** — real-time Twitter sentiment using LSTM networks (Spring 2024).
- **Medical Image Preprocessing** — automated MRI segmentation using U-Net (Fall 2024, in collaboration with Dr. Emily Watson's biomedical engineering group).
- **Federated Learning Prototype** — privacy-preserving model training across simulated hospital networks (Spring 2025, supervised jointly by Prof. Liu and Prof. Chen).

## Textbooks

- James, G., Witten, D., Hastie, T., and Tibshirani, R. *An Introduction to Statistical Learning (ISLR)*, 2nd ed. Springer, 2021.
- Goodfellow, I., Bengio, Y., and Courville, A. *Deep Learning*. MIT Press, 2016. (Selected chapters.)

## Contact

Email: j.liu@university.edu
"""
    },
    {
        "filename": "hw2_linear_algebra.md",
        "stage": "stage2",
        "category": "homework",
        "content": """# MATH 205 — Homework 2: PCA and SVD

**Author:** Priya Sharma
**Course:** MATH 205 Linear Algebra, Prof. Maria Rodriguez
**Due:** March 13, 2026

---

## Problem 1: Principal Component Analysis (PCA) Derivation (30 pts)

Given a data matrix X ∈ ℝ^(n×d) with centered columns (zero mean), the **sample covariance matrix** is:

    S = (1/(n-1)) Xᵀ X

### Part (a): Eigenvalue formulation (10 pts)

PCA seeks directions of maximum variance. The first principal component is the unit vector **v₁** that maximizes:

    var(X**v₁**) = **v₁**ᵀ S **v₁**   subject to  ‖**v₁**‖ = 1

Using the method of Lagrange multipliers, we set up:

    L(**v₁**, λ₁) = **v₁**ᵀ S **v₁** − λ₁ (**v₁**ᵀ **v₁** − 1)

Taking the derivative and setting it to zero:

    S **v₁** = λ₁ **v₁**

Thus **v₁** is an eigenvector of S corresponding to the **largest eigenvalue** λ₁. Subsequent components are eigenvectors of the remaining eigenvalues, orthogonal to all previous components.

### Part (b): Variance explained (10 pts)

The proportion of variance explained by the first k principal components is:

    PVE(k) = (Σᵢ₌₁ᵏ λᵢ) / (Σᵢ₌₁ᵈ λᵢ)

This metric guides dimensionality reduction — we choose k such that PVE exceeds a threshold (typically 90–95%).

### Part (c): Connection to ML (10 pts)

**Connection to Prof. Chen's CS 301:** In Prof. Chen's Advanced Machine Learning course, PCA appears in several contexts:

1. **Efficient attention:** Projecting high-dimensional key and value matrices into lower-dimensional subspaces before computing attention scores, reducing the O(n²d) complexity.
2. **Visualization:** Projecting high-dimensional attention weight matrices into 2D for interpretability (see cs301_syllabus.md).
3. **Data preprocessing:** Removing noise dimensions before training few-shot learning models.

The eigenvalue theory from MATH 205 Week 4 guarantees that PCA produces orthogonal components — this is the spectral theorem applied to the symmetric covariance matrix S.

## Problem 2: Singular Value Decomposition (SVD) (35 pts)

### Part (a): Statement of SVD (10 pts)

Every matrix A ∈ ℝ^(m×n) can be decomposed as:

    A = U Σ Vᵀ

where U ∈ ℝ^(m×m) is orthogonal, Σ ∈ ℝ^(m×n) is diagonal (with singular values σ₁ ≥ σ₂ ≥ … ≥ 0), and V ∈ ℝ^(n×n) is orthogonal.

### Part (b): Low-rank approximation (15 pts)

The **Eckart–Young theorem** states that the best rank-k approximation to A (in both the spectral norm and Frobenius norm) is:

    A_k = U_k Σ_k V_kᵀ

where we keep only the top k singular values. The approximation error is:

    ‖A − A_k‖_F = √(Σᵢ₌ₖ₊₁ʳ σᵢ²)

where r = rank(A). This is the mathematical foundation for dimensionality reduction, image compression, and — critically — efficient transformer attention as explored in Prof. Chen's ASA framework.

### Part (c): Computational considerations (10 pts)

For an n×n matrix, full SVD costs O(n³). However, **randomized SVD** algorithms (one of Prof. Rodriguez's research areas) reduce this to O(n²k + nk²) for rank-k approximations, making large-scale PCA feasible.

## Problem 3: SVD Application (35 pts)

Given the 4×3 matrix:

    A = [1  0  1]
        [0  1  0]
        [1  0  1]
        [0  1  0]

1. Compute AᵀA and its eigenvalues.
2. Find the singular values of A.
3. Give the rank-1 approximation A₁ and compute ‖A − A₁‖_F.
4. Interpret: what structure does the rank-1 approximation capture?

---

*References: Prof. Rodriguez's lecture notes (Week 4); Strang, G., Introduction to Linear Algebra, 6th ed., Ch. 7.*
"""
    },
    {
        "filename": "capstone_ml_medical.md",
        "stage": "stage2",
        "category": "project_report",
        "content": """# CS 301 Capstone Project: Few-Shot Medical Image Classification

**Title:** Prototypical Networks with Cross-Attention for Few-Shot Dermoscopy Classification
**Authors:** Priya Sharma and Marcus Johnson
**Advisor:** Prof. Sarah Chen
**External Collaborator:** Dr. Emily Watson, Department of Biomedical Engineering
**Course:** CS 301 Advanced Machine Learning, Spring 2026

---

## Abstract

We present a few-shot learning system for classifying rare skin conditions from dermoscopy images. Using Prototypical Networks enhanced with cross-attention between support and query embeddings, our model achieves **73.5% accuracy in the 5-shot setting** across 15 dermatological conditions, significantly outperforming the baseline Prototypical Network (68.2%) and matching-network (65.7%) approaches.

## 1. Introduction

Rare skin conditions present a significant diagnostic challenge: dermatologists may encounter fewer than 10 cases of a specific disease during their entire career. Deep learning models typically require hundreds or thousands of labeled examples per class, making them poorly suited to rare-condition diagnosis.

Few-shot learning addresses this by training models to generalize from very few examples. In collaboration with Dr. Emily Watson's biomedical engineering group, we curated a dataset of **1,200 dermoscopy images** spanning **15 dermatological conditions**, with per-class counts as low as 20 images.

## 2. Related Work

- **Prototypical Networks** (Snell et al., 2017): Learn a metric space where classification is performed by computing distances to class prototypes (mean embeddings).
- **Matching Networks** (Vinyals et al., 2016): Use attention-based matching with episodic training.
- **MAML** (Finn et al., 2017): Model-agnostic meta-learning that finds initialization parameters.
- **Prof. Chen's ASA Framework:** Adaptive Sparse Attention reduces quadratic attention complexity and has been shown to improve feature extraction in low-data regimes (see prof_chen_research.md).

## 3. Method

Our architecture builds on Prototypical Networks with two key modifications:

1. **Cross-attention refinement:** After computing initial prototypes as mean support embeddings, we apply a cross-attention layer where each support embedding attends to all other support embeddings within the same class. This allows prototypes to incorporate relational information between examples.

2. **Sparse attention regularization:** Inspired by Prof. Chen's ASA work, we apply a sparsity mask to the cross-attention weights, encouraging the model to focus on the most informative support-query relationships. This reduces overfitting in the few-shot regime.

### Architecture

    Input images → ResNet-18 encoder → Embedding (64-d)
    → Cross-attention refinement (within-class)
    → Prototypes (15 × 64)
    → Distance-based classification

## 4. Experiments and Results

| Method | 1-shot | 5-shot | 10-shot |
|--------|--------|--------|---------|
| Matching Network | 52.1% | 65.7% | 71.3% |
| ProtoNet (baseline) | 55.8% | 68.2% | 74.0% |
| MAML | 53.4% | 66.9% | 72.5% |
| **ProtoNet + CrossAttn (Ours)** | **58.3%** | **73.5%** | **77.8%** |

Our best model achieves **73.5% 5-shot accuracy**, a 5.3 percentage point improvement over the standard Prototypical Network.

## 5. Ablation Study

- Removing cross-attention: accuracy drops to 68.2% (baseline).
- Removing ASA-inspired sparsity: accuracy drops to 71.1%, suggesting regularization is important.
- Using full attention (no sparsity): accuracy is 71.9%, with significantly higher memory usage.

## 6. Discussion

The cross-attention mechanism allows prototypes to capture within-class variation — for instance, different presentations of the same skin condition. The sparsity constraint prevents the model from memorizing spurious correlations in the small support sets.

**Limitations:** The dataset is relatively small and single-institution. Future work should include multi-center validation and integration with Dr. Watson's clinical decision support pipeline.

## 7. Acknowledgments

We thank Prof. Chen for her guidance and for sharing insights from the ASA framework. We are grateful to Dr. Emily Watson for access to the dermoscopy dataset and clinical expertise. Alex Kim provided valuable feedback on the attention implementation.

---

*See also: biomedical_ml_collab.md for the broader collaboration context; hw3_transformers.md for related coursework.*
"""
    },
    {
        "filename": "research_essay_few_shot.md",
        "stage": "stage2",
        "category": "research_essay",
        "content": """# Literature Review: Meta-Learning for Few-Shot Classification

**Author:** Priya Sharma
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Date:** March 2026

---

## 1. Introduction

Few-shot learning aims to classify new objects from very few labeled examples — a single image (1-shot) or a handful (5-shot). This capability is critical in domains where data is scarce: rare disease diagnosis, robotics, and personalized recommendation.

This review surveys the major approaches to few-shot classification, with emphasis on metric-based, optimization-based, and attention-based methods.

## 2. Metric-Based Approaches

### 2.1 Siamese Networks (Koch et al., 2015)

The earliest deep learning approach to few-shot classification used **Siamese networks** — twin networks sharing weights that learn a similarity function. Two inputs are passed through the same network, and a distance metric determines if they belong to the same class. Limitation: the network is trained for verification (same/different) rather than classification, requiring a separate procedure for k-way tasks.

### 2.2 Matching Networks (Vinyals et al., 2016)

Matching Networks introduced **episodic training**: the model is trained on tasks that mimic the test-time few-shot scenario. Each episode consists of a support set S = {(xᵢ, yᵢ)} and a query point. The prediction uses a weighted nearest-neighbor with attention:

    P(ŷ|q, S) = Σᵢ a(q, xᵢ) · yᵢ

where a(q, xᵢ) = softmax(f(q)ᵀ g(xᵢ)) is a learned attention kernel.

### 2.3 Prototypical Networks (Snell et al., 2017)

Prototypical Networks (ProtoNets) simplify matching networks by computing a **prototype** for each class as the mean of its support embeddings:

    cₖ = (1/|Sₖ|) Σ_{(x,y)∈Sₖ} f(x)

Classification is performed by nearest neighbor in embedding space. ProtoNets are computationally efficient and remarkably effective. Our capstone project (see capstone_ml_medical.md) builds directly on this framework.

## 3. Optimization-Based Approaches

### 3.1 MAML (Finn et al., 2017)

Model-Agnostic Meta-Learning (MAML) learns an **initialization** of model parameters from which a few gradient steps on a small support set will yield good performance. The outer loop optimizes:

    θ* = θ − β ∇_θ Σ_{task_i} L_{task_i}(θ − α ∇_θ L_{task_i}(θ))

MAML is elegant but expensive: computing second-order gradients requires O(n²) memory.

### 3.2 Reptile (Nichol et al., 2018)

Reptile simplifies MAML by avoiding second-order gradients entirely. It runs SGD on each task and moves the initialization toward the task-specific solution. Surprisingly competitive with MAML at a fraction of the computational cost.

## 4. Attention and Transformer Approaches

Recent work has applied transformer architectures to few-shot learning:

- **FEAT** (Ye et al., 2020): Uses transformer layers to refine class prototypes via self-attention across support examples.
- **Prof. Chen's ASA Framework** (Chen et al., 2022): Adaptive Sparse Attention has shown promise in few-shot settings by dynamically selecting the most relevant support-query relationships, reducing noise from irrelevant examples.

The connection to our capstone work: we adapted ASA-inspired sparsity into the Prototypical Network's cross-attention layer, achieving our best results (73.5% 5-shot accuracy on the dermoscopy dataset).

## 5. Comparative Analysis

| Method | Type | Strengths | Weaknesses |
|--------|------|-----------|------------|
| Siamese Nets | Metric | Simple | Not episodic |
| Matching Nets | Metric | Episodic | Complex attention |
| ProtoNets | Metric | Efficient, effective | Ignores within-class variation |
| MAML | Optimization | Flexible | Computationally expensive |
| Transformer/ASA | Attention | Captures relations | Requires careful regularization |

## 6. Conclusion

Few-shot learning has matured rapidly. The most effective current approaches combine metric learning with attention mechanisms. Future directions include cross-modal few-shot learning, continual few-shot learning, and clinical deployment (see biomedical_ml_collab.md).

## References

1. Koch, G. et al. "Siamese Neural Networks for One-Shot Image Recognition." *ICML Deep Learning Workshop*, 2015.
2. Vinyals, O. et al. "Matching Networks for One Shot Learning." *NeurIPS*, 2016.
3. Snell, J. et al. "Prototypical Networks for Few-shot Learning." *NeurIPS*, 2017.
4. Finn, C. et al. "Model-Agnostic Meta-Learning for Fast Adaptation of Deep Networks." *ICML*, 2017.
5. Nichol, A. et al. "Reptile: A Scalable Metalearning Algorithm." *arXiv*, 2018.
6. Ye, M. et al. "FEAT: Few-Shot Embedding Adaptation with Transformers." *ICML*, 2020.
7. Chen, S. et al. "Adaptive Sparse Attention for Scalable Transformers." *NeurIPS*, 2022.
"""
    },
    {
        "filename": "stat210_practical.md",
        "stage": "stage2",
        "category": "course_material",
        "content": """# STAT 210 — Lab 5: Bayesian Linear Regression

**Instructor:** Prof. Thomas Brown
**TA:** Derek Lee
**Semester:** Spring 2026

---

## Objectives

In this lab, you will:
1. Implement Bayesian linear regression from scratch.
2. Visualize posterior distributions over regression coefficients.
3. Connect Bayesian inference to regularization in machine learning.
4. See how Prof. Chen's research on few-shot learning relates to Bayesian updating.

## 1. Background

### Bayesian Linear Regression

Given data D = {(xᵢ, yᵢ)} with yᵢ = xᵢᵀ **w** + εᵢ, εᵢ ~ N(0, σ²), and a **Gaussian prior** on the weights:

    **w** ~ N(μ₀, Σ₀)

The **posterior** is:

    **w** | D ~ N(μₙ, Σₙ)

where:
- Σₙ = (Σ₀⁻¹ + (1/σ²) XᵀX)⁻¹
- μₙ = Σₙ (Σ₀⁻¹ μ₀ + (1/σ²) Xᵀ**y**)

The **posterior predictive** for a new input x* is:

    p(y*|x*, D) = N(x*ᵀ μₙ, x*ᵀ Σₙ x* + σ²)

### Connection to Regularization

A critical insight: **Gaussian prior with zero mean is equivalent to L2 (ridge) regularization.**

With prior **w** ~ N(0, σ₀²I), the MAP estimate is:

    **ŵ**_MAP = argmax [log p(D|**w**) + log p(**w**)]
             = argmax [−½Σᵢ(yᵢ − xᵢᵀ**w**)²/σ² − ‖**w**‖²/(2σ₀²)]

This is exactly ridge regression with λ = σ²/σ₀².

Similarly, a **Laplace prior** (double exponential) yields L1 (lasso) regularization. This connection was highlighted in Prof. Liu's CS 201 lectures on regularization (see cs201_syllabus.md).

## 2. Lab Exercise

### Step 1: Generate Synthetic Data

```python
import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)
n = 50
X = np.random.uniform(-3, 3, (n, 2))
true_w = np.array([1.5, -0.8])
y = X @ true_w + np.random.normal(0, 0.5, n)
```

### Step 2: Implement Posterior Computation

```python
def bayesian_linear_regression(X, y, sigma2=0.25, mu0=None, Sigma0=None):
    n, d = X.shape
    if mu0 is None:
        mu0 = np.zeros(d)
    if Sigma0 is None:
        Sigma0 = np.eye(d) * 10.0  # vague prior

    Sigma0_inv = np.linalg.inv(Sigma0)
    Sigma_n = np.linalg.inv(Sigma0_inv + X.T @ X / sigma2)
    mu_n = Sigma_n @ (Sigma0_inv @ mu0 + X.T @ y / sigma2)
    return mu_n, Sigma_n
```

### Step 3: Visualization

Plot the posterior contours for (w₁, w₂). As more data is collected, the posterior shrinks around the true parameter values — this is **posterior consistency** in action.

## 3. Connection to Few-Shot Learning

Prof. Chen's research on few-shot learning (see prof_chen_research.md) draws on a Bayesian perspective. In the few-shot setting:

- **Prior:** The model's knowledge from pre-training or other tasks.
- **Observations:** The small support set (e.g., 5 images per class).
- **Posterior:** Updated model that can classify new examples.

The Prototypical Network's class prototype can be interpreted as a **posterior mean** of the class centroid, with the support set playing the role of observed data. As more support examples are added, the prototype converges to the true class mean — analogous to Bayesian posterior convergence.

This Bayesian interpretation explains why few-shot learning works: it is a form of **online Bayesian inference** where the model rapidly updates beliefs from very few observations.

## 4. Deliverables

1. Completed notebook with posterior computation and visualization.
2. Short essay (300 words) connecting Bayesian linear regression to either:
   - Ridge/lasso regularization in Prof. Liu's CS 201, or
   - Few-shot learning in Prof. Chen's CS 301.

## Grading

- Code correctness: 50%
- Visualization quality: 20%
- Essay insight: 30%

---

*Lab held in Statistics Computer Lab, Room 101. TA Derek Lee's office hours: Wednesdays 4:00–5:30 PM.*
"""
    },

    # ── Stage 3 (10 docs) ─────────────────────────────────────────────
    {
        "filename": "hw3_transformers.md",
        "stage": "stage3",
        "category": "homework",
        "content": """# CS 301 — Homework 3: Transformers and Attention

**Author:** Marcus Johnson
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Due:** April 10, 2026

---

## Problem 1: Multi-Head Attention Implementation (30 pts)

### Part (a): Scaled Dot-Product Attention (10 pts)

Implement the scaled dot-product attention function:

```python
import torch
import torch.nn.functional as F
import math

def scaled_dot_product_attention(Q, K, V, mask=None):
    # Args:
    #   Q: (batch, heads, seq_len, d_k)
    #   K: (batch, heads, seq_len, d_k)
    #   V: (batch, heads, seq_len, d_v)
    #   mask: optional (batch, 1, 1, seq_len) or (batch, 1, seq_len, seq_len)
    # Returns:
    #   output: (batch, heads, seq_len, d_v)
    #   attention_weights: (batch, heads, seq_len, seq_len)
    d_k = Q.size(-1)
    scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, float('-inf'))
    attention_weights = F.softmax(scores, dim=-1)
    output = torch.matmul(attention_weights, V)
    return output, attention_weights
```

### Part (b): Multi-Head Attention (10 pts)

```python
class MultiHeadAttention(torch.nn.Module):
    def __init__(self, d_model, num_heads):
        super().__init__()
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        self.W_Q = torch.nn.Linear(d_model, d_model)
        self.W_K = torch.nn.Linear(d_model, d_model)
        self.W_V = torch.nn.Linear(d_model, d_model)
        self.W_O = torch.nn.Linear(d_model, d_model)

    def forward(self, Q, K, V, mask=None):
        batch_size = Q.size(0)
        Q = self.W_Q(Q).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        K = self.W_K(K).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        V = self.W_V(V).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        attn_output, attn_weights = scaled_dot_product_attention(Q, K, V, mask)
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        return self.W_O(attn_output), attn_weights
```

### Part (c): Complexity analysis (10 pts)

With sequence length n, embedding dimension d, and h heads:
- Each head operates on dimension d_k = d/h.
- Per-head cost: O(n² · d/h).
- Total across h heads: O(n² · d) — same as single-head, but with **representational power** of h independent attention patterns.

## Problem 2: Sparse Attention Patterns (35 pts)

### Part (a): Prof. Chen's ASA Framework (15 pts)

The Adaptive Sparse Attention (ASA) mechanism (see prof_chen_research.md) reduces attention complexity by selecting a subset of key positions for each query. Specifically:

1. A **gating network** g(qᵢ) produces a sparse distribution over keys.
2. Only the top-k keys (k ≪ n) are attended to.
3. The effective complexity becomes O(n · k · d) instead of O(n² · d).

**Advantages:**
- Reduces memory from O(n²) to O(n·k).
- Can learn task-specific sparsity patterns.
- Particularly effective for sequences with local structure (e.g., text, time series).

**Disadvantages:**
- Requires careful tuning of sparsity level k.
- May miss long-range dependencies if k is too small.
- Training the gating network adds complexity.

### Part (b): Fixed sparse patterns (10 pts)

Compare three fixed sparse attention patterns:
1. **Local (sliding window):** Each position attends to w neighbors. Cost: O(n·w·d).
2. **Dilated:** Like local but with gaps. Captures longer range with same cost.
3. **Block-sparse:** Divide sequence into blocks; attend only within and between adjacent blocks.

### Part (c): Attention in few-shot learning (10 pts)

In few-shot classification (see our capstone project, capstone_ml_medical.md), sparse attention serves a different purpose: **regularization**. With only 5 support examples, full cross-attention between support and query embeddings can overfit. ASA-inspired sparsity forces the model to focus on the most informative support-query pairs, improving generalization.

Our capstone results: ProtoNet + CrossAttn achieves 73.5% 5-shot accuracy, while removing the sparsity constraint drops accuracy to 71.9% (see capstone_ml_medical.md, Section 4).

## Problem 3: Coding Exercise — Transformer Block (35 pts)

Implement a complete transformer encoder block:

```python
class TransformerBlock(torch.nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attn = MultiHeadAttention(d_model, num_heads)
        self.norm1 = torch.nn.LayerNorm(d_model)
        self.norm2 = torch.nn.LayerNorm(d_model)
        self.ff = torch.nn.Sequential(
            torch.nn.Linear(d_model, d_ff),
            torch.nn.ReLU(),
            torch.nn.Linear(d_ff, d_model),
        )
        self.dropout = torch.nn.Dropout(dropout)

    def forward(self, x, mask=None):
        attn_out, attn_weights = self.attn(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_out))
        ff_out = self.ff(x)
        x = self.norm2(x + self.dropout(ff_out))
        return x, attn_weights
```

Test with n=128, d=256, h=8, d_ff=1024. Verify output shape is (batch, 128, 256) and attention weights sum to 1 along the key dimension.

---

*References: Vaswani et al., "Attention Is All You Need," 2017; Chen et al., "Adaptive Sparse Attention," NeurIPS 2022.*
"""
    },
    {
        "filename": "cs490_seminar_notes.md",
        "stage": "stage3",
        "category": "course_material",
        "content": """# CS 490: Advanced Topics Seminar — Notes

**Instructor:** Prof. Sarah Chen
**Topic:** Scaling Laws and Emergent Abilities in Large Language Models
**Date:** April 22, 2026

---

## Overview

This seminar session explored the empirical and theoretical foundations of scaling laws in neural language models, and the controversial concept of emergent abilities.

## 1. Kaplan et al. (2020) Scaling Laws

OpenAI's landmark paper established power-law relationships:

    L(N) ∝ N^(−α_N)     (model parameters)
    L(D) ∝ D^(−α_D)     (training data)
    L(C) ∝ C^(−α_C)     (compute budget)

where L is the cross-validation loss. Typical exponents: α_N ≈ 0.076, α_D ≈ 0.095, α_C ≈ 0.050.

**Key insight:** Performance improves predictably with scale, and the optimal allocation of compute between model size and data size follows a specific ratio.

## 2. Chinchilla Scaling (Hoffmann et al., 2022)

The Chinchilla paper challenged the "bigger model" approach by showing that for a given compute budget, the optimal model size scales linearly with the number of training tokens:

    N_opt ∝ C^(0.5),  D_opt ∝ C^(0.5)

This implies many large models (including GPT-3) were **undertrained** relative to their size. The 70B Chinchilla model outperformed the 175B Gopher despite being 2.5× smaller.

## 3. Emergent Abilities

**Wei et al. (2022)** defined emergent abilities as capabilities that are:

> "absent in small models but present in large models"

Examples include:
- **Chain-of-thought reasoning:** Models can solve multi-step problems when prompted to "think step by step," but only above ~100B parameters.
- **Few-shot learning:** Large models can learn new tasks from examples in the context window — this connects directly to Prof. Chen's research on few-shot learning (see prof_chen_research.md).
- **Code generation:** Ability to write executable code appears suddenly at sufficient scale.

### Criticism

**Schaeffer et al. (2023)** argued that emergent abilities are **artifacts of metric choice**. Using smooth metrics (e.g., Brier score instead of exact-match accuracy), performance improves gradually. The "emergence" disappears when we measure correctly.

## 4. Discussion

### Alex Kim's Presentation: ASA and Scaling

Alex Kim (Ph.D. student in Prof. Chen's lab) presented preliminary results on how the ASA (Adaptive Sparse Attention) mechanism scales with model size:

- At small model sizes (< 1B params), ASA provides modest gains (2–3% on perplexity).
- At larger sizes (7B+), ASA shows more significant improvements (5–7%), suggesting that **sparsity becomes more valuable as models grow**.
- Alex hypothesizes that larger models have more redundant attention patterns that ASA can prune.

### Questions for Further Reading

1. Does ASA interact with Chinchilla-optimal training? Can sparse models be trained with less data?
2. Are "few-shot learning" abilities truly emergent, or do they improve gradually with scale?
3. How do scaling laws apply to multimodal models (vision + language)?

## Attendees

Prof. Sarah Chen, Alex Kim, Priya Sharma, Marcus Johnson, Fatima Al-Rashid, Derek Lee, and 8 other graduate students.

## References

- Kaplan, J. et al. "Scaling Laws for Neural Language Models." *arXiv:2001.08361*, 2020.
- Hoffmann, J. et al. "Training Compute-Optimal Large Language Models." *NeurIPS*, 2022.
- Wei, J. et al. "Emergent Abilities of Large Language Models." *TMLR*, 2022.
- Schaeffer, R. et al. "Are Emergent Abilities of LLMs a Mirage?" *NeurIPS*, 2023.
"""
    },
    {
        "filename": "project_gan_music.md",
        "stage": "stage3",
        "category": "project_report",
        "content": """# CS 301 Project: Attention-Based Music Generation

**Title:** Sparse Attention for Efficient Neural Music Composition
**Authors:** Fatima Al-Rashid and Derek Lee
**Course:** CS 301 Advanced Machine Learning, Prof. Sarah Chen
**Date:** April 2026

---

## Abstract

We present an attention-based music generation system that leverages Prof. Chen's Adaptive Sparse Attention (ASA) mechanism to reduce parameter count while maintaining generation quality. Our model uses **39% fewer parameters** than a comparable full-attention transformer while achieving comparable music quality scores as evaluated by human listeners and automated metrics.

## 1. Introduction

Neural music generation has advanced rapidly with transformer-based models. However, the quadratic complexity of self-attention limits the sequence lengths that can be modeled — a critical limitation for music, where long-range structure (themes, key changes, repetition) is essential.

We propose using **sparse attention patterns** to model long musical sequences efficiently. Our approach is inspired by Prof. Chen's ASA framework (see prof_chen_research.md), which demonstrates that not all token-to-token relationships are necessary for high-quality generation.

## 2. Related Work

- **Music Transformer** (Huang et al., 2018): Applied self-attention to symbolic music generation, using relative attention for pitch and time.
- **ASA** (Chen et al., 2022): Adaptive Sparse Attention for efficient transformers.
- **Performer** (Choromanski et al., 2021): Linear attention via random feature approximation.

## 3. Model Architecture

### Input Representation

We represent music as a sequence of events: (pitch, duration, velocity, time_shift). The vocabulary size is 512, and sequences are up to 4096 tokens long.

### Sparse Attention Design

We implement three attention configurations:

1. **Full attention** (baseline): Standard O(n²d) attention.
2. **Local + Global:** 90% local sliding window (w=128) + 10% global tokens that attend to everything. Cost: O(n·w·d + g²·d) where g = 0.1n.
3. **ASA-inspired:** Learned sparsity with top-k selection (k=64). The gating network learns to identify which key positions are most relevant for each query.

### Training

- **Dataset:** MAESTRO dataset (22 hours of piano performances).
- **Loss:** Cross-entropy on next-token prediction.
- **Optimizer:** AdamW with cosine learning rate schedule.
- **Training:** 500K steps, batch size 16, sequence length 2048.

## 4. Results

| Model | Params | FLOPs | Melody Coherence | Human Pref. |
|-------|--------|-------|------------------|-------------|
| Full Attention | 142M | 1.0× | 0.84 | 34% |
| Local + Global | 108M (−24%) | 0.71× | 0.82 | 28% |
| **ASA-Inspired** | **87M (−39%)** | **0.52×** | **0.83** | **38%** |

Surprisingly, the ASA-inspired model received the **highest human preference rating** (38%), suggesting that sparse attention may act as a useful inductive bias that encourages the model to focus on musically meaningful relationships.

### Analysis of Learned Sparsity Patterns

Visualization of the learned sparsity patterns (using techniques from Prof. Rodriguez's research on low-rank matrix approximation, see rodriguez_research.md) reveals that:
- The model strongly attends to the **previous occurrence of similar motifs** (repetition tracking).
- **Harmonic relationships** (intervals of octaves, fifths, and thirds) create long-range attention patterns.
- **Rhythmic patterns** at regular intervals create periodic attention structures.

## 5. Ablation Study

| k (top-k) | Params | Melody Coherence |
|-----------|--------|------------------|
| 32 | 72M | 0.78 |
| 64 | 87M | 0.83 |
| 128 | 108M | 0.84 |
| 256 | 128M | 0.85 |

The sweet spot is k=64, achieving near-full-attention quality with 39% fewer parameters.

## 6. Conclusions

Sparse attention is effective for music generation. The ASA-inspired approach not only reduces computational cost but may improve generation quality by filtering out irrelevant token relationships. Future work includes extending to multi-instrument generation and integrating Prof. Rodriguez's randomized SVD for further efficiency gains.

---

*Code available at: github.com/cs301-music-gen/sparse-music*
"""
    },
    {
        "filename": "biomedical_ml_collab.md",
        "stage": "stage3",
        "category": "research_essay",
        "content": """# Biomedical ML Collaboration: Few-Shot Rare Disease Diagnosis

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
"""
    },
    {
        "filename": "liu_teaching_philosophy.md",
        "stage": "stage3",
        "category": "research_essay",
        "content": """# Prof. James Liu: Teaching Philosophy and Curriculum Vision

**Author:** Prof. James Liu
**Department:** Computer Science
**Date:** April 2026

---

## 1. Teaching Philosophy

My approach to teaching machine learning is guided by a simple principle: **start with intuition, build to rigor**.

Too many ML courses begin with equations and end with applications. I invert this: we start with a real problem, develop intuition for why certain approaches work, and then formalize the mathematics. This **top-down approach** has been central to my teaching since I joined the department in 2015.

The evidence supports this philosophy: students who learn ML through application-first pedagogy show higher retention, better transfer to novel problems, and more confidence in research settings.

## 2. CS 201: Building the Foundation

CS 201 (Introduction to Machine Learning) is designed as the gateway to the ML curriculum. The course covers:

- **Supervised learning:** Regression, classification, decision trees, ensemble methods.
- **Neural networks:** Backpropagation, MLPs, introduction to PyTorch.
- **Unsupervised learning:** Clustering, PCA.
- **Evaluation and ethics:** Cross-validation, fairness, responsible AI.

### Connection to Prerequisites

CS 201 explicitly bridges the prerequisite courses:

- **MATH 205 (Prof. Rodriguez):** Students apply eigenvalue theory from linear algebra directly to PCA implementation. The matrix calculus from Week 4 of MATH 205 underpins the backpropagation derivations in CS 201.
- **STAT 210 (Prof. Brown):** Bayesian reasoning informs our treatment of regularization (L1/L2 as prior choices), model selection, and uncertainty quantification. Students who have internalized the Bayesian perspective from STAT 210 find the regularization module in CS 201 almost intuitive.

### Bridge to CS 301

CS 201 is the **direct prerequisite** for Prof. Chen's CS 301 (Advanced Machine Learning). The progression is deliberate:

- CS 201 covers vanilla backpropagation → CS 301 covers transformer architectures.
- CS 201 covers basic gradient descent → CS 301 covers Adam, learning rate scheduling, and optimization theory.
- CS 201 covers logistic regression → CS 301 covers attention as a form of dynamic weighting.
- CS 201 covers k-means and PCA → CS 301 covers sparse attention and efficient transformers.

Prof. Chen and I coordinate our syllabi each semester to ensure smooth transitions. Her capstone projects often build on foundations laid in CS 201 — for instance, the recent medical imaging project (see capstone_ml_medical.md) used ResNet architectures that students first encounter in CS 201.

## 3. Notable Alumni

Several former CS 201 students have gone on to do exceptional work:

- **Priya Sharma** — took CS 201 in Fall 2023, now a Ph.D. student with Prof. Chen working on few-shot learning (see research_essay_few_shot.md).
- **Fatima Al-Rashid** — took CS 201 in Spring 2024, now co-leading the music generation project using ASA attention (see project_gan_music.md).
- **Derek Lee** — took CS 201 in Fall 2024, now a TA for STAT 210 and co-author on the music generation project.

These success stories validate the curriculum design: CS 201 provides the foundational skills, CS 301 provides the advanced tools, and the supporting courses (MATH 205, STAT 210) provide the mathematical and statistical depth.

## 4. Federated Learning and Privacy

A newer thread in my teaching involves **federated learning** — training ML models across distributed data sources without sharing raw data. This connects to my research collaboration with Prof. Chen (see prof_chen_research.md) on federated PCA for privacy-preserving student data analysis.

I am developing a new module for CS 201 (to be introduced in Fall 2026) that covers federated learning basics, allowing students to see how the supervised learning methods they learn can be adapted for privacy-preserving settings.

## 5. Assessment Philosophy

I believe in **authentic assessment**: projects that mirror real-world ML workflows, homework that requires both coding and written analysis, and exams that test conceptual understanding rather than memorization. The CS 201 programming projects are designed to be portfolio-quality — several alumni have cited their CS 201 projects in job interviews.

## 6. Future Vision

The ML curriculum is evolving rapidly. My goals for the next three years:

1. **Integrate LLM fundamentals** into CS 201, so students arrive in CS 301 with transformer intuition.
2. **Expand cross-listed courses** with Statistics (Prof. Brown) and Mathematics (Prof. Rodriguez).
3. **Develop a clinical AI track** in partnership with Dr. Emily Watson's biomedical engineering group.
4. **Launch a summer ML bootcamp** for students from non-STEM backgrounds.

---

*Prof. Liu's office: Engineering Building Room 210. Email: j.liu@university.edu.*
"""
    },
    {
        "filename": "rodriguez_research.md",
        "stage": "stage3",
        "category": "research_essay",
        "content": """# Research Profile: Prof. Maria Rodriguez

## Background

Prof. Maria Rodriguez is a Professor of Mathematics at the university, specializing in applied linear algebra and numerical methods. She received her Ph.D. from the University of Chicago in 2012 under Prof. Michael Mahoney, with a dissertation on *"Randomized Algorithms for Large-Scale Matrix Computations."*

## Research Interests

### 1. Tensor Decomposition

Tensor decompositions generalize matrix factorizations to multi-dimensional arrays. Prof. Rodriguez's work on **CP decomposition** and **Tucker decomposition** has applications in:

- **Data compression:** Reducing the storage requirements of high-dimensional scientific data.
- **Signal processing:** Separating mixed signals in telecommunications.
- **Machine learning:** Analyzing multi-way data (e.g., time × feature × subject in neuroscience).

Key publication: Rodriguez, M. "Scalable Tensor Decompositions for Multi-Way Data Analysis." *SIAM Journal on Matrix Analysis*, 2021.

### 2. Randomized SVD

Prof. Rodriguez is a leading expert on **randomized algorithms** for computing low-rank matrix approximations. Her randomized SVD algorithm achieves near-optimal accuracy in O(mnk) time for an m×n matrix of rank k, compared to O(mn min(m,n)) for the deterministic SVD.

This work has direct applications in:
- **Principal Component Analysis (PCA):** Enabling PCA on datasets with millions of features.
- **Natural language processing:** Efficient word embeddings and topic modeling.
- **Attention mechanisms in transformers:** As discussed in the ML seminar, randomized SVD can approximate attention weight matrices efficiently.

### 3. Collaborations

#### With Prof. Sarah Chen (Computer Science)

Prof. Rodriguez and Prof. Chen collaborate on applying tensor decomposition and low-rank approximation methods to **analyze attention weight matrices** in transformer models. Attention matrices are often approximately low-rank, meaning that much of the computation in standard attention is redundant.

Their joint work includes:
- "Low-Rank Structure in Transformer Attention: An Empirical Analysis." *ICLR Workshop on Efficient Transformers*, 2025.
- Ongoing work on using randomized SVD to initialize efficient attention patterns (connecting to Chen's ASA framework).

#### With Prof. James Liu (Computer Science)

Prof. Rodriguez and Prof. Liu collaborate on **federated PCA** — computing principal components across distributed data sources without centralizing data. This has applications in:
- **Privacy-preserving student analytics:** Analyzing student performance data across multiple institutions.
- **Healthcare:** Federated learning for multi-hospital medical studies.

Their joint paper, "Federated Principal Component Analysis with Communication Efficiency," is under review at *KDD 2026*.

#### With Dr. Emily Watson (Biomedical Engineering)

Prof. Rodriguez provides mathematical consultation on dimensionality reduction techniques for the dermoscopy image dataset used in the Chen-Watson collaboration on few-shot rare disease diagnosis (see biomedical_ml_collab.md).

## Teaching

Prof. Rodriguez teaches MATH 205 (Linear Algebra) and MATH 410 (Numerical Linear Algebra). Her MATH 205 course is a required prerequisite for CS 201 and CS 301 in the machine learning sequence.

She is known for her emphasis on **geometric intuition** — teaching eigenvalues through visual transformations rather than rote computation, and connecting abstract vector space theory to practical applications in machine learning.

## Selected Publications

1. Rodriguez, M. "Randomized SVD for Scalable PCA." *SIAM Review*, 2019.
2. Rodriguez, M. and Chen, S. "Low-Rank Attention Analysis." *ICLR Workshop*, 2025.
3. Rodriguez, M. and Liu, J. "Federated PCA." *Under review, KDD 2026*.
4. Rodriguez, M. et al. "Scalable Tensor Decompositions." *SIAM J. Matrix Analysis*, 2021.

## Contact

Prof. Rodriguez's office: Mathematics Building Room 410. Email: m.rodriguez@university.edu.
"""
    },
    {
        "filename": "student_survey_2025.md",
        "stage": "stage3",
        "category": "research_essay",
        "content": """# Student Survey Results: Machine Learning Course Sequence — Fall 2025

**Prepared by:** Department of Computer Science, Office of Educational Assessment
**Survey Period:** December 2025
**Response Rate:** 78% (187/240 students)

---

## 1. Overview

This survey assessed student satisfaction, learning outcomes, and curriculum coherence across the three-course ML sequence: CS 201 (Introduction to Machine Learning, Prof. James Liu), MATH 205 (Linear Algebra, Prof. Maria Rodriguez), and STAT 210 (Probability and Statistical Inference, Prof. Thomas Brown). Students who had completed at least two of the three courses were eligible to respond.

## 2. Overall Satisfaction

| Course | Instructor | Satisfaction (1–5) | Would Recommend |
|--------|------------|--------------------|--------------------|
| CS 201 | Prof. Liu | 4.6 | 94% |
| MATH 205 | Prof. Rodriguez | 4.3 | 88% |
| STAT 210 | Prof. Brown | 4.1 | 82% |
| **Average** | | **4.3** | **88%** |

## 3. Key Findings

### 3.1 Curriculum Coherence

**88% of students** agreed or strongly agreed that "the prerequisites (MATH 205, STAT 210) were well-aligned with what I needed for CS 201."

> *"MATH 205 eigenvalue theory clicked immediately when we did PCA in CS 201. I could see exactly why the math mattered."* — 3rd-year CS student

> *"STAT 210's Bayesian inference section was the most useful thing I learned all year. It made regularization intuitive."* — 4th-year Statistics student

### 3.2 Preparation for CS 301

Among students who completed CS 201 and were planning to take CS 301:

- **91%** felt well-prepared for advanced topics (transformers, attention).
- **7%** felt somewhat prepared but wanted more depth on neural networks.
- **2%** felt underprepared (cited gaps in programming skills, not conceptual understanding).

> *"Prof. Liu's top-down approach really works. I understood WHY transformers matter before we dove into the HOW."* — 3rd-year CS student

### 3.3 Instructor Quality

| Dimension | Prof. Liu | Prof. Rodriguez | Prof. Brown |
|-----------|-----------|-----------------|-------------|
| Clarity of explanation | 4.7 | 4.5 | 4.0 |
| Responsiveness to questions | 4.6 | 4.2 | 4.3 |
| Relevance of examples | 4.8 | 4.1 | 3.9 |
| Fairness of assessment | 4.4 | 4.4 | 4.5 |
| Overall | 4.6 | 4.3 | 4.1 |

### 3.4 Areas for Improvement

The most common suggestions:

1. **More hands-on coding in MATH 205:** 62% of students requested more programming assignments (Python/MATLAB) to connect abstract theory to computation.
2. **Better integration of STAT 210 with ML applications:** 55% wanted more ML examples in the statistics course.
3. **Office hours accessibility:** Some students reported difficulty accessing Prof. Rodriguez's office hours due to scheduling conflicts.
4. **Project guidelines in CS 201:** 38% wanted clearer rubrics for the programming projects.

## 4. Cross-Course Connections

Students were asked about the connections between courses:

- **MATH 205 → CS 201:** "Eigenvalues and PCA" was cited as the most relevant connection (71%).
- **STAT 210 → CS 201:** "Bayesian inference and regularization" was the top connection (64%).
- **CS 201 → CS 301:** "Backpropagation and neural networks" was the primary bridge (82%).

## 5. Demographics

- 58% Computer Science majors
- 22% Data Science majors
- 12% Statistics majors
- 8% Other (Mathematics, Engineering, Biology)

## 6. Recommendations

1. Add a Python-based computational component to MATH 205 (coordinate with Prof. Rodriguez).
2. Create a "bridge module" connecting STAT 210's Bayesian inference to ML regularization (coordinate with Prof. Brown and Prof. Liu).
3. Publish sample CS 201 projects from previous semesters as exemplars.
4. Synchronize office hours across the three courses to facilitate student cross-questioning.

---

*Full survey data available from the Office of Educational Assessment.*
"""
    },
    {
        "filename": "alex_kim_notes.md",
        "stage": "stage3",
        "category": "homework",
        "content": """# Alex Kim — Research Notes: Sparse Attention Experiments

**Ph.D. Student, Prof. Sarah Chen's Lab**
**Period:** January – April 2026

---

## Week 1 (Jan 12–16): Setup

Set up the experimental environment for ASA (Adaptive Sparse Attention) experiments:
- PyTorch 2.2 with CUDA 12.1
- Custom ASA implementation based on Chen et al. (2022)
- Baseline: standard multi-head attention (8 heads, d_model=256)
- Dataset: synthetic sequence classification (length 512, 10 classes)

**Initial results:** ASA with k=64 achieves 94.2% accuracy vs. 95.1% full attention. Only 23% of attention weight computed.

## Week 2 (Jan 19–23): Gating Network Design

Experimented with different gating architectures for ASA:
- Linear gate: 93.8% (too simple)
- 2-layer MLP: 94.2%
- **Residual gate with layer norm: 94.7%** ← selected for further experiments

The residual gate allows the model to learn a perturbation on top of uniform attention, which converges faster.

## Week 3 (Jan 26–30): Sparsity Analysis

Analyzed what ASA learns to attend to in a simple language model:
- Adjacent tokens: 45% of attention budget
- Sentence-level tokens (first word of each sentence): 20%
- Task-relevant tokens (e.g., negation words for sentiment): 35%

This suggests ASA is learning linguistically meaningful sparsity patterns, not just local neighborhoods.

## Week 4 (Feb 2–6): Dermoscopy Dataset

Received the dermoscopy dataset from Dr. Emily Watson (1,200 images, 15 conditions). Preprocessing:
- Resize to 224×224
- Normalize with ImageNet statistics
- Augmentation: random horizontal flip, color jitter

Split: 60% train (episodic), 20% val, 20% test. Each episode samples C classes from N-way task.

## Week 5 (Feb 9–13): ProtoNet Baseline

Implemented Prototypical Networks baseline on dermoscopy:
- Backbone: ResNet-18 (pretrained on ImageNet)
- Embedding dim: 64
- Results: 55.8% (1-shot), 68.2% (5-shot), 74.0% (10-shot)

These match reported numbers in the literature.

## Week 6 (Feb 16–20): Cross-Attention Prototype Refinement

Implemented cross-attention between support embeddings within each class:
- Support embeddings attend to each other before averaging into prototypes.
- Without sparsity: 71.9% (5-shot) — improved but overfits.
- With ASA sparsity (k=8): **73.5% (5-shot)** ← significant improvement.

The sparsity prevents overfitting in the cross-attention by limiting each support embedding to attending to at most 8 others (out of ~40 support examples in 5-shot 8-way).

## Week 7 (Feb 23–27): Ablation Studies

| Configuration | 5-shot acc. |
|---|---|
| ProtoNet baseline | 68.2% |
| + cross-attention | 71.9% |
| + ASA sparsity (k=8) | 73.5% |
| + ASA sparsity (k=4) | 71.1% |
| + ASA sparsity (k=16) | 73.2% |

Sweet spot is k=8 for this dataset. Lower k under-attends, higher k re-introduces overfitting.

## Week 8 (Mar 2–6): Collaboration with Marcus

Marcus Johnson joined the project to handle the medical image processing pipeline:
- Implemented test-time augmentation (TTA): horizontal flip + color jitter
- TTA improves 5-shot accuracy from 73.5% to 74.2%
- Marcus is writing the capstone report (see capstone_ml_medical.md)

## Week 9 (Mar 9–13): Scaling Experiments

Tested ASA on larger models:
- ResNet-50 backbone: 75.1% (5-shot), up from 73.5% with ResNet-18
- ViT-Small backbone: 76.8% (5-shot) — best result so far

ViT's patch-based attention interacts well with the ASA sparsity pattern.

## Week 10 (Mar 16–20): Paper Preparation

Started writing MICCAI paper with Priya Sharma (see biomedical_ml_collab.md):
- Paper 1: "Sparse Attention for Few-Shot Medical Image Classification"
- Target: MICCAI 2027
- Drafting introduction and related work sections.

## Week 11 (Mar 23–27): Seminar Presentation

Presented ASA scaling results at CS 490 seminar (see cs490_seminar_notes.md):
- ASA provides increasing gains as model size grows
- At 1B parameters, ASA saves 40% compute with <1% quality loss
- Prof. Chen suggested exploring ASA for the music generation project too

## Week 12 (Apr 6–10): Integration with Music Generation

Brief consultation with Fatima Al-Rashid and Derek Lee on their music generation project (see project_gan_music.md):
- Shared the gating network architecture from ASA
- Their results validate that sparsity helps even in generative settings

## Summary

Key results from this research period:
1. ASA gating network with residual connections achieves 94.7% on synthetic tasks.
2. ProtoNet + cross-attention + ASA sparsity achieves **73.5% 5-shot accuracy** on dermoscopy.
3. ASA gains increase with model scale (confirmed at seminar).
4. Two papers in preparation: MICCAI 2027 and Scientific Data.
"""
    },
    {
        "filename": "department_report_2026.md",
        "stage": "stage3",
        "category": "research_essay",
        "content": """# Department of Computer Science — Annual Report 2025–2026

**Prepared by:** CS Department Chair, Prof. Robert Taylor
**Date:** May 2026

---

## 1. Executive Summary

The 2025–2026 academic year was a landmark year for the Department of Computer Science. Research funding grew by 23%, enrollment in the machine learning course sequence increased by 35%, and faculty published in top-tier venues including NeurIPS, ICML, ICLR, and MICCAI.

## 2. Research Highlights

### 2.1 Grants and Funding

| Grant | PI | Amount | Source |
|---|---|---|---|
| Efficient Attention for Scalable AI | Prof. Sarah Chen | $1.2M | NSF IIS |
| Federated Learning for Healthcare | Prof. James Liu & Prof. Chen | $800K | NIH R01 |
| Tensor Methods for Data Science | Prof. Maria Rodriguez | $450K | NSF DMS |
| Biomedical Image Analysis | Dr. Emily Watson (BME) & Prof. Chen | $650K | NIH R21 |
| **Total new funding** | | **$3.1M** | |

This represents a **23% increase** over the previous year ($2.52M).

### 2.2 Publications

Faculty and students published 47 papers, including:

- **Chen, S. et al.** "Adaptive Sparse Attention for Scalable Transformers." *NeurIPS 2022* (highly cited, 340+ citations in 2025–2026).
- **Rodriguez, M. and Chen, S.** "Low-Rank Attention Analysis." *ICLR Workshop on Efficient Transformers*, 2025.
- **Rodriguez, M. and Liu, J.** "Federated Principal Component Analysis." *Under review, KDD 2026*.
- **Sharma, P. et al.** "Sparse Attention for Few-Shot Medical Image Classification." *In preparation for MICCAI 2027*.
- **Watson, E., Johnson, M., and Chen, S.** "Curated Dermoscopy Dataset for Few-Shot Learning." *In preparation for Scientific Data*.

### 2.3 Student Achievements

- **Alex Kim** (Ph.D., Prof. Chen): Selected for the NeurIPS 2025 Student Workshop; presented ASA scaling results at CS 490 seminar.
- **Priya Sharma** (Ph.D., Prof. Chen): Won the CS department's Best Paper Award for her literature review on meta-learning; co-leading the biomedical collaboration.
- **Marcus Johnson** (M.S., Prof. Chen): Capstone project on few-shot medical image classification achieved 73.5% 5-shot accuracy (see capstone_ml_medical.md).
- **Fatima Al-Rashid** (undergraduate): CS 301 project on attention-based music generation accepted to the ACM Student Research Competition.
- **Derek Lee** (undergraduate): Co-author on the music generation project; hired as a TA for STAT 210.

## 3. Enrollment and Teaching

### 3.1 Course Enrollment

| Course | Instructor | Fall 2024 | Fall 2025 | Growth |
|---|---|---|---|---|
| CS 201 (Intro ML) | Prof. Liu | 95 | 128 | +35% |
| MATH 205 (Linear Algebra) | Prof. Rodriguez | 110 | 132 | +20% |
| STAT 210 (Probability) | Prof. Brown | 88 | 105 | +19% |
| CS 301 (Adv ML) | Prof. Chen | 42 | 58 | +38% |

The **35% growth in CS 201** reflects broader industry demand for ML skills. We have responded by adding a second section for Fall 2026.

### 3.2 New Courses

- **CS 490: Advanced Topics Seminar** (Prof. Chen): Launched Spring 2026. First topic: scaling laws and emergent abilities in LLMs (see cs490_seminar_notes.md).
- **CS 350: Federated Learning** (Prof. Liu, planned for Fall 2026): New course covering distributed ML, privacy, and secure computation.

### 3.3 Student Evaluations

Per the Student Survey (see student_survey_2025.md):
- Average satisfaction across ML sequence: **4.3/5.0**
- 88% would recommend the sequence to other students
- Key strength: curriculum coherence across courses
- Key improvement area: more hands-on coding in MATH 205

## 4. Collaborative Initiatives

The department has strengthened interdisciplinary collaboration:

- **Chen–Watson Biomedical Collaboration:** Two papers in preparation; dataset of 1,200 dermoscopy images curated (see biomedical_ml_collab.md).
- **Chen–Rodriguez Attention Analysis:** Joint work on low-rank structure in attention matrices.
- **Liu–Rodriguez Federated PCA:** Under review at KDD 2026.
- **Cross-course coordination:** Profs. Chen, Liu, Rodriguez, and Brown coordinate the ML course sequence to ensure prerequisite alignment.

## 5. Infrastructure

- **GPU Cluster:** Upgraded to 32 NVIDIA A100 GPUs (from 16) — supports larger model training and student projects.
- **Data Lab:** New collaborative workspace for graduate students, equipped with dual monitors and whiteboard walls.
- **Cloud Credits:** AWS research credits ($50K) for distributed experiments.

## 6. Looking Ahead: 2026–2027

1. **Hiring:** One new tenure-track position in AI Safety and Alignment.
2. **Curriculum:** Launch CS 350 (Federated Learning) and expand CS 201 to two sections.
3. **Research:** Submit NIH R01 renewal for the Chen–Watson biomedical collaboration.
4. **Partnerships:** Establish industry partnerships with 2 healthcare AI companies for clinical validation.

## 7. Acknowledgments

Thanks to all faculty, students, and staff for a productive year. Special thanks to Prof. Chen for her leadership in interdisciplinary research and to Prof. Liu for his curriculum development work.

---

*Department of Computer Science, College of Engineering*
*For questions: cs-chair@university.edu*
"""
    },
    {
        "filename": "watson_biomed_notes.md",
        "stage": "stage3",
        "category": "course_material",
        "content": """# BME 305: Biomedical Signal Processing — Guest Lecture Notes

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
"""
    },
]


def word_count(text: str) -> int:
    return len(text.split())


def main():
    # Create stage directories
    for stage in ["stage1", "stage2", "stage3"]:
        (CORPUS_DIR / stage).mkdir(parents=True, exist_ok=True)

    manifest = {"documents": [], "qa_pairs": []}

    for doc in DOCUMENTS:
        stage_dir = CORPUS_DIR / doc["stage"]
        filepath = stage_dir / doc["filename"]
        content = doc["content"].strip() + "\n"
        filepath.write_text(content, encoding="utf-8")

        rel_path = f"{doc['stage']}/{doc['filename']}"
        wc = word_count(doc["content"])

        manifest["documents"].append({
            "filename": doc["filename"],
            "stage": doc["stage"],
            "category": doc["category"],
            "path": rel_path,
            "word_count": wc,
        })

        print(f"  OK {rel_path} ({wc} words)")

    # Write manifest
    manifest_path = CORPUS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifest written to {manifest_path}")
    print(f"Total documents: {len(manifest['documents'])}")

    counts = {}
    for d in manifest["documents"]:
        counts[d["stage"]] = counts.get(d["stage"], 0) + 1
    for stage, count in sorted(counts.items()):
        print(f"  {stage}: {count} documents")


if __name__ == "__main__":
    main()
