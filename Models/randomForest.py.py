import pandas as pd
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Load the data
data = pd.read_csv('data_builds_features.csv')
data = data[data['repo'] == 'bioimage-io/spec-bioimage-io']
# Simplify branch transformation using vectorized operations
data['is_master'] = data['branch'].isin(['master', 'axis']).astype(int)

# Convert 'gh_is_pr' and 'git_merged_with' to integers (handling NaNs)
data['gh_is_pr'] = data['gh_is_pr'].astype(int)


# Count how many unique values are present
def safe_convert(value):
    try:
        return int(value)
    except ValueError:
        return None  # or return -1, or other flag


data['git_merged_with'] = data['git_merged_with'].apply(safe_convert)

# Now you can fill NaN values if you used None for errors
data['git_merged_with'] = data['git_merged_with'].fillna(0).astype(int)

# Normalize boolean columns
data['tests_ran'] = data['tests_ran'].astype(int)
data['status'] = (data['status'] == 'completed').astype(int)
data['languages'] = (data[
                         'languages'] == 'C++, Rust, Python, Swift, Java, C#, JavaScript, Kotlin, Dart, TypeScript, PHP, Go, Nim, Lua, CMake, Starlark, Shell, Batchfile, C, Ruby, Roff, Makefile').astype(
    int)


# Categorize file types
def categorize_file_type(file_type_list):
    categories = {
        'Image': ['.png', '.jpg', '.jpeg', '.gif'],
        'Code': ['.java', '.py', '.js', '.cpp', '.c'],
        'Document': ['.md', '.txt', '.pdf'],
        'Configuration': ['.xml', '.json', '.yaml', '.config'],
        'Data': ['.csv', '.xlsx', '.xls', '.data']
    }
    categorized = []
    if isinstance(file_type_list, str):
        file_type_list = file_type_list.split(', ')
    elif file_type_list is None:
        return []
    for file_type in file_type_list:
        added = False
        for category, extensions in categories.items():
            if file_type in extensions:
                categorized.append(category)
                added = True
                break
        if not added:
            categorized.append('Other')
    return list(set(categorized))


data['file_types'] = data['file_types'].apply(
    lambda x: x if isinstance(x, list) else x.split(', ') if isinstance(x, str) else [])
data['file_types'] = data['file_types'].apply(categorize_file_type)

# Using MultiLabelBinarizer for the categorized data
mlb = MultiLabelBinarizer()
categorized_encoded = pd.DataFrame(mlb.fit_transform(data['file_types']), columns=mlb.classes_, index=data.index)
data = pd.concat([data.drop('file_types', axis=1), categorized_encoded], axis=1)

# Display a sample of the processed data
print(data.head())

# Filtering projects with more than 30 'conclusion_failure'
if 'conclusion_failure' in data.columns:
    filtered_data = data.groupby('repo').filter(lambda x: x['conclusion_failure'].sum() > 30)

data.drop(columns=['conclusion', 'repo', 'branch', 'created_at', 'updated_at', 'gh_first_commit_created_at', 'id_build',
                   'commit_sha', 'gh_job_id', 'test_framework', 'build_language'], inplace=True)

# Define quantiles
quantiles = data['build_duration'].quantile([0.25, 0.75])


# Custom function to classify duration based on quantiles
def classify_duration_by_quantile(duration, quantiles):
    if duration <= quantiles[0.25]:
        return 'Fast'
    elif duration <= quantiles[0.75]:
        return 'Medium'
    else:
        return 'Slow'


# Apply function to create a new column based on quantiles
data['duration_class'] = data['build_duration'].apply(classify_duration_by_quantile, quantiles=quantiles)

# Check the distribution of custom categories
print(data['duration_class'].value_counts())

import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import RFECV

# Assuming 'data' is already loaded and cleaned
X = data.drop(columns=['duration_class', 'build_duration'])  # Feature matrix, removing 'duration_class' and 'build_duration'
y = data['duration_class']  # Target variable (classification labels)

