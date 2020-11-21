---
title:  Hypothesis Testing
---

Classical frequentist hypothesis testing can be very [confusing](https://en.wikipedia.org/wiki/Statistical_hypothesis_testing#Cautions). Everytime I come back to it I find myself needing to refresh a lot of the concepts and to convince myself that I am interpreting the results correctly. Making inferences about parameters that aren't random variables has never felt natural to me. This is why certain researchers recommend using [Bayesian alternatives](https://encyclopediaofmath.org/wiki/The_significance_test_controversy_and_the_bayesian_alternative). Changing framework doesn't come with costs though, and sometimes the frequentist framework is really what we should be using.

I found a way to rid my brain of the cognitive dissonance associated with hypothesis testing, by using parallels with anomaly detection that are often two different interpretations of the same procedure!

# Anomaly Detection vs. Hypothesis Testing

Suppose you are the owner of Charlie Chaplin's factory.
<iframe src="/assets/videos/charlie-chaplin-factory.gif" width="500" height="376" frameBorder="0" class="giphy-embed" allowFullScreen></iframe>

Charlie's assembly line is manufacturing bolts specified to be 25cm wide. In order to safeguard the solid reputation of your factory, you ask Charlie to reject all anomalously wide bolts, both too small and too long. After quality controlling a day's output of bolts, you conclude that their width is well modeled by a normal distribution centered at 25cm with a 0.01cm standard deviation. Arguing that a 0.03cm error off of 25cm is invisible to the naked eye, you decide to reject only those bolts with width outside of [24.97,25.03]. According to the [3-sigma rule](https://en.wikipedia.org/wiki/68%E2%80%9395%E2%80%9399.7_rule), this entails that Charlie will be throwing away 0.3% of the bolts produced, which you deem reasonable.

A year later, Charlie reports having thrown away 3% of the bolts after a long day of work. Is Charlie an incompetent that should be fired, was this just an anomalous day, or does this rather mean that the bolt-producing machine needs repair? Or perhaps there is another explanation behind this situation? Solving this question requires hypothesis testing knowledge.

Detecting the anomalous bolts is clearly a anomaly detection problem, and deciding which theory best explains Charlie's lousy day is clearly a hypothesis testing problem. But are the two concepts really that different? The "was this just an anomalous day" was thrown in the list of theories to highlight their connection.

![pi-x-pgm](/assets/hypothesis-testing/pi-x-pgm.svg)

Every probabilistic model separates the parameters $\theta$ from the data $X$. For the factory example above, $\theta=(\mu,\sigma^2)$ is the parameters of a Normal distribution and $X_i$ is the width of bolt $i$. Suppose we start with a given set of parameters, and we receive data. We can be in two different situations:
- Anomaly Detection: we trust the model parameters, and want to test the data
- Hypothesis Testing: we trust the data, and want to test the model parameters

Surprisingly, we will see that in many cases, these two seemingly different tests are actually one and the same, and it is only the conclusion that is reached that is different.

# Generic Test

<iframe src="/assets/hypothesis-testing/normal_mu_hyptest.html" width="50%" height="360px"></iframe>

# Most Powerful Test: Likelihood Ratio test and Neyman-Pearson Lemma

![likelihood-ratio-diagram](/assets/hypothesis-testing/likelihood-ratio-pgm.svg)

### Generic tests derived from LR test

|Model | Param | LR $\frac{f_{\theta_1(x)}}{f_{\theta_0}(x)}$ | Summary Statistic $T(X)$ | Test|
|:----:|:-----:|:-----------------------------------------:|:-----------------:|:---:|
|$N(\mu, \sigma^2)$ | $\mu$ | $\exp\left(\frac{2(\mu_1-\mu_0)\sum x_i + n(\mu_0^2 - \mu_1^2)}{2\sigma^2} \right)$ | $\sum X_i \| H_0 \sim N(n\mu_0, n\sigma^2)$ | $\mu_1 > \mu_0: \sum x_i > c$ $\mu_1 < \mu_0 : \sum x_i < c$|
|$N(\mu, \sigma^2)$ | $\sigma^2$ | $(\frac{\sigma_0}{\sigma_1})^n \exp\left( (\frac{1}{2\sigma_0^2}-\frac{1}{2\sigma_1^2}) \sum (x_i-\mu)^2 \right)$ | $\sum \frac{(X_i - \mu)^2}{\sigma_0^2} \| H_0 \sim \chi_n^2$ | $\sigma_1 > \sigma_0 : \sum \frac{(x_i - \mu)^2}{\sigma_0^2} > c$ $\sigma_1 < \sigma_0 : \sum \frac{(x_i - \mu)^2}{\sigma_0^2} < c$ 
| Exp($\lambda$) | $\lambda$ | $(\frac{\lambda_1}{\lambda_0})^n \exp \left( -(\lambda_1 - \lambda_0) \sum x_i \right)$ | $\sum X_i \| H_0 \sim \text{Gamma}(n, \lambda_0)$ | $\lambda_1 > \lambda_0 : \sum x_i < c$ $\lambda_1 < \lambda_0 : \sum x_i > c$
| Ber($\pi$) | $\pi$ | $\left( \frac{\pi_0(1-\pi_1)}{(1-\pi_0)\pi_1}\right)^{\sum X_i} \left(\frac{1-\pi_0}{1-\pi_1}\right)^n$ | $\sum X_i \| H_0 \sim \text{Bin}(n,\pi_0)$ | $\pi_{1}>\pi_{0}: \sum x_i > c$ $\pi_{1}<\pi_{0}: \sum x_i < c $


