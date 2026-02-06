import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


print("Loading dataset...")

data = pd.read_csv("train.csv")

print("\nFirst 5 rows:")
print(data.head())

print("\nColumn names:")
print(data.columns)

print("\nDataset shape:", data.shape)

# STEP 3.2: Separate input and output
X = data.drop("FloodProbability", axis=1)
y = data["FloodProbability"]

print("\nInput features shape:", X.shape)
print("Target shape:", y.shape)

# STEP 3.3: Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("\nTraining feature shape:", X_train.shape)
print("Testing feature shape:", X_test.shape)
print("Training target shape:", y_train.shape)
print("Testing target shape:", y_test.shape)
print("\nDataset shape:", data.shape)


# STEP 3.4: Feature Scaling
scaler = StandardScaler()

# Fit only on training data
X_train_scaled = scaler.fit_transform(X_train)

# Transform test data using same scaler
X_test_scaled = scaler.transform(X_test)

print("\nAfter scaling:")
print("Scaled training features shape:", X_train_scaled.shape)
print("Scaled testing features shape:", X_test_scaled.shape)


# STEP 4: Model Training - Linear Regression
model = LinearRegression()

# Train model
model.fit(X_train_scaled, y_train)

print("\nModel training completed!")
# Predictions
y_pred = model.predict(X_test_scaled)

# Evaluation
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\nModel Evaluation:")
print("Mean Squared Error (MSE):", mse)
print("R2 Score:", r2)
joblib.dump(model, 'flood_model.pkl')
joblib.dump(scaler, 'scaler.pkl')