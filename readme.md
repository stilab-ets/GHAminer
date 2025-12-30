## About the project:
GHAminer is a data collection tool that enables practitioners and researchers to monitor, optimize, and improve Continuous Integration (CI) performance on GitHub Actions (GHA). This project is designed to extract a comprehensive set of GitHub-specific build metrics to provide insights into key CI workflow aspects such as build duration, test results, code changes, and repository metadata.

These metrics, listed in the next section (Metrics), capture build outcomes and workflow configurations across various levels of detail, offering valuable data-driven insights into CI efficiency and quality. The tool operates via modular components that facilitate efficient data extraction, commit history analysis, build log parsing, and more, while minimizing API load to enhance performance and scalability.



## Configuration:
GHAminer uses a `config.yaml` file to control which metrics are collected and which workflows to analyze. You can enable or disable specific metric groups to customize the output and reduce API calls when you only need certain data.

**By default, all options are set to `true` and all workflows are processed.**

To modify the configuration, edit the `src/config.yaml` file:

```yaml
# Workflow filtering - specify which workflows to analyze
workflow_ids: []                 # Empty = all workflows, or list specific IDs: [12345, 67890]

# Metric collection options
fetch_job_details: true          # Job and step information
fetch_test_parsing_results: true # Test pass/fail counts from logs
fetch_commit_details: true       # Code churn and contributor metrics
fetch_pull_request_details: true # PR-related information
fetch_sloc: true                 # Source lines of code metrics
```

### Workflow Filtering

By default, GHAminer processes **all workflows** in a repository. To analyze only specific workflows:

```yaml
# Process only these specific workflow IDs
workflow_ids:
  - 12345678
  - 87654321
```

To find workflow IDs:
1. **GitHub API**: `GET https://api.github.com/repos/{owner}/{repo}/actions/workflows`
2. **GitHub UI**: Navigate to Actions → select a workflow → the ID is in the URL or API response

Set any metric option to `false` to skip collecting those metrics, which can significantly reduce processing time.



## Metrics:
The following tables list all metrics collected by GHAminer, organized by configuration groups.

### Core Metrics (Always Collected)
These metrics are always included in the output regardless of configuration settings.

| Metric Name                    | Description                                                              | Unit / Example                |
| ------------------------------ | ------------------------------------------------------------------------ | ----------------------------- |
| repo                           | Full repository name (owner/repo)                                        | String / mozilla-bteam/bmo    |
| id\_build                      | Unique identifier of the build (workflow run ID)                         | Integer / 15115327064         |
| workflow\_id                   | Workflow ID in the repository                                            | Integer / 69080091            |
| issuer\_name                   | Username of the person who triggered the workflow                        | String / dklawren             |
| branch                         | Branch of the repository where the build was executed                    | String / main                 |
| commit\_sha                    | SHA of the commit associated with the build                              | String / 34aa9260e20f...      |
| languages                      | Primary programming language used in the project                         | String / Perl                 |
| status                         | Build status (e.g., completed, in\_progress, queued)                     | String / completed            |
| workflow\_event\_trigger       | Event that triggered the workflow (e.g., push, pull\_request, schedule)  | String / pull\_request        |
| conclusion                     | Build result (e.g., success, failure, cancelled, skipped)                | String / success              |
| run\_attempt                   | The attempt number of the workflow run (1 for first attempt, 2+ for retries) | Integer / 1               |
| created\_at                    | Start time of the latest run attempt                                     | Date / 2025-05-19T14:13:13Z   |
| updated\_at                    | End time of the latest run attempt                                       | Date / 2025-05-19T14:29:12Z   |
| build\_duration                | Duration of the latest run attempt in seconds                            | Float / 959.0                 |
| total\_builds                  | Running count of builds processed for this workflow                      | Integer / 1                   |
| gh\_first\_commit\_created\_at | Timestamp of the head commit associated with the workflow run            | Date / 2025-05-19T14:12:09Z   |
| build\_language                | Build tool/language detected (e.g., java-maven, python-pip, nodejs-npm)  | String / java-maven           |
| dependencies\_count            | Number of dependencies detected in build files                           | Integer / 45                  |
| workflow\_size                 | Number of lines in the workflow YAML file                                | Integer / 82                  |
| test\_framework                | Test frameworks detected in the project (e.g., junit, pytest, jest)      | List / \["pytest", "jest"]    |
| workflow\_name                 | Name of the workflow as defined in the YAML file                         | String / BMO Test Suite       |
| fetch\_duration                | Time taken to fetch and process data for this build (in seconds)         | Float / 4.75                  |


