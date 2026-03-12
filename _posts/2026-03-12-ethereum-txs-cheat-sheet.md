---
title:  "Ethereum Transactions Cheat Sheet"
category: blockchain
---

<style>
.cheat-wrap {
  overflow: auto;
  max-height: 80vh;
  border: 1px solid #ddd;
}
/* break out of Minima's narrow content column on desktop */
@media (min-width: 800px) {
  .cheat-wrap {
    width: 90vw;
    margin-left: calc(50% - 45vw);
  }
}
.cheat-wrap table {
  border-collapse: separate;
  border-spacing: 0;
  min-width: 900px;
  font-size: 0.85rem;
  line-height: 1.4;
}
.cheat-wrap th,
.cheat-wrap td {
  padding: 6px 10px;
  border: 1px solid #ddd;
  vertical-align: top;
  background: #fff;
}
/* sticky header row */
.cheat-wrap thead th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #1a1a2e;
  color: #fff;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}
/* sticky Concern column (first col) — exclude group headers */
.cheat-wrap tbody tr:not(.group-header) td:first-child,
.cheat-wrap thead th:first-child {
  position: sticky;
  left: 0;
  z-index: 4;
  background: #1a1a2e;
  color: #fff;
  font-weight: 600;
  min-width: 200px;
  max-width: 280px;
  box-shadow: 2px 0 4px rgba(0,0,0,0.15);
}
.cheat-wrap thead th:first-child {
  z-index: 11;
  background: #1a1a2e;
}
/* code inside dark columns */
.cheat-wrap tbody tr:not(.group-header) td:first-child code,
.cheat-wrap thead th code {
  background: rgba(255,255,255,0.15);
  color: #fff;
}
/* group header rows — z-index below sticky header so they scroll behind it */
.cheat-wrap .group-header td {
  background: #eef;
  font-weight: 700;
  font-size: 0.9rem;
  padding: 8px 10px;
  border-bottom: 2px solid #bbc;
}
/* feature subtitle in concern cells */
.cheat-wrap td:first-child .feature {
  display: block;
  font-weight: 400;
  font-size: 0.8em;
  opacity: 0.65;
  margin-top: 2px;
}
/* ensure group-header first-child keeps its color */
.cheat-wrap .group-header td:first-child {
  background: #eef;
}
</style>

<div class="cheat-wrap">
<table>
<thead>
<tr>
  <th>Concern</th>
  <th>EIP-1559 tx</th>
  <th>EIP-4337 UserOp</th>
  <th>EIP-8141 Frame tx</th>
  <th>Porto</th>
  <th>Tempo tx</th>
  <th>Seismic tx</th>
</tr>
</thead>
<tbody>

<tr class="group-header"><td colspan="7">Authentication — Mechanism</td></tr>
<tr>
  <td>Signing scheme <span class="feature">Flexible auth</span></td>
  <td>ECDSA (secp256k1)</td>
  <td>Anything (ECDSA, P256, WebAuthn, multisig, MPC, ZK proof)</td>
  <td>ECDSA or P256 natively; smart accounts define freely</td>
  <td>secp256k1, P256, WebAuthn, External/ISigner (EVM-verified)</td>
  <td>ECDSA, WebAuthn, P256</td>
  <td>secp256k1 (EIP-712 <code>message_version</code>)</td>
</tr>
<tr>
  <td>Signing cardinality <span class="feature">Multisig / threshold</span></td>
  <td>1-of-1 only</td>
  <td>N-of-M, threshold, social recovery — account defines</td>
  <td>N-of-M — account defines</td>
  <td>1-of-1 per key (External → m-of-n via MultiSigSigner)</td>
  <td>1-of-1 (or account-defined?)</td>
  <td>1-of-1</td>
</tr>

<tr class="group-header"><td colspan="7">Authentication — Policy</td></tr>
<tr>
  <td>Who authorized execution?</td>
  <td>signer = sender = payer (all one)</td>
  <td>Smart account <code>validateUserOp</code></td>
  <td><code>VERIFY</code> frame → <code>APPROVE(0x0)</code></td>
  <td>keyHash (super admin or session)</td>
  <td>app-defined</td>
  <td>signer = sender = payer</td>
