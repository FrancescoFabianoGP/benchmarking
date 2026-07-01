# Coaction Initial Benchmark Draft

This report is the first thin benchmark loop built from the local
Coaction and UniCourt venue-risk tables stored under `cases/coaction_venue_risk/data`.

## Scorecard

- Runner: `structured_lookup`
- Cases: `15`
- Overall accuracy: `100.0%`
- Average latency: `0.03 ms`
- Total input tokens: `None`
- Total output tokens: `None`
- Total tokens: `None`
- Estimated cost: `n/a`

## Accuracy By Dataset

| Dataset | Accuracy | Cases |
|---|---:|---:|
| coaction | 100.0% | 7 |
| unicourt | 100.0% | 8 |

## Accuracy By Query Type

| Query Type | Accuracy | Cases |
|---|---:|---:|
| county_metric_extreme | 100.0% | 10 |
| county_top_judge_dismissal_rate | 100.0% | 5 |

## Case Results

| Case | Dataset | Prompt | Expected | Predicted | Correct |
|---|---|---|---|---|---|
| case-0001 | unicourt | Which county has the lowest average case duration for Personal Injury and Torts? Use the unicourt overall court stats table. | Bronx County | Bronx County | yes |
| case-0002 | unicourt | Which county has the lowest average time to resolution for Personal Injury and Torts? Use the unicourt overall court stats table. | Los Angeles County | Los Angeles County | yes |
| case-0003 | unicourt | Which county has the highest motion-to-dismiss success rate for Personal Injury and Torts? Use the unicourt overall court stats table. | Bronx County | Bronx County | yes |
| case-0004 | unicourt | Which county has the highest summary-judgment success rate for Personal Injury and Torts? Use the unicourt overall court stats table. | Los Angeles County | Los Angeles County | yes |
| case-0005 | unicourt | Which county resolves no-trial Personal Injury and Torts cases the fastest on average? Use the unicourt overall court stats table. | Bronx County | Bronx County | yes |
| case-0006 | coaction | Which county has the lowest average case duration for Personal Injury and Torts? Use the coaction overall court stats table. | Bronx County | Bronx County | yes |
| case-0007 | coaction | Which county has the lowest average time to resolution for Personal Injury and Torts? Use the coaction overall court stats table. | Bronx County | Bronx County | yes |
| case-0008 | coaction | Which county has the highest motion-to-dismiss success rate for Personal Injury and Torts? Use the coaction overall court stats table. | Bronx County | Bronx County | yes |
| case-0009 | coaction | Which county has the highest summary-judgment success rate for Personal Injury and Torts? Use the coaction overall court stats table. | Los Angeles County | Los Angeles County | yes |
| case-0010 | coaction | Which county resolves no-trial Personal Injury and Torts cases the fastest on average? Use the coaction overall court stats table. | Kings County | Kings County | yes |
| case-0011 | unicourt | For Bronx County, which judge has the highest dismissal rate in the unicourt judge table overall rows? | MASS TORT JUDGE | MASS TORT JUDGE | yes |
| case-0012 | unicourt | For Kings County, which judge has the highest dismissal rate in the unicourt judge table overall rows? | GARSON, HON. ROBIN S. | GARSON, HON. ROBIN S. | yes |
| case-0013 | unicourt | For Los Angeles County, which judge has the highest dismissal rate in the unicourt judge table overall rows? | RAUL A. SAHAGUN | RAUL A. SAHAGUN | yes |
| case-0014 | coaction | For Bronx County, which judge has the highest dismissal rate in the coaction judge table overall rows? | GUZMAN, HON. WILMA | GUZMAN, HON. WILMA | yes |
| case-0015 | coaction | For Kings County, which judge has the highest dismissal rate in the coaction judge table overall rows? | RIVERA, HON. FRANCOIS A. | RIVERA, HON. FRANCOIS A. | yes |