### Job Details (`fetch_job_details: true`)
Information about jobs and steps within each workflow run.

| Metric Name  | Description                                                                        | Unit / Example                |
| ------------ | ---------------------------------------------------------------------------------- | ----------------------------- |
| gh\_job\_id  | List of job IDs in the workflow run                                                | List / \[42484452320, ...]    |
| total\_jobs  | Total number of jobs in the workflow run                                           | Integer / 7                   |
| job\_details | JSON structure containing job and step details (names, start/end times, durations) | JSON / \[{"job\_name": ...}]  |
| tests\_ran   | Whether tests were executed (detected from job/step names containing "test")       | Boolean / True                |


### Test Parsing Results (`fetch_test_parsing_results: true`)
Test results extracted by parsing build logs. Supports 50+ test frameworks including pytest, JUnit, Jest, RSpec, Go test, Cargo test, PHPUnit, and many more.

| Metric Name    | Description                       | Unit / Example |
| -------------- | --------------------------------- | -------------- |
| tests\_passed  | Number of tests that passed       | Integer / 150  |
| tests\_failed  | Number of tests that failed       | Integer / 2    |
| tests\_skipped | Number of tests that were skipped | Integer / 5    |
| tests\_total   | Total number of tests executed    | Integer / 157  |


### Commit Details (`fetch_commit_details: true`)
Code change metrics and contributor statistics derived from commit analysis.

| Metric Name                    | Description                                                       | Unit / Example    |
| ------------------------------ | ----------------------------------------------------------------- | ----------------- |
| gh\_files\_added               | Number of files added by the commits                              | Integer / 3       |
| gh\_files\_deleted             | Number of files deleted by the commits                            | Integer / 1       |
| gh\_files\_modified            | Number of files modified by the commits                           | Integer / 12      |
| file\_types                    | List of file extensions changed in the commits                    | List / \[".py", ".js"] |
| gh\_lines\_added               | Total lines of code added                                         | Integer / 107     |
| gh\_lines\_deleted             | Total lines of code deleted                                       | Integer / 18      |
| gh\_src\_churn                 | Total source code churn (lines added + lines deleted)             | Integer / 125     |
| gh\_tests\_added               | Lines of test code added                                          | Integer / 25      |
| gh\_tests\_deleted             | Lines of test code deleted                                        | Integer / 5       |
| gh\_test\_churn                | Total test code churn (test lines added + deleted)                | Integer / 30      |
| gh\_src\_files                 | Number of source code files in the commits                        | Integer / 8       |
| gh\_doc\_files                 | Number of documentation files in the commits                      | Integer / 2       |
| gh\_other\_files               | Number of other files in the commits                              | Integer / 1       |
| gh\_commits\_on\_files\_touched| Number of commits on touched files within the last 3 months       | Integer / 8       |
| dockerfile\_changed            | Number of Dockerfile changes in the commits                       | Integer / 0       |
| docker\_compose\_changed       | Number of docker-compose file changes in the commits              | Integer / 0       |
| git\_num\_committers           | Total number of unique committers since the start of the project  | Integer / 281     |
| git\_commits                   | Total number of commits in the repository up to this run          | Integer / 13480   |
| gh\_team\_size\_last\_3\_month | Number of unique committers in the last 3 months                  | Integer / 7       |


### Pull Request Details (`fetch_pull_request_details: true`)
Information about associated pull requests (when the build is PR-related).

| Metric Name                | Description                                            | Unit / Example        |
| -------------------------- | ------------------------------------------------------ | --------------------- |
| gh\_pull\_req\_number      | Pull request number (0 if not a PR-triggered build)    | Integer / 42          |
| gh\_is\_pr                 | Indicates if the build is associated with a pull request | Boolean / True      |
| gh\_num\_pr\_comments      | Number of comments on the associated PR                | Integer / 5           |
| git\_merged\_with          | SHA of the merge commit (if the PR was merged)         | String / 43860b4f4... |
| gh\_description\_complexity| Word count of the PR title and description combined    | Integer / 150         |


