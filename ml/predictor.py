import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

class DragErrorPredictor:
    def __init__(self):
        self.model = GradientBoostingRegressor(n_estimators=50, random_state=42)
        self.is_trained = False
        self._train_dummy()
        
    def _train_dummy(self):
        np.random.seed(42)
        X_train = np.random.rand(200, 5)
        X_train[:, 0] = X_train[:, 0] * 1000.0 + 200.0
        X_train[:, 1] = X_train[:, 1] * 150.0 + 70.0
        X_train[:, 2] = X_train[:, 2] * 8.0 + 1.0
        X_train[:, 3] = X_train[:, 3] * 0.001
        X_train[:, 4] = X_train[:, 4] * 10.0
        
        y_train = (X_train[:, 2] * 50.0) + (X_train[:, 1] * 2.0) + (X_train[:, 4] * 100.0) * (1500.0 / X_train[:, 0]) + np.random.normal(0, 10, 200)
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
    def predict_error(self, altitude_km, f107, kp, b_star, tle_age_days):
        if not self.is_trained:
            return 50.0
        X = np.array([[altitude_km, f107, kp, b_star, tle_age_days]])
        pred = self.model.predict(X)[0]
        return float(max(1.0, pred))
