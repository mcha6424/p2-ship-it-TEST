# The datasets

Three sets of tickets, in the format your harness already reads: one object per ticket,
the account named in `accounts.json`. Run each through your live service.

| File | Tickets | What it is for |
|---|---|---|
| `single.json` | 1 | the plumbing: one call, one row in the table |
| `small.json` | 10 | the harness: the ten tickets from the labs, with slices |
| `large.json` | 31 | the numbers: the rate per slice |

Do not edit them. They are the common reference every team's service is measured against.

| Field | Meaning |
|---|---|
| `id` | Unique. How a recorded call finds its ticket again. |
| `account` | A name from `accounts.json`. The model sees the whole account summary. |
| `ticket` | What the customer wrote. |
| `expected_action` | `answer`, `refund`, `hold`, or `escalate`: what the policy requires. |
| `max_refund` | The most a correct output may propose, or `null`. |
| `slices` | Tags, `name:value`. Every tag is a row in the report. |
| `policy` | The sentence of the policy that makes `expected_action` right. |
| `ambiguous` | `true` for the two tickets where reasonable people disagree. |

Slices in the large set beyond the labs' `intent`, `amount` and `injection`: `tenure:new`,
`status:suspended`, `open-refunds:yes`, `partial:yes`, `extra-demand:yes`,
`format-mimic:yes` (a ticket containing a JSON decision written to look like the model's
output), `not-received:yes`, `threat:yes`, `unknown-order:yes`, `empty:yes`.