</tr>
<tr>
  <td>Who authorized payment? <span class="feature">Gas sponsorship</span></td>
  <td><em>same as sender</em> (implicit)</td>
  <td>Paymaster <code>validatePaymasterUserOp</code> (or self-pay)</td>
  <td><code>VERIFY</code> frame → <code>APPROVE(0x1)</code></td>
  <td>Account pays tokens → relayer; relayer pays ETH</td>
  <td><code>fee_payer_signature</code> (separate signer)</td>
  <td>Same as sender</td>
</tr>
<tr>
  <td>Can sender ≠ payer?</td>
  <td>No</td>
  <td>Yes — Paymaster is separate entity</td>
  <td>Yes — <code>APPROVE(0x2)</code> opts into collapse; otherwise distinct</td>
  <td>Yes</td>
  <td>Yes — separate signers</td>
  <td>No</td>
</tr>

<tr class="group-header"><td colspan="7">Authorization — Payment</td></tr>
<tr>
  <td>Gas pricing <span class="feature">EIP-1559 gas</span></td>
  <td>maxFee, maxPriority, gasLimit</td>
  <td>maxFee, maxPriority, preVerificationGas, per-op gasLimits</td>
  <td>maxFee, maxPriority, per-frame <code>gas_limit</code></td>
  <td>EIP-1559 + <code>combinedGas</code> in Intent</td>
  <td>EIP-1559 fees</td>
  <td><code>gas_price</code> (legacy)</td>
</tr>
<tr>
  <td>Gas token <span class="feature">ERC-20 gas payment</span></td>
  <td>ETH only</td>
  <td>ETH (Paymaster accepts ERC-20 off-protocol)</td>
  <td>ETH (sponsor accepts ERC-20 via frames)</td>
  <td>ETH (relayer); tokens (account → relayer)</td>
  <td><code>fee_token</code> (any TIP-20 stablecoin)</td>
  <td>ETH only</td>
</tr>

