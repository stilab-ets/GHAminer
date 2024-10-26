# feature_selection.py

import json
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import RFECV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer



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


# Custom function to classify duration based on quantiles
def classify_duration_by_quantile(duration, quantiles):
    if duration <= quantiles[0.25]:
        return 'Fast'
    elif duration <= quantiles[0.75]:
        return 'Medium'
    else:
        return 'Slow' 
    


# Count how many unique values are present
def safe_convert(value):
    try:
        return int(value)
    except ValueError:
        return None  # or return -1, or other flag

# Assuming 'data' is already loaded and cleaned
def perform_feature_selection(data):



        # Simplify branch transformation using vectorized operations
    data['is_master'] = data['branch'].isin(['master', 'axis']).astype(int)

    # Convert 'gh_is_pr' and 'git_merged_with' to integers (handling NaNs)
    data['gh_is_pr'] = data['gh_is_pr'].astype(int)



    data['git_merged_with'] = data['git_merged_with'].apply(safe_convert)

    # Now you can fill NaN values if you used None for errors
    data['git_merged_with'] = data['git_merged_with'].fillna(0).astype(int)


    # Normalize boolean columns
    data['tests_ran'] = data['tests_ran'].astype(int)
    data['status'] = (data['status'] == 'completed').astype(int)
    data['languages'] = (data['languages'] == 'C++, Rust, Python, Swift, Java, C#, JavaScript, Kotlin, Dart, TypeScript, PHP, Go, Nim, Lua, CMake, Starlark, Shell, Batchfile, C, Ruby, Roff, Makefile').astype(int)




    data['file_types'] = data['file_types'].apply(lambda x: x if isinstance(x, list) else x.split(', ') if isinstance(x, str) else [])
    data['file_types'] = data['file_types'].apply(categorize_file_type)

    # Using MultiLabelBinarizer for the categorized data
    mlb = MultiLabelBinarizer()
    categorized_encoded = pd.DataFrame(mlb.fit_transform(data['file_types']), columns=mlb.classes_, index=data.index)
    data = pd.concat([data.drop('file_types', axis=1), categorized_encoded], axis=1)

    # Display a sample of the processed data
    print(data.head())


    
    data.drop(columns=['conclusion', 'repo', 'branch', 'created_at', 'updated_at', 'gh_first_commit_created_at','id_build','commit_sha','gh_job_id','test_framework', 'build_language'], inplace=True)
    
  
    
    # Define quantiles
    quantiles = data['build_duration'].quantile([0.25, 0.75])



    # Apply function to create a new column based on quantiles
    data['duration_class'] = data['build_duration'].apply(classify_duration_by_quantile, quantiles=quantiles)

    # Check the distribution of custom categories
    print(data['duration_class'].value_counts())
    X = data.drop(columns=['duration_class', 'build_duration'])  # Feature matrix
    y = data['duration_class']  # Target variable (classification labels)

    # Separate numerical columns
    numerical_cols = X.select_dtypes(include=['float64', 'int64']).columns
    
    # Handle missing values for numerical columns
    if len(numerical_cols) > 0:
        X[numerical_cols] = X[numerical_cols].fillna(X[numerical_cols].mean())  # Fill NaN with mean
    
    # Split the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Scaling only the numerical columns
    scaler = StandardScaler()
    X_train_scaled = X_train.copy()
    X_train_scaled[numerical_cols] = scaler.fit_transform(X_train[numerical_cols])

    # Feature selection with RFECV using RandomForestClassifier for ranking importance
    selector = RFECV(RandomForestClassifier(n_estimators=100, random_state=42), step=1, cv=5)
    X_train_selected = selector.fit_transform(X_train_scaled, y_train)

    # Get selected feature indices and names
    selected_features_indices = selector.get_support(indices=True)
    selected_features = X_train.columns[selected_features_indices].tolist()

    # Save selected features to a JSON file
    with open('selected_features.json', 'w') as f:
        json.dump(selected_features, f)

    print("Feature selection completed. Selected features saved to 'selected_features.json'.")

# Example usage:
if __name__ == "__main__":
    # Load your data here
    data = pd.read_csv('data_builds_features.csv')
    perform_feature_selection(data)
