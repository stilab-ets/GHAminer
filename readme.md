## About the project:




## Metrics:


## Metrics

The following table provides a comprehensive list of the metrics collected by the tool:

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





## Usage:





## Output:





## Evaluation:


## Contributing


## License:



## Contact:



## How to cite:


