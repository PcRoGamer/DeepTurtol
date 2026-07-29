# Research Profile: Prof. Maria Rodriguez

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
