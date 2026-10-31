# Project 2- Ship it

A support-ticket triage service deployed behind Amazon API Gateway and AWS Lambda. The service calls Gemini, records inference metadata in DynamoDB, and is evaluated against three fixed reference datasets. Evaluation outcomes are read back from DynamoDB and converted into fixtures for per-slice scoring.

Project requirements: [PROJECT(p2).md](PROJECT%28p2%29.md).

## Architecture

```text
Reference tickets + accounts
         |
         v
record.py --provider http
         |
         v
API Gateway -> Lambda/FastAPI -> Gemini
                      |
                      +-> DynamoDB inference metadata
                      +-> CloudWatch structured logs

DynamoDB -> table_to_fixtures.py -> data/fixtures/ddb-<condition>/
                                          |
                                          v
                               score.py + reference dataset
                                          |
                                          v
                                  per-slice evaluation
```

The harness's local HTTP responses are useful diagnostic records. Final table-backed evaluation uses the separately reconstructed `ddb-...` fixtures, not those original response files.

## Prerequisites

- Git and a Bash-compatible shell; Windows instructions assume Git Bash.
- Python 3.12 or newer and `uv`.
- AWS CLI v2.
- A running AWS Academy Learner Lab session with current temporary credentials.
- Access to the pre-created `LabRole` in the Learner Lab account.
- A Gemini API key.
- Access to this private GitHub repository.

The deployment script targets Lambda Python 3.12 on x86_64 and uses `us-east-1`.
The lockfile controls local dependency resolution; `deploy.sh` currently installs its own version-constrained runtime dependencies, so it is not a fully lockfile-pinned Lambda build.

## 1. Clone and install

```bash
git clone https://github.com/mcha6424/p2-ship-it.git
cd p2-ship-it
uv sync

```
Run all subsequent commands from the repository root. Python scripts are executed with `uv run`, not `uv <script>.py`.

## 2. Create local configuration

Create `.env` 
`cp .env.example .env`

Use actual values; do not leave the Gemini placeholder in place. Keep this file compatible with Bash assignment syntax: no spaces around `=`.

The deployment script generates `LAB_TOKEN` if missing and writes `LAB_URL` after deployment. A deployed configuration therefore also contains:

```dotenv
LAB_TOKEN=YOUR_GENERATED_TOKEN
LAB_URL=https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/triage
```

- `INFERENCES_TABLE` is a table name, not an AWS Console URL, and must not be blank.
- `LAB_URL` points to `/triage`, not `/docs` or localhost.
- The local `LAB_TOKEN` must match the deployed service.
- Do not commit `.env`, keys, tokens, or AWS credentials.
- Avoid stale exported variables: Python's dotenv loader normally preserves existing environment values. Clear unintended overrides with `unset INFERENCES_TABLE LAB_URL LAB_TOKEN`, then rerun the Python command.

The repository's `.gitignore` excludes `.env`, `.venv/`, `build/`, and Python caches. It intentionally permits measurement fixtures to be committed. Review artifacts for sensitive data before committing them.

## 3. Deploy

```bash
bash deploy.sh
```

The script builds a Linux-compatible package, creates or reuses the inference table, creates or updates Lambda, creates or reuses the API, and writes the endpoint to `.env`. Defaults:

| Setting | Default |
|---|---|
| Region | `us-east-1` |
| Function | `triage-api` |
| API | `triage-api` |
| Table | `triage-inferences` |
| Runtime | Python 3.12 |
| Memory | 512 MB |
| Timeout | 30 seconds |
| IAM execution role | Existing `LabRole` |

The table uses `day` as partition key and `ts` as sort key. The build identifier is a UTC deployment timestamp with minute resolution, not a Git commit hash. Record the final Git commit separately when reporting results.

The current script uses `uv run python` for token generation and Python's `zipfile` module for packaging, avoiding the separate `python3` and `zip` commands that caused earlier Windows failures.

Changing service code requires redeployment. Changing only local scoring or export code does not. Keep the deployment unchanged across a final evaluation condition.

## 4. Verify the API and Swagger UI

Use the API base URL printed by deployment:

- `GET /`: health and build metadata; open.
- `GET /docs`: Swagger UI; open.
- `POST /triage`: structured triage request; token protected when `LAB_TOKEN` is configured.
- `POST /chat`: one chat turn; also token protected.

In Swagger:

1. Open `<API_BASE_URL>/docs`.
2. Click **Authorize** and paste only the `LAB_TOKEN` value.
3. Expand `POST /triage` and select **Try it out**.
4. Use a valid ticket and full account object, such as the example request.
5. Execute and inspect the returned decision and `function.build`.
6. Verify a corresponding record appears using `uv run inferences.py`.

The `account` value in a dataset is a lookup key, not the full API account body. `record.py` performs this lookup for dataset runs. Do not paste an entire dataset array into `/triage`.

Keep the public URL and token available to the instructor through Canvas. Do not put the actual token in this README.

## 6. Inference records and evaluation linkage

Inference metadata should include request ID, UTC time, build, model, latency, action, refund amount, parse status, and error details when applicable. Do not persist ticket text, account summaries, raw model output, or rationale text in the inference table.

