# STAT 210: Probability and Statistical Inference — Key Concepts

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
