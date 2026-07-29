# MATH 205: Linear Algebra — Lecture Notes (Weeks 1–4)

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
