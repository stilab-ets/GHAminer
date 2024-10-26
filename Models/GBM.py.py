import pandas as pd
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer, StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.feature_selection import RFECV
import numpy as np

# Load data
data = pd.read_csv('data_builds_features.csv')
# Filter to use only the specified repository
data = data[data['repo'] == 'OP-TED/eforms-notice-viewer']
# Data preprocessing
data['is_master'] = data['branch'].isin(['master', 'axis']).astype(int)
data['gh_is_pr'] = data['gh_is_pr'].astype(int)

def safe_convert(value):
    try:
        return int(value)
    except ValueError:
        return None  # Return None if the conversion fails



# Apply conversion and handle missing values
data['git_merged_with'] = data['git_merged_with'].apply(safe_convert)
data['git_merged_with'] = data['git_merged_with'].fillna(0).astype(int).infer_objects()

data['tests_ran'] = data['tests_ran'].astype(int)
data['status'] = (data['status'] == 'completed').astype(int)
data['languages'] = (data['languages'] == 'C++, Rust, Python, Swift, Java, C#, JavaScript, Kotlin, Dart, TypeScript, PHP, Go, Nim, Lua, CMake, Starlark, Shell, Batchfile, C, Ruby, Roff, Makefile').astype(int)

def categorize_file_type(file_type_list):
    categories = {
        'Image': ['.png', '.jpg', '.jpeg', '.gif'],
        'Code': ['.java', '.py', '.js', '.cpp', '.c'],
        'Document': ['.md', '.txt', '.pdf'],
        'Configuration': ['.xml', '.json', '.yaml', '.config'],
        'Data': ['.csv', '.xlsx', '.xls', '.data']
    }
    result = []
    for file_type in file_type_list.split(', ') if isinstance(file_type_list, str) else []:
        category = next((cat for cat, exts in categories.items() if file_type in exts), 'Other')
        result.append(category)
    return list(set(result))

data['file_types'] = data['file_types'].apply(categorize_file_type)
mlb = MultiLabelBinarizer()
data = pd.concat([data, pd.DataFrame(mlb.fit_transform(data['file_types']), columns=mlb.classes_, index=data.index)], axis=1)

# Remove unused columns
data.drop(columns=['file_types', 'conclusion', 'repo', 'branch', 'created_at', 'updated_at', 'gh_first_commit_created_at', 'id_build', 'commit_sha', 'gh_job_id', 'test_framework', 'build_language'], inplace=True)

# Feature engineering
data['duration_class'] = pd.qcut(data['build_duration'], 3, labels=['Fast', 'Medium', 'Slow'])

X = data.drop(['duration_class', 'build_duration'], axis=1)
y = data['duration_class']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Feature selection with RFECV using GradientBoostingClassifier
selector = RFECV(GradientBoostingClassifier(n_estimators=100, random_state=42), step=1, cv=5)
X_train_selected = selector.fit_transform(X_train_scaled, y_train)
X_test_selected = selector.transform(X_test_scaled)

# Gradient Boosting Classifier model with GridSearch
param_grid = {
    'n_estimators': [100, 200, 300],
    'learning_rate': [0.01, 0.1, 0.2],
    'max_depth': [3, 5, 7]
}
gbm = GridSearchCV(GradientBoostingClassifier(), param_grid, cv=5, scoring='accuracy')
gbm.fit(X_train_selected, y_train)
print("Best parameters:", gbm.best_params_)
print("Best cross-validation accuracy:", gbm.best_score_)

# Evaluate the model
y_pred = gbm.predict(X_test_selected)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("Precision:", precision_score(y_test, y_pred, average='weighted'))
print("Recall:", recall_score(y_test, y_pred, average='weighted'))
print("F1 Score:", f1_score(y_test, y_pred, average='weighted'))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
