---
title:  Etherscan Puzzle Scam
category: blockchain
---

EDIT: this is a honeypot!!
https://honeypot.is/ethereum.html
https://www.youtube.com/watch?v=DDn5mksOUCc

My brother found this fucker:
https://etherscan.io/address/0x2b977007ea88dfdf3bee259e63b6d18a7fc1aed9
whose code is (supposedly according to etherscan)
```
/**
 *Submitted for verification at Etherscan.io on 2021-01-27
*/

contract Ridle_Game
{
    function Try(string _response) external payable 
    {
        require(msg.sender == tx.origin);

        if(responseHash == keccak256(_response) && msg.value > 1 ether)
        {
            msg.sender.transfer(this.balance);
        }
    }

    string public question;

    bytes32 responseHash;

    mapping (bytes32=>bool) admin;

    function Start(string _question, string _response) public payable isAdmin{
        if(responseHash==0x0){
            responseHash = keccak256(_response);
            question = _question;
        }
    }

    function Stop() public payable isAdmin {
        msg.sender.transfer(this.balance);
    }

    function New(string _question, bytes32 _responseHash) public payable isAdmin {
        question = _question;
        responseHash = _responseHash;
    }

    constructor(bytes32[] admins) public{
        for(uint256 i=0; i< admins.length; i++){
            admin[admins[i]] = true;        
        }       
    }

    modifier isAdmin(){
        require(admin[keccak256(msg.sender)]);
        _;
    }

    function() public payable{}
}
```
QUESTION TO ANSWER: can this be the wrong code? The decompiler doesn't even show the function start...?!?
The contract source code is verified with an exact match... but maybe he actually used another solidity compiler version which results in exact match
even though the source code is different?


He tried reverse engineering the stored responseHash with the following code:
```
from web3 import Web3
import sys

# First we get the storage from the smart contract
infura_url = "https://mainnet.infura.io/v3/ca59be150c824096b43ba48fbc5ebe00"
web3 = Web3(Web3.HTTPProvider(infura_url))
contract = "0x2B977007EA88DFdF3beE259e63b6D18a7fC1aeD9"
memblock1 = web3.eth.get_storage_at(contract, 1)
print(memblock1)
```

QUESTION TO ANSWER: why memblock1?

Good thing we weren't experienced enough to realized that the contract was initialized with `Start` and not `New`, so that the answer was there in plain sight.
![](/assets/etherscan-puzzle-scam/contract-txs.png)
![](/assets/etherscan-puzzle-scam/contract-Start()-arguments.png)


Doing this would have taken all the funds (~15 ETH) out of the contract.... or would it have?


have a look at this very very similar contract (https://etherscan.io/address/0x7d3b61b6a731fe0696ec84d76fe398338f8f7694)
where someone actually tried the Try() method with the correct answer.

How did I find these contracts?
With this fantastic tool called bitquery: https://explorer.bitquery.io/ethereum/smart_contract/0x2b977007ea88dfdf3bee259e63b6d18a7fc1aed9/graph?from=2020-12-16&till=2022-01-17
![](/assets/etherscan-puzzle-scam/bitquery-txs-graph.png)

Our contract is the one at the far right. The whole chain of accounts/contracts is the same individual moving funds between different addresses and using them to create new similar contracts, trying to scam new people (perhaps new contracts are near the top of etherscan so he needs to deploy new contracts to trap people who are scanning etherscan for exploits?)

QUESTION TO ANSWER: ask bitquery if they can add a feature to add date/time on the graph. It would be nice to see when these txs were made

