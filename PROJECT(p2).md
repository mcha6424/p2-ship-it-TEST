# P2 — Ship it

Stand up the triage service behind a public API, write every inference to a DynamoDB
table, and run your evaluation harness against the live service on three datasets.

Everything you need exists: the public API from the *publish the API* lab, the harness
from P1, and the datasets in this repository. The project is to put them together.

## Deliverables

1. **A git repository**, private, the instructor and your partner as collaborators,
   tagged `p2` by the deadline in Canvas. It holds the service code, your harness, your
   scripts, and a README that says how to deploy, run and query everything from a clean
   clone.
2. **A public URL** that answers `POST /triage` and shows `GET /docs`, with the token,
   submitted in Canvas. Every response carries a build identifier.
3. **Every inference in a DynamoDB table.** One item per call: request id, time, build,
   model, latency, the action, the amount, whether the output parsed, any error. No
   ticket text. A script in the repository pulls a day's rows and prints them.
4. **The harness run against the live URL** on `data/datasets/single.json`,
   `small.json` and `large.json`, scored per slice. The results are read back from the
   table, not from your laptop.
5. **A write-up**, two pages, outlining: the rate of right actions per slice on the large
   set; what the table and the log showed that the harness alone did not (latency, cold
   starts, errors, anything unexpected); and the two changes you would make next.

## How it is graded

| Deliverable | Weight |
|---|---|
| 1. Repository, runnable from a clean clone | 15% |
| 2. The service, public, with a build identifier | 15% |
| 3. The inference table and the script that reads it | 25% |
| 4. The harness on the three datasets | 25% |
| 5. The write-up | 20% |

## Budget

About 100 live calls: the three datasets once each, with room to repeat. The function,
the API and the table cost nothing while idle. One key per student, in `.env`, never in
a commit.

## Permitted and prohibited

AI assistance is permitted and expected; you are responsible for every line. Any tool is
permitted, but the harness and the script that reads the table must be yours to read.
Do not edit the datasets.