For table-backed evaluation, each evaluation request must carry and persist:

| Field | Example | Purpose |
|---|---|---|
| `case_id` | `v001` | Join observed outcome to reference ticket |
| `dataset` | `single` | Distinguish reference sets |
| `condition` | `p2-single-final-v1` | Identify one evaluation configuration |
| `run` | `1` | Identify the pass through that dataset |

`dataset` should normally equal the dataset filename stem. Keep these identifiers out of the model prompt. Expected actions and labels remain in the unchanged reference files; do not send them to the model.

Old table rows without evaluation identifiers cannot be safely matched by action, amount, or approximate time. Make a fresh identified run after implementing the linkage.

## 7. Run the three reference datasets against the live API

Check the CLI interfaces first:

```bash
uv run record.py --help
uv run score.py --help
uv run table_to_fixtures.py --help
```

Do not proceed if required flags are missing; finish the integration checklist above.

| Dataset | Tickets | Purpose |
|---|---:|---|
| `data/datasets/single.json` | 1 | Plumbing check |
| `data/datasets/small.json` | 10 | Harness and familiar slices |
| `data/datasets/large.json` | 31 | Expanded slice analysis |

Do not modify the datasets. One pass over all three schedules 42 requests. Keep debugging and repeats within the project's approximately 100-call budget.

The commands below explicitly choose system placement of policy. This is the documented example evaluation condition, not an assignment mandate. If using a different placement, change it consistently and report it.

### Single case: verify the full pipeline first

```bash
uv run record.py \
  --provider http \
  --dataset data/datasets/single.json \
  --accounts data/datasets/accounts.json \
  --runs 1 \
  --policy-in system \
  --name p2-single-final-v1
```

Verify one fresh request, one matching table outcome with identifiers, successful conversion, and scoring before continuing.

### Small set

```bash
uv run record.py \
  --provider http \
  --dataset data/datasets/small.json \
  --accounts data/datasets/accounts.json \
  --runs 1 \
  --policy-in system \
  --name p2-small-final-v1
```

### Large set

```bash
uv run record.py \
  --provider http \
  --dataset data/datasets/large.json \
  --accounts data/datasets/accounts.json \
  --runs 1 \
  --policy-in system \
  --name p2-large-final-v1
```

`--provider http` is essential. Without it, the default provider runs the model locally and bypasses the deployed service.

The recorder resumes existing fixture files by case ID. `0 to go` means no new requests will be sent. Use a fresh condition name for a new experiment; do not silently discard failed attempts or mix different deployments under one name.

## 8. Query and export the inference table

```bash
uv run inferences.py
uv run inferences.py --days 2
uv run inferences.py --day 2026-10-31
```

Dates are UTC, not local time. Substitute the actual evaluation date.

To retain an ordinary JSON-lines export:

```bash
mkdir -p results
uv run inferences.py --day 2026-10-31 --json > results/inferences-2026-10-31.jsonl
```

The script also supports `--save`, which writes retrieved daily rows under `data/inference/`. In the inspected implementation it replaces that day's local file rather than appending indefinitely.

Table totals include earlier tests and chat traffic. Reconcile by dataset, condition, run, and case ID, not by total daily item count.

## 9. Convert DynamoDB outcomes into fixtures

Prerequisite: add the supplied `table_to_fixtures.py` and persist evaluation identifiers before recording final runs.

For evaluations performed on UTC date `2026-10-31`:

```bash
uv run table_to_fixtures.py \
  --dataset data/datasets/single.json \
  --condition p2-single-final-v1 \
  --run 1 --day 2026-10-31

uv run table_to_fixtures.py \
  --dataset data/datasets/small.json \
  --condition p2-small-final-v1 \
  --run 1 --day 2026-10-31

uv run table_to_fixtures.py \
  --dataset data/datasets/large.json \
  --condition p2-large-final-v1 \
  --run 1 --day 2026-10-31
```

Replace the date and condition names with your actual runs. Repeat `--day` if a run spans UTC midnight.

The converter writes `run-1.jsonl` and `manifest-1.json` under `data/fixtures/ddb-<source-condition>/`. It validates coverage, rejects duplicates and mixed builds, and refuses to overwrite existing output. A new `--out-name` permits another export without altering the source condition.

Missing outcomes fail conversion by default. `--allow-missing` deliberately creates flagged synthetic error records; disclose them as missing observations, not DynamoDB outcomes. Do not report a smaller denominator because some cases disappeared.

Optional offline conversion from the ordinary JSON-lines export:

```bash
uv run table_to_fixtures.py \
  --input-jsonl results/inferences-2026-10-31.jsonl \
  --dataset data/datasets/single.json \
  --condition p2-single-final-v1 \
  --day 2026-10-31 \
  --out-name ddb-single-offline-check
```

The input must contain the evaluation identifiers. AWS typed JSON exports are not accepted directly.

## 10. Score table-derived outcomes per slice

Prerequisite: `score.py` must support `--dataset` and load that file, not the default golden set. The golden loader must accept the selected path.

