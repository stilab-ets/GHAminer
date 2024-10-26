# Code Package: Predicting Build Durations Using GitHub Data

## Overview

This project involves gathering build-related data from GitHub repositories and using machine learning models (K-Nearest Neighbors and RandamFforest, GBM and NN3) to predict build durations based on extracted features. The process is divided into three main steps:

1. **Data Gathering**: Using the GitHub API to extract build-related data from a list of GitHub projects.
2. **Data Preprocessing and Feature Engineering**: Preparing the build features data for model training.
3. **Model Training and Evaluation**: Applying machine learning algorithms to predict build durations.

## Files

- **`build_data_gathering.py`**  
  This Python script uses the GitHub API to gather build-related data from a list of GitHub projects. The gathered data is then saved in the `data_builds_features.csv` file.  
  The script relies on a predefined list of GitHub project URLs stored in `github_projects.csv`.

- **`Random_forest.py`**  
  Implements a Random_forest Classification model to predict build durations using the features from `data_builds_features.csv`.  
  Includes data preprocessing steps like feature scaling and model evaluation metrics.

 **`NN3.py`**  
  Implements a NN3 Classification model to predict build durations using the features from `data_builds_features.csv`.  
  Includes data preprocessing steps like feature scaling and model evaluation metrics.
 **`knn.py`**  

  Implements a K-Nearest Neighbors (KNN) Classification model to predict build durations using the features from `data_builds_features.csv`.  
  Includes data preprocessing steps like feature scaling and model evaluation metrics.

- **`GBM.py`**  
  Implements an GBM Classification model to predict build durations using the features from `data_builds_features.csv`.  
  Similar to `knn_test.py`, this script also includes data preprocessing and model evaluation metrics.

- **`data_builds_features.csv`**  
  A CSV file that contains the extracted build-related data (including build durations). This data is used to train and evaluate the machine learning models.

- **`github_projects.csv`**  
  A CSV file containing a list of 17,020 GitHub project URLs. These URLs are used by `build_data_gathering.py` to extract build-related information from GitHub repositories.

- **`log.txt`**  
  Contains terminal output from runs of `Random_forest.py`,NN3.py, `knn.py` and `GBM.py`. Useful for debugging and tracking the performance of each model.

## Usage

### 1. Data Gathering

Run `build_data_gathering.py` to fetch the build data from GitHub projects. Ensure you have a valid GitHub API token.

python build_data_gathering.py

The gathered data will be saved to data_builds_features.csv.


### 4. Logs
Check log.txt for previous example output logs from the model runs.

### Dependencies

pip install requests pydriller pandas 

Notes
Ensure you have a valid GitHub API token when running build_data_gathering.py to avoid rate limit issues.
