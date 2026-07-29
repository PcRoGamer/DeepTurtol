# MATH 205 — Homework 2: PCA and SVD

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