### Source Lines of Code (`fetch_sloc: true`)
Repository size and test density metrics calculated using the `scc` tool.

| Metric Name              | Description                                        | Unit / Example |
| ------------------------ | -------------------------------------------------- | -------------- |
| gh\_sloc                 | Total source lines of code in the repository       | Integer / 230963 |
| gh\_test\_lines\_per\_kloc | Test density: lines of test code per 1,000 SLOC  | Float / 72.63  |



## Getting Started:
To get a local copy of GHAminer up and running, follow these steps.

#### Prerequisites

Ensure you have the following installed:

- Python 3.x
- Git (for cloning repositories during analysis)

Install the required packages:

```bash
pip install requests pandas numpy pyyaml
```

#### Installation
1. Clone the repository:
```bash
git clone https://github.com/stilab-ets/GHAminer.git
```

2. Navigate to the project directory:
```bash
cd GHAminer/src
```



## Usage:

GHAminer is a standalone Python script that can be executed from the command line on any operating system with Python 3.x installed. 

To run GHAminer, use the following command along with the specified parameters:

```bash
python GHAMetrics.py <parameters>
```

#### Input projects csv file (github_projects.csv): 
Ensure the CSV file does not contain a header (column name), and each row contains a single GitHub repository link.

#### Parameters:

`-t, --token` : GitHub personal access token for API access.

`-p, --projects` : CSV file path containing the list of repositories to analyze.

`-s, --single-project` : (Optional) GitHub repository URL for analyzing a single project without using a CSV file.

`-fd, --from_date` : (Optional) Start date for the date range of builds to retrieve.

`-td, --to_date` : (Optional) End date for the date range of builds to retrieve.



## GitHub Token Permissions:
To ensure GHAminer runs successfully, your GitHub token must have the following permissions:

- **Actions**: Read access
  - To fetch workflows, runs, logs, and job details.
- **Contents**: Read access
  - To retrieve files and their contents (e.g., `.github/workflows/build.yml`).
- **Commits**: Read access
  - To access commit details and contributors.
- **Metadata**: Read access
  - To access repository details, such as languages and contributors.
- **Pull Requests**: Read access
  - To retrieve pull request details, comments, and merge commits.
- **Contributors**: Read access
  - To fetch the list of contributors to the repository.

#### Example Usage:
To analyze repositories from a CSV file and save the results:
```bash
python GHAMetrics.py -t <Your_GitHub_Token> -p /path/to/repositories.csv
```

To analyze a single repository:
```bash
python GHAMetrics.py -t <Your_GitHub_Token> -s https://github.com/owner/repo
```

To analyze with date filtering:
```bash
python GHAMetrics.py -t <Your_GitHub_Token> -s https://github.com/owner/repo -fd 2023-01-01 -td 2023-12-31
```


For detailed usage, please refer to this video:

[![Video Title](https://img.youtube.com/vi/4ZC71ootygA/0.jpg)](https://www.youtube.com/watch?v=4ZC71ootygA)


## Output:
GHAminer generates a CSV file (`builds_features.csv`), where each row contains metrics for a unique build. Please refer to `example_output.csv` for an example of build metrics collected for one repository.


## Supported Technologies:

### Build Systems Detected (40+)
Java (Maven, Gradle, Ant), JavaScript/TypeScript (npm, yarn, pnpm, bun), Python (pip, poetry, pipenv, conda), Ruby (Bundler), Go, Rust (Cargo), PHP (Composer), Swift (SPM, CocoaPods), Kotlin, Scala (sbt), Elixir (Mix), C/C++ (CMake, Make, Meson, Bazel), Dart/Flutter, and more.

### Test Frameworks Detected (60+)
pytest, unittest, JUnit, TestNG, Jest, Mocha, Vitest, RSpec, Minitest, NUnit, xUnit, MSTest, Go test, Cargo test, PHPUnit, Pest, XCTest, Kotest, ScalaTest, ExUnit, Google Test, Catch2, Playwright, Cypress, and many more.

### Dependency Files Supported (30+)
`pom.xml`, `build.gradle`, `package.json`, `requirements.txt`, `pyproject.toml`, `Gemfile`, `go.mod`, `Cargo.toml`, `composer.json`, `Package.swift`, `pubspec.yaml`, `CMakeLists.txt`, and more.


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