<tr class="group-header"><td colspan="7">Authorization — Temporal Replay</td></tr>
<tr>
  <td>Sequence (don't execute twice) <span class="feature">Nonce</span></td>
  <td>nonce (sequential, protocol-enforced)</td>
  <td>nonce (2D: <code>key ‖ sequence</code> in EntryPoint)</td>
  <td>nonce (protocol-enforced, incremented by <code>APPROVE</code>)</td>
  <td>Sequential per 192-bit key (on account)</td>
  <td>nonce (sequential)</td>
  <td>Sequential (legacy)</td>
</tr>
<tr>
  <td>Validity window <span class="feature">Time/block-based validity</span></td>
  <td>None (valid until included or nonce consumed)</td>
  <td><code>validUntil</code>, <code>validAfter</code> (paymaster can enforce)</td>
  <td>None (app-defined in frame logic)</td>
  <td><code>Intent.expiry</code></td>
  <td><code>valid_before</code> + <code>valid_after</code></td>
  <td><code>recent_block_hash</code> + <code>expires_at_block</code></td>
</tr>

<tr class="group-header"><td colspan="7">Authorization — Spatial Replay</td></tr>
<tr>
  <td>Cross-chain protection</td>
  <td>chainId (in RLP, protocol-enforced)</td>
  <td>chainId (in UserOp hash)</td>
  <td>chainId (in RLP)</td>
  <td>EIP-712 domain separator</td>
  <td>domainSeparator</td>
  <td><code>chainId</code></td>
</tr>
<tr>
  <td>Cross-type protection <span class="feature">Domain separation</span></td>
  <td>RLP structure (not valid EIP-191)</td>
  <td>Wrapped inside regular tx (bundler submits 0x00–0x04)</td>
  <td><code>0x06 ‖ RLP(...)</code></td>
  <td>EIP-712 type hashes</td>
  <td>tx type / EIP-712?</td>
  <td><code>0x4A ‖ RLP(…)</code></td>
</tr>
<tr>
  <td>Nonce lane selection <span class="feature">2D nonces</span></td>
  <td>—</td>
  <td>Yes (<code>nonce_key</code>)</td>
  <td>—</td>
  <td>Yes (192-bit key prefix)</td>
  <td>Yes (<code>nonce_key</code>)</td>
  <td>—</td>
</tr>

<tr class="group-header"><td colspan="7">Execution — Payload</td></tr>
<tr>
  <td>Payload structure</td>
  <td>single: to, value, data</td>
  <td>single: to, value, calldata</td>
  <td><code>frames[]</code> — ordered (mode, target, gas_limit, data)</td>
  <td><code>calls[]</code> — ERC-7821 <code>Call{target,value,data}</code></td>
  <td><code>calls[]</code> (batched)</td>
  <td>Single <code>to, value, data</code></td>
</tr>
<tr>
  <td>Multicall <span class="feature">Call batching</span></td>
  <td>—</td>
  <td>— (account contracts often implement it)</td>
  <td>Yes — multi-frame</td>
  <td>Yes</td>
  <td>Yes — native <code>calls[]</code></td>
  <td>—</td>
</tr>

<tr class="group-header"><td colspan="7">Execution — Lifecycle / Concurrency / EVM</td></tr>
<tr>
  <td>Account deployment</td>
  <td>Separate tx</td>
  <td><code>initCode</code> in first UserOp</td>
  <td>Frame 0 as <code>DEFAULT</code> calling deployer</td>
  <td>7702 delegation tx</td>
  <td>aa_authorization_list</td>
  <td>—</td>
</tr>
<tr>
  <td>Pre-warm storage / parallel execution <span class="feature">Access lists</span></td>
  <td>access_list (declares touched slots upfront)</td>
  <td>—</td>
  <td>Warm/cold journal shared across frames</td>
  <td>Inherits from carrier tx</td>
  <td>—</td>
  <td>None</td>
</tr>
<tr>
  <td><code>msg.sender</code> at depth 0</td>
  <td>from (= signer)</td>
  <td>account address (via EntryPoint)</td>
  <td><code>SENDER</code>: <code>tx.sender</code>. <code>DEFAULT</code>/<code>VERIFY</code>: <code>ENTRY_POINT</code></td>
  <td>Orchestrator (or self if direct)</td>
  <td>?</td>
  <td><code>from</code> (= signer)</td>
</tr>
<tr>
  <td><code>tx.origin</code></td>
  <td>from (= signer)</td>
  <td>bundler EOA (!)</td>
  <td>frame's <code>caller</code> (varies per frame!)</td>
  <td>Relayer EOA</td>
  <td>?</td>
  <td><code>from</code> (= signer)</td>
</tr>

<tr class="group-header"><td colspan="7">Confidentiality — Data</td></tr>
<tr>
  <td>Calldata privacy <span class="feature">Calldata encryption</span></td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>encrypted (ECDH+AEAD)</td>
</tr>
<tr>
  <td>Response privacy <span class="feature">Response encryption</span></td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>encrypted</td>
</tr>
<tr>
  <td>Authenticated reads <span class="feature">Signed reads</span></td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td>—</td>
  <td><code>signed_read</code></td>
</tr>

</tbody>
</table>
</div>

## Transaction Serialization Format

<div class="cheat-wrap" style="max-height: none;">
<table>
<thead>
<tr>
  <th>Byte(s)</th>
  <th>Name</th>
  <th>Context</th>
  <th>Wire / Signing Format</th>
</tr>
</thead>
<tbody>

<tr class="group-header"><td colspan="4">On-Chain Transaction Types (EIP-2718 envelope)</td></tr>
<tr>
  <td><code>0x00</code></td>
  <td>Legacy (Homestead)</td>
  <td>On-chain tx</td>
  <td><code>RLP([nonce, gasPrice, gasLimit, to, value, data, v, r, s])</code></td>
</tr>
<tr>
  <td><code>0x01</code></td>
  <td>EIP-2930 (Berlin)</td>
  <td>On-chain tx</td>
  <td><code>0x01 ‖ RLP([chainId, nonce, gasPrice, gasLimit, to, value, data, accessList, v, r, s])</code></td>
</tr>
<tr>
  <td><code>0x02</code></td>
  <td>EIP-1559 (London)</td>
  <td>On-chain tx</td>
  <td><code>0x02 ‖ RLP([chainId, nonce, maxPriorityFee, maxFee, gasLimit, to, value, data, accessList, v, r, s])</code></td>
</tr>
<tr>
  <td><code>0x03</code></td>
  <td>EIP-4844 (Dencun)</td>
  <td>On-chain tx</td>
  <td><code>0x03 ‖ RLP([chainId, nonce, maxPriorityFee, maxFee, gasLimit, to, value, data, accessList, maxFeePerBlobGas, blobVersionedHashes, v, r, s])</code></td>
</tr>
<tr>
  <td><code>0x04</code></td>
  <td>EIP-7702 (Pectra)</td>
  <td>On-chain tx</td>
  <td><code>0x04 ‖ RLP([chainId, nonce, maxPriorityFee, maxFee, gasLimit, to, value, data, accessList, authorizationList, v, r, s])</code></td>
</tr>
<tr>
  <td><code>0x06</code></td>
  <td>EIP-8141 Frame tx (draft)</td>
  <td>On-chain tx</td>
  <td><code>0x06 ‖ RLP([chainId, nonce, …, frames[], v, r, s])</code></td>
</tr>
<tr>
  <td><code>0x4A</code></td>
  <td>TxSeismic</td>
  <td>On-chain tx</td>
  <td><code>0x4A ‖ RLP([chainId, nonce, maxFee, maxPriorityFee, gasLimit, to, value, data, accessList, encryptionPubkey, encryptionNonce, validBefore, validAfter, v, r, s])</code></td>
</tr>
<tr>
  <td><code>0x4B</code></td>
  <td>TxSeismicRead</td>
  <td>Signed read (never in blocks)</td>
  <td><code>0x4B ‖ RLP([…])</code> — same fields as 0x4A, different EIP-712 domain</td>
</tr>
<tr>
  <td><code>0x76</code></td>
  <td>TempoTx</td>
  <td>On-chain tx</td>
  <td><code>0x76 ‖ RLP([chainId, nonce, …, calls[], fee_token, …, v, r, s])</code></td>
</tr>

<tr class="group-header"><td colspan="4">Signing-Only Domains (not wire tx types)</td></tr>
<tr>
  <td><code>0x05</code></td>
  <td>EIP-7702 authorization</td>
  <td>Signing domain</td>
  <td><code>keccak256(0x05 ‖ RLP([chainId, address, nonce]))</code></td>
</tr>
<tr>
  <td><code>0x19 0x00</code></td>
  <td>EIP-191 validator data</td>
  <td>Off-chain sig</td>
  <td><code>0x19 ‖ 0x00 ‖ validatorAddress ‖ data</code></td>
</tr>
<tr>
  <td><code>0x19 0x01</code></td>
  <td>EIP-712 typed data</td>
  <td>Off-chain sig</td>
  <td><code>0x19 ‖ 0x01 ‖ domainSeparator ‖ structHash</code></td>
</tr>
<tr>
  <td><code>0x19 0x45</code></td>
  <td>personal_sign</td>
  <td>Off-chain sig</td>
  <td><code>0x19 ‖ "Ethereum Signed Message:\n" ‖ len ‖ message</code></td>
</tr>

<tr class="group-header"><td colspan="4">Reserved Ranges</td></tr>
<tr>
  <td><code>0x05–0x7f</code></td>
  <td>—</td>
  <td>EIP-2718 typed tx range</td>
  <td>Available for future tx types (except assigned above)</td>
</tr>
<tr>
  <td><code>0xc0–0xfe</code></td>
  <td>Legacy tx</td>
  <td>RLP list prefix</td>
  <td>Legacy txs start with RLP list byte (≥ 0xc0), which is how nodes distinguish them from typed txs</td>
</tr>
<tr>
  <td><code>0xff</code></td>
  <td>Reserved</td>
  <td>EIP-2718</td>
  <td>Reserved — also used as CREATE2 address prefix</td>
</tr>

</tbody>
</table>
</div>
