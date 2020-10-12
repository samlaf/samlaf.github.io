---
title:  Optimization vs Sampling based algorithms
---

A priori it would seem like sampling is a stupid idea, and optimization should always win (except when we actually want to compute an expected value as in MC methods).

However it seems like when dealing with real world noise, we can't do much better than sampling. Examples:
- [RANSAC](https://en.wikipedia.org/wiki/Random_sample_consensus)

Note: Actually, for any parameter in an algorithm, we can either 1. assign it a value (eg. fixed distance measure), 2. optimize it, or 3. sample it (and do something with the samples)

### RANSAC
We want to do regression that is robust to outliers. Instead of "finding" the outliers by some "smart" (optimization) procedure, all we do is to subsample the dataset many times, and use the best regression line. That is, we are hoping one of our subsamples will contain very few outliers...