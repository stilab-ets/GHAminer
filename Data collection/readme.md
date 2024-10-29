# Command Line 
This section explains how to use the script via the command line. The script supports several options that allow you to customize its behavior.

 **Prerequisites**
Before running the script, ensure you have Python installed on your system. You also need to set up a GitHub token with the appropriate permissions and store it in a secure location.

 **General Syntax**
 ```
python script_name.py [options]
```
- **Options**
-t, --token:Specify your GitHub access token. This token is used to authenticate API requests. Do not hardcode your token in the script. Instead, pass it securely via this command line argument.

-**Example:**
```
python script_name.py --token YOUR_GITHUB_TOKEN
```
-p, --projects: Path to a CSV file that contains a list of GitHub project URLs. The script processes each project listed in the file.

- **Example:**
```
python script_name.py --projects path/to/your/projects.csv
```
-fd, --from_date: The start date from which the script will begin collecting data. The date should be in the format YYYY-MM-DD.

- **Example:**
```
python script_name.py --from_date 2024-01-01
```
-td, --to_date: The end date until which the script will collect data. The date should be in the format YYYY-MM-DD.

- **Example:**
```
python script_name.py --to_date 2024-10-10
```
Example of Full Command
Here's how you might run the script with all the options provided:

```
python script_name.py --token YOUR_GITHUB_TOKEN --projects path/to/projects.csv --from_date 20224-01-01 --to_date 2024-10-10
```
### Notes
* It's important to replace YOUR_GITHUB_TOKEN with your actual GitHub token.
  
* Adjust the paths to the project CSV file and dates according to your requirements.
  
* Ensure you have the necessary Python packages installed (e.g., requests, pydriller).
