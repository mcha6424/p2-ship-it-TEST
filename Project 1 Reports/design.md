# 3.1 Requirements Brief 

## What decision does the model make?
The model takes an input (text from a ticket, and account information), and produces an output that includes an action, amount, and a rationale. The model tries to triage tickets given some simple rules so it can automate responses to some tickets. Automations can include answering questions, issuing a refund, or holding or escalating a refund request that is above a certain amount. Anything that is a 'hold' or 'escalate' goes to a human reviewer. Incorrect decisions can cause refunds that should not be authorized, triaging tickets to a human review process when they should be automatic (causing longer wait time for the customer), or fail to provide answers to customer questions.

## Should this be a model at all?
The refund limits and guidelines don't require an LLM, but interpretting customer text does. A change to the model could be that the LLM is used to determine the values of variable and assign them, then the program can sort the variables as inputs into a final decision.

## Requirements

### 90% of tickets requesting refunds under $50 get processed automatically
Both policy in system (100%) and policy in user (93%) cleared this threshold. If the ticket gets misclassified as an "answer", the system fails. If it misclassifies the ticket as a "hold" or "escalate" it will still get processed by the human reviewer, but take longer to get a response.

### 90% of questions get a correct and accurate answer within 1 second
The policy in user (85%), and policy in system (73%) did not clear this bar. If these tickets get misclassified as 'refund' the system fails, and the company loses money. If it gets misclassified as 'hold' or 'escalate' it's also a failure. The questions would go to a human for review and the customer would not get a repsonse within 1 second. Queuing and sending a 'message recieved' message would acknowledge a ticket (and could do so in 1 second), but it would not answer the question, and it would still be misclassified.

### 90% of tickes with a max refudn of over-200 are escalated
The policy in user failed with 81% and policy in system (91%)met this requirement. The Policy in system also improved it's accuracy on the injection:yes slice, which all the injections fit into the over-200 slice. This means that the policy in system is better identifying injections and accurately classifying over-200s better. For 'answer' misclassification, the customer does not get their refund. However, they may see that the response they get is not what they are looking for, which could result in another ticket. So, the ticket may fail, but the customer will have another shot at getting the result they want. For a 'refund' misclassification, the company may have issued a refund anyways, but if there is another step in the process or added customer service, those would be missed. If the misclassification is 'hold' there is no real consequence since the ticket would go to a human reviewer.