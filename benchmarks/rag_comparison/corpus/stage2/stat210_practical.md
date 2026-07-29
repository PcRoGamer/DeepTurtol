# STAT 210 — Lab 5: Bayesian Linear Regression

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