```bash
mkdir -p results

uv run score.py ddb-p2-single-final-v1 \
  --dataset data/datasets/single.json \
  --detail > results/single-score.txt

uv run score.py ddb-p2-small-final-v1 \
  --dataset data/datasets/small.json \
  --detail > results/small-score.txt

uv run score.py ddb-p2-large-final-v1 \
  --dataset data/datasets/large.json \
  --detail > results/large-score.txt
```

The `ddb-` conditions identify table-derived fixtures. `score.py` makes no model calls.

Right-action rate is the number of outcomes matching `expected_action` divided by the expected evaluated cases in that slice. Report numerator and denominator as well as percentage. Slices overlap; do not sum them as disjoint groups. Explicitly account for missing and failed outcomes.

For table-derived records, the format scorer should use `output.get("parsed") is True`. Rationale evaluation is unavailable from this metadata-only table; the converter does not invent rationale text or judge verdicts. Preserve provenance rather than implying all P1 checks were rerun.

A one-run best-minus-worst range of zero is not evidence of no model variability; it only reflects that there was one run.

## 11. Inspect CloudWatch and operational evidence

On Git Bash, disable automatic path conversion for the log command:

```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/triage-api \
  --since 2h --region us-east-1
```

Add `--follow` to watch new events. Substitute the function name if customized.

Compare table/log evidence with harness observations:

- Model latency versus client round-trip latency, where retained locally.
- Cold versus warm calls.
- Provider failures and unparsed outcomes.
- DynamoDB write warnings.
- Missing/duplicate case outcomes and unexpected build changes.

The current service logs DynamoDB write failures without failing an otherwise successful API request. Therefore, HTTP success alone does not prove persistence. Hard timeouts may prevent final logging altogether. The current cold-start flag marks the first handled request in a sandbox; a health check may consume that first request before triage arrives.

## 12. Troubleshooting

| Symptom | Action |
|---|---|
| `uv: unrecognized subcommand 'score.py'` | Use `uv run score.py ...`. |
| `unrecognized arguments: --dataset --accounts` | The checked-out recorder lacks the dataset CLI changes; check `--help` and implement them. |
| `score.py` rejects `--dataset` | Add dataset selection to the scorer before evaluating reference files. |
| `python3: command not found` | Use the updated deployment script with `uv run python`. |
| `zip: command not found` | Use the updated deployment script with Python ZIP packaging. |
| CloudWatch rejects `logGroupName` in Git Bash | Prefix the command with `MSYS_NO_PATHCONV=1`. |
| `TableName` is an AWS Console URL | Set `INFERENCES_TABLE=triage-inferences`, not the browser URL. |
| `TableName` length is zero | Correct a blank setting, run `unset INFERENCES_TABLE`, then retry. |
| Expired/invalid AWS credentials | Refresh all three Learner Lab credential values and verify caller identity. |
| HTTP 401 | Check the deployed and local `LAB_TOKEN` values match. |
| No new requests, `0 to go` | Existing recording already contains the case ID; use a new condition for a fresh run. |
| Converter finds no outcomes | Check UTC date, table/account/region, dataset value, source condition, run, and persisted metadata. |
| Converter finds duplicate cases | Inspect retries; preserve evidence and use a fresh final condition if needed. |
| Converter output already exists | Choose a new `--out-name`; do not mix snapshots. |

## 13. Repository map and evidence

```text
PROJECT(p2).md             Assignment requirements
README.md                  Setup and reproduction instructions
deploy.sh                  Package and deploy table/function/API
record.py                  Send reference tickets to the live service
inferences.py              Query and export daily inference records
table_to_fixtures.py        Table-backed fixture conversion (must be added)
score.py                   Evaluate fixtures against selected reference labels
src/function/app.py        API routes, token checks, inference persistence
src/function/handler.py    Lambda adapter
src/system/                Triage implementation and model plumbing
src/harness/               Dataset loading, fixtures, scoring, reports
data/datasets/             Unmodified P2 reference datasets and accounts
data/fixtures/             Original and table-derived recorded outcomes
results/                   Reviewed exports and evaluation reports
```

No evaluation numbers are asserted in this README. Final evidence should identify the actual condition names, UTC dates, deployed build, Git commit, expected/matched/missing cases, and table-derived reports.

## 14. Write-up and submission

Prepare the required two-page write-up with:

1. Large-set right-action counts/rates per slice.
2. Coverage and provenance of table-derived results.
3. Operational observations from DynamoDB and CloudWatch beyond the harness alone.
4. Two specific next changes supported by observed evidence.

Before submission:

- Verify repository privacy and instructor/partner access.
- Verify all documented commands from a separate clean clone.
- Review staged files for keys, tokens, credentials, and sensitive text.
- Include code, scripts, reviewed measurement evidence, and the write-up.
- Commit the final version and publish tag `p2` before the Canvas deadline.
- Submit the public URL and token through Canvas as instructed.

After the final commit is ready, and only if the tag does not already exist:

```bash
git tag p2
git push origin p2
```

Do not replace an existing submission tag without inspecting it and confirming the intended version. Do not tear down the service before the required grading availability period; follow the course's cleanup guidance afterward.
