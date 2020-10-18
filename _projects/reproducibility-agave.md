---
title:  "Reproducing Auxiliary Guided Autoregressive Variational Autoencoder"
description: "IFT-6269 Probabilistic Graphical Models - Final Project"
date:   2017-11-20
abstract: "We reproduce the Auxiliary Guided Autoregressive Variational autoEncoder (AGAVE) model, which combines the global information of Variational Autoencoders (VAEs) with the local consistency of PixelCNNs. The corresponding loss function generalizes the variational lower bound used to train VAEs and permits using an autoregressive model as a decoder to generate lower-level image details. We implemented the proposed model, and can confirm the main finding of the paper, which is that this approach yields nearly identical likelihood scores as using only the Pixel-CNN++, while efficiently leveraging the VAE’s latent representation. Our code can be found [here](https://github.com/pclucas14/aux-vae)."
---

<iframe src="https://drive.google.com/file/d/1pCGJhgwBviVVNm8y-3M5b7ypJTp7QR9p/preview" width="640" height="480"></iframe>