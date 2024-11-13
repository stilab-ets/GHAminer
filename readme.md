## About the project:
GHBminer is a data collection tool that enables practitioners and researchers to monitor, optimize, and improve Continuous Integration (CI) performance on GitHub Actions (GHA). This project is designed to extract a set of 45 GitHub-specific build metrics to provide insights into key CI workflow aspects such as build duration, test results, code changes, and repository metadata.

These metrics, listed in the next section (Metrics), capture build outcomes and workflow configurations across various levels of detail, offering valuable data-driven insights into CI efficiency and quality. The tool operates via modular components that facilitate efficient data extraction, commit history analysis, build log parsing, and more, while minimizing API load to enhance performance and scalability.



## Metrics:
The following table provides the list of the 45 metrics collected by GHBMiner:

| Metric Name                | Description                                                                                                 | Unit / Example          |
|----------------------------|-------------------------------------------------------------------------------------------------------------|--------------------------|
| id_build                   | Unique identifier of the build in the project                                                               | Integer / 9460091666     |
| branch                     | Branch of the repository where the build was executed                                                       | String / main            |
| commit_sha                 | SHA of the commit associated with the build                                                                 | String / f63d348b2273c...|
| languages                  | Programming languages used in the project                                                                   | String / Java            |
| status                     | Build status (e.g., completed, failed)                                                                      | String / completed       |
| conclusion                 | Build result (e.g., success, failure)                                                                       | String / failure         |
| created_at                 | Creation date of the build                                                                                  | Date / 2024-06-11T05:..  |
| updated_at                 | Last updated date of the build                                                                              | Date / 2024-06-11T05:... |
| build_duration             | Build process duration in seconds                                                                          | Float / 213              |
| total_builds               | Total number of builds in the file                                                                          | Integer / 67             |
| gh_files_added             | Number of files added by the commits                                                                        | Integer / 0              |
| gh_files_deleted           | Number of files deleted by the commits                                                                      | Integer / 0              |
| gh_files_modified          | Number of files modified by the commits                                                                     | Integer / 1              |
| tests_ran                  | Whether tests were executed                                                                                | Other / False            |
| gh_lines_added             | Number of (production code) lines added by the commits                                                      | Integer / 13             |
| gh_lines_deleted           | Number of (production code) lines deleted by the commits                                                    | Integer / 1              |
| file_types                 | File types used in the build                                                                                | String / .java           |
| gh_tests_added             | Lines of test code added by the commits                                                                     | Integer / 0              |
| gh_tests_deleted           | Lines of test code deleted by the commits                                                                   | Integer / 0              |
| gh_test_churn              | Number of test code lines changed                                                                           | Integer / 0              |
| gh_src_churn               | Number of production code lines changed                                                                     | Integer / 14             |
| gh_pull_req_number         | GitHub pull request number                                                                                  | Integer / 0              |
| gh_is_pr                   | Whether this build was triggered by a pull request                                                          | Other / False            |
| gh_sloc                    | Number of executable source lines of code in the repository                                                 | Integer / 138900         |
| gh_description_complexity  | Total words in title and description if `gh_is_pr` is true                                                  | Integer / 0              |
| gh_src_files               | Number of production files in the commits                                                                   | Integer / 1              |
| gh_doc_files               | Number of documentation files in the commits                                                                | Integer / 0              |
| gh_other_files             | Number of other files in the commits                                                                        | Integer / 0              |
| git_num_committers         | Number of comments on Git commits                                                                           | Integer / 130            |
| gh_job_id                  | Unique job ID(s) in the project                                                                             | String / [26058288671,...]|
| total_jobs                 | Total number of jobs in the build workflow                                                                  | Integer / 3              |
| gh_first_commit_created_at | Timestamp of the first commit in the push triggering the build                                              | String / 2024-06-11T05:...|
| gh_team_size_last_3_months | Team size contributing within the last 3 months                                                             | Integer / 5              |
| gh_commits_on_files_touched| Number of unique modifications to files in this build within the last 3 months                              | Integer / 1              |
| gh_num_pr_comments         | Number of comments on this pull request if `gh_is_pr` is true                                              | Integer / 0              |
| git_merged_with            | SHA1 of the commit that merged this pull request                                                            | String / 43860b4f4...    |
| gh_test_lines_per_kloc     | Test density: lines in test cases per 1,000 SLOC                                                            | Double / 226.4363        |
| build_language             | Build log parser used (e.g., Java-maven, Java-gradle)                                                       | String / java-maven      |
| total_dependencies         | Total number of dependencies used in the project                                                            | Integer / 24             |
| workflow_file_size         | `build.yml` total lines of code                                                                            | Integer / 57             |
| test_framework             | Test frameworks recognized and invoked by the analyzer                                                     | String / junit           |
| tests_passed               | Number of tests passed if available (depends on `build_language` and `test_framework`)                      | Integer / 4136           |
| tests_failed               | Number of tests failed if available                                                                        | Integer / 4              |
| tests_skipped              | Number of tests skipped if available                                                                       | Integer / 312            |
| tests_total                | Total number of tests in the project                                                                        | Integer / 4452           |




