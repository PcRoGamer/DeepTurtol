# Prof. James Liu: Teaching Philosophy and Curriculum Vision

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