# Separate numerical and categorical columns
numerical_cols = X.select_dtypes(include=['float64', 'int64']).columns
categorical_cols = X.select_dtypes(include=['object', 'category']).columns

# Handle missing values for numerical and categorical columns separately
if len(numerical_cols) > 0:
    X[numerical_cols] = X[numerical_cols].fillna(X[numerical_cols].mean())  # Fill NaN in numerical columns with mean

if len(categorical_cols) > 0:
    X[categorical_cols] = X[categorical_cols].fillna(X[categorical_cols].mode().iloc[0])  # Fill NaN in categorical columns with mode

# Fill missing values in target variable (categorical)
y.fillna(y.mode()[0], inplace=True)

# Split the dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scaling only the numerical columns
scaler = StandardScaler()
X_train_scaled = X_train.copy()
X_test_scaled = X_test.copy()
X_train_scaled[numerical_cols] = scaler.fit_transform(X_train[numerical_cols])
X_test_scaled[numerical_cols] = scaler.transform(X_test[numerical_cols])

# Feature selection with RFECV using RandomForestClassifier for ranking importance
selector = RFECV(RandomForestClassifier(n_estimators=100, random_state=42), step=1, cv=5)
X_train_selected = selector.fit_transform(X_train_scaled, y_train)
X_test_selected = selector.transform(X_test_scaled)

# Get selected feature indices and names
selected_features_indices = selector.get_support(indices=True)
selected_features = X_train.columns[selected_features_indices].tolist()

# Save selected features to a JSON file
with open('selected_features.json', 'w') as f:
    json.dump(selected_features, f)

# Initialize RandomForest model
rf = RandomForestClassifier(random_state=42)

# Define a parameter grid to search for the best parameters for the RandomForest model
param_grid = {
    'n_estimators': [100, 200, 300, 400],
    'max_features': ['auto', 'sqrt', 'log2'],
    'max_depth': [None, 10, 20, 30, 40],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}

# Grid Search to find the best hyperparameters for classification
grid_search = GridSearchCV(rf, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
grid_search.fit(X_train_selected, y_train)

# Print the best parameters and the corresponding score
print("Best parameters:", grid_search.best_params_)
print("Best cross-validation accuracy:", grid_search.best_score_)

# Save best RandomForest hyperparameters to a JSON file
with open('best_rf_params.json', 'w') as f:
    json.dump(grid_search.best_params_, f)

# Retrieve the best RandomForest model
best_rf = grid_search.best_estimator_

# Predict on the test set using the best model
y_train_pred = best_rf.predict(X_train_selected)
y_test_pred = best_rf.predict(X_test_selected)

# Calculate accuracy, precision, recall, and F1 score for both the training and testing sets
train_accuracy = accuracy_score(y_train, y_train_pred)
test_accuracy = accuracy_score(y_test, y_test_pred)
test_precision = precision_score(y_test, y_test_pred, average='weighted')
test_recall = recall_score(y_test, y_test_pred, average='weighted')
test_f1 = f1_score(y_test, y_test_pred, average='weighted')

# Print the classification results
print(f"RandomForest Accuracy on test set: {test_accuracy:.2f}")
print(f"RandomForest Precision on test set: {test_precision:.2f}")
print(f"RandomForest Recall on test set: {test_recall:.2f}")
print(f"RandomForest F1 Score on test set: {test_f1:.2f}")

# Confusion matrix to understand the misclassifications
conf_matrix = confusion_matrix(y_test, y_test_pred)
print("Confusion Matrix:\n", conf_matrix)

# Calculate cross-validation accuracy scores
cv_scores = cross_val_score(best_rf, X_train_selected, y_train, cv=5, scoring='accuracy')

# Print the mean cross-validation score
print("Mean cross-validation accuracy:", np.mean(cv_scores))
