## About the project:
GHAminer is a data collection tool that enables practitioners and researchers to monitor, optimize, and improve Continuous Integration (CI) performance on GitHub Actions (GHA). This project is designed to extract a set of 55 GitHub-specific build metrics to provide insights into key CI workflow aspects such as build duration, test results, code changes, and repository metadata.

These metrics, listed in the next section (Metrics), capture build outcomes and workflow configurations across various levels of detail, offering valuable data-driven insights into CI efficiency and quality. The tool operates via modular components that facilitate efficient data extraction, commit history analysis, build log parsing, and more, while minimizing API load to enhance performance and scalability.



## Metrics:
The following table provides the list of the 45 metrics collected by GHAminer:

| Metric Name                     | Description                                                                             | Unit / Example                   |
| ------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------- |
| repo                            | Full repository name (owner/repo)                                                       | String / mozilla-bteam/bmo       |
| id\_build                       | Unique identifier of the build in the project                                           | Integer / 15115327064            |
| branch                          | Branch of the repository where the build was executed                                   | String / main                    |
| commit\_sha                     | SHA of the commit associated with the build                                             | String / 34aa9260e20f...         |
| languages                       | Programming languages used in the project                                               | String / Perl                    |
| status                          | Build status (e.g., completed, failed)                                                  | String / completed               |
| conclusion                      | Build result (e.g., success, failure)                                                   | String / success                 |
| workflow\_event\_trigger        | Event that triggered the workflow run (e.g., push, pull\_request)                       | String / pull\_request           |
| issuer\_name                    | Username of the person who triggered the workflow                                       | String / dklawren                |
| workflow\_id                    | Workflow ID in the repository                                                           | Integer / 69080091               |
| created\_at                     | Creation date of the build                                                              | Date / 2025-05-19T14:13:13Z      |
| updated\_at                     | Last updated date of the build                                                          | Date / 2025-05-19T14:29:12Z      |
| build\_duration                 | Duration of the build in seconds                                                        | Float / 959.0                    |
| total\_builds                   | Total number of builds in the file                                                      | Integer / 1                      |
| gh\_files\_added                | Number of files added by the commits                                                    | Integer / 0                      |
| gh\_files\_deleted              | Number of files deleted by the commits                                                  | Integer / 0                      |
| gh\_files\_modified             | Number of files modified by the commits                                                 | Integer / 1                      |
| tests\_ran                      | Whether tests were executed (based on job/step names)                                   | Boolean / True                   |
| gh\_lines\_added                | Lines of production code added by the commits                                           | Integer / 107                    |
| gh\_lines\_deleted              | Lines of production code deleted by the commits                                         | Integer / 18                     |
| file\_types                     | List of file extensions used in the build                                               | List / \[".pl"]                  |
| gh\_tests\_added                | Lines of test code added by the commits                                                 | Integer / 0                      |
| gh\_tests\_deleted              | Lines of test code deleted by the commits                                               | Integer / 0                      |
| gh\_test\_churn                 | Total number of test lines changed                                                      | Integer / 0                      |
| gh\_src\_churn                  | Total number of source code lines changed                                               | Integer / 125                    |
| gh\_pull\_req\_number           | Pull request number if applicable                                                       | Integer / 0                      |
| gh\_is\_pr                      | Indicates if the build is associated with a pull request                                | Boolean / False                  |
| gh\_sloc                        | Source lines of code in the repository                                                  | Integer / 230963                 |
| gh\_description\_complexity     | Word count of the PR title and description                                              | Integer / 0                      |
| gh\_src\_files                  | Number of source code files in the commits                                              | Integer / 1                      |
| gh\_doc\_files                  | Number of documentation files in the commits                                            | Integer / 0                      |
| gh\_other\_files                | Number of other files in the commits                                                    | Integer / 0                      |
| git\_num\_committers            | Total number of unique committers since the start of the project                        | Integer / 281                    |
| git\_commits                    | Total number of commits in the repository up until the run date                         | Integer / 13480                  |
| gh\_job\_id                     | List of job IDs in the workflow                                                         | List / \[42484452320, ...]       |
| total\_jobs                     | Total number of jobs in the workflow run                                                | Integer / 7                      |
| job\_details                    | JSON structure containing job and step details, including start/end times and durations | JSON / \[ { "job\_name": ... } ] |
| gh\_first\_commit\_created\_at  | Timestamp of the first commit in the workflow run                                       | Date / 2025-05-19T14:12:09Z      |
| gh\_team\_size\_last\_3\_month  | Number of unique committers in the last 3 months                                        | Integer / 7                      |
| gh\_commits\_on\_files\_touched | Number of unique modifications to files in the build within the last 3 months           | Integer / 8                      |
| gh\_num\_pr\_comments           | Number of comments on the associated PR if applicable                                   | Integer / 0                      |
| git\_merged\_with               | SHA of the commit that merged the pull request                                          | String / 43860b4f4...            |
| gh\_test\_lines\_per\_kloc      | Test density: lines of test code per 1,000 SLOC                                         | Float / 72.63                    |
| build\_language                 | Build tool/language detected (e.g., maven, gradle, npm)                                 | String / -                       |
| dependencies\_count             | Number of dependencies detected                                                         | Integer / 0                      |
| workflow\_size                  | Number of lines in the workflow file                                                    | Integer / 82                     |
| test\_framework                 | Test frameworks detected in the build (e.g., junit, pytest)                             | List / \[]                       |
| tests\_passed                   | Number of tests that passed                                                             | Integer / 0                      |
| tests\_failed                   | Number of tests that failed                                                             | Integer / 0                      |
| tests\_skipped                  | Number of tests that were skipped                                                       | Integer / 0                      |
| tests\_total                    | Total number of tests in the workflow run                                               | Integer / 0                      |
| workflow\_name                  | Name of the workflow run                                                                | String / BMO Test Suite          |
| dockerfile\_changed             | Whether a Dockerfile was modified in the run                                            | Boolean / False                  |
| docker\_compose\_changed        | Whether a docker-compose file was modified in the run                                   | Boolean / False                  |
| fetch\_duration                 | Time taken to fetch data for the current build                                          | Float / 4.75                     |




## Getting Started:
To get a local copy of GHAminer up and running, follow these steps.

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
git clone https://github.com/stilab-ets/GHAminer.git
```

2. Navigate to the project directory:
```bash
cd GHAminer
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

`-fd` : Start date for the date range of builds to retrieve.

`-td` : End date for the date range of builds to retrieve.



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
python GHAMetrics.py -t <Your_GitHub_Token> -p /path/to/repositories.csv -fd 2023-01-01 -td 2023-12-31
```
To analyze a single repository:
```bash
python GHAMetrics.py -t <Your_GitHub_Token> -s <GitHub_Repository_URL> -fd 2023-01-01 -td 2023-12-31
```


For detailed usage, please refer to this video:

[![Video Title](https://img.youtube.com/vi/4ZC71ootygA/0.jpg)](https://www.youtube.com/watch?v=4ZC71ootygA)


## Output:
GHAminer generates a CSV file, where each row contains metrics for a unique build. Please refer to `example_output.csv` for an example of build metrics collected for one repository.


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