## Getting Started:
To get a local copy of GHBminer up and running, follow these steps.

#### Prerequisites

Ensure you have the following installed:

- Python 3.x

Install the required package:

```bash
pip install requests
```

#### Installation
1. Clone the repository:
```bash
git clone https://github.com/stilab-ets/GHBminer.git
```

2. Navigate to the project directory:
```bash
cd GHBminer
```



## Usage:

GHBminer is a standalone Python script that can be executed from the command line on any operating system with Python 3.x installed. 

To run GHBminer, use the following command along with the specified parameters:

```bash
python GHBMetrics.py <parameters>
```
#### Parameters:

`-t, --token` : GitHub personal access token for API access.

`-p, --projects` : CSV file path containing the list of repositories to analyze.

`-s, --single-project` : (Optional) GitHub repository URL for analyzing a single project without using a CSV file.

`-fd` : Start date for the date range of builds to retrieve.

`-td` : End date for the date range of builds to retrieve.

#### Example Usage:
To analyze repositories from a CSV file and save the results:
```bash
python GHBMetrics.py -t <Your_GitHub_Token> -p /path/to/repositories.csv -fd 2023-01-01 -td 2023-12-31
```
To analyze a single repository:
```bash
python GHBMetrics.py -t <Your_GitHub_Token> -s <GitHub_Repository_URL> -fd 2023-01-01 -td 2023-12-31
```


## Output:
GHBminer generates a CSV file, where each row contains metrics for a unique build. Below is an example row to illustrate the output format:
```bash
| Metric                       | Value                                  |
|------------------------------|----------------------------------------|
| repo                         | gluonhq/gluonfx-maven-plugin           |
| id_build                     | 6171745243                             |
| branch                       | master                                 |
| commit_sha                   | 587198416ab5396a17fac86da131ae61f8473ef7 |
| languages                    | Java                                   |
| status                       | completed                              |
| conclusion                   | success                                |
| created_at                   | 2023-09-13T11:20:12Z                   |
| updated_at                   | 2023-09-13T11:21:55Z                   |
| build_duration               | 103.0                                  |
| total_builds                 | 3                                      |
| gh_files_added               | 0                                      |
| gh_files_deleted             | 0                                      |
| gh_files_modified            | 0                                      |
| tests_ran                    | False                                  |
| gh_lines_added               | 52                                     |
| gh_lines_deleted             | 42                                     |
| file_types                   | .xml                                   |
| gh_tests_added               | 0                                      |
| gh_tests_deleted             | 0                                      |
| gh_test_churn                | 0                                      |
| gh_src_churn                 | 94                                     |
| gh_pull_req_number           | 0                                      |
| gh_is_pr                     | False                                  |
| gh_sloc                      | 52                                     |
| gh_description_complexity     | 0                                      |
| gh_src_files                 | 2                                      |
| gh_doc_files                 | 0                                      |
| gh_other_files               | 0                                      |
| git_num_committers           | 8                                      |
| gh_job_id                    | [16750594224]                          |
| total_jobs                   | 1                                      |
| gh_first_commit_created_at   | 2023-09-13T11:20:08Z                   |
| gh_team_size_last_3_month    | 3                                      |
| gh_commits_on_files_touched  | 1                                      |
| gh_num_pr_comments           | 0                                      |
| git_merged_with              | (empty)                                |
| gh_test_lines_per_kloc       | 0.0                                    |
| build_language               | java-maven                             |
| test_framework               | []                                     |
| tests_passed                 | 0                                      |
| tests_failed                 | 0                                      |
| tests_skipped                | 0                                      |
| tests_total                  | 0                                      |
| fetch_duration               | 4.887585639953613                      |
```





## Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Your contributions are genuinely valued and greatly appreciated.

If you have ideas or improvements to enhance the project, we encourage you to fork the repository and initiate a pull request. Alternatively, feel free to open an issue labeled "enhancement" to share your suggestions. Don't forget to show your support by starring the project! Thank you once again for being a part of this collaborative journey.

Here's a step-by-step guide to guide you through the contribution process:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request for review


## License:
Distributed under the MIT License. See `LICENSE.md` for more information.


## Contact:
Jasem Khelifi - jasemkhelifi[at]gmail.com



