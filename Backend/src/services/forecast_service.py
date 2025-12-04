import pandas as pd
import numpy as np
from src.logging.logger import logger
from datetime import timedelta
import tensorflow.keras as keras
import joblib 

def aggregate_hourly_to_daily(raw_iot_df):
    """
    Chuyển đổi dữ liệu IoT thô (theo giờ/phút) thành dữ liệu tổng hợp theo ngày.
    """
    if raw_iot_df.empty:
        return pd.DataFrame()
        
    if not isinstance(raw_iot_df.index, pd.DatetimeIndex):
        raw_iot_df['timestamp'] = pd.to_datetime(raw_iot_df['timestamp'])
        raw_iot_df.set_index('timestamp', inplace=True)
    
    daily_data = raw_iot_df.resample('D').agg({
        'temperature': 'mean', 'humidity': 'mean', 'soil_moisture': 'mean',
        'soil_ph': 'mean', 'lux': 'mean', 'wind': 'mean',
        'wind_avg': 'mean', 'water_level': 'mean',
    }).dropna()

    daily_data['temperature'] = daily_data['temperature'].round(1)
    daily_data['humidity'] = daily_data['humidity'].round(1)
    daily_data['soil_moisture'] = daily_data['soil_moisture'].round(1)
    daily_data['soil_ph'] = daily_data['soil_ph'].round(1)
    daily_data['lux'] = daily_data['lux'].round(1)
    daily_data['wind'] = daily_data['wind'].round(0).astype(int) 
    daily_data['wind_avg'] = daily_data['wind_avg'].round(2)
    daily_data['water_level'] = daily_data['water_level'].round(1)
    
    COLUMNS = ["temperature", "humidity", "soil_moisture", "soil_ph", "lux", "wind", "wind_avg", "water_level"]
    daily_data = daily_data[COLUMNS]
    return daily_data

class ForecastService:
    def __init__(self):
        self.N_STEPS = 7
        self.N_FEATURES = 8
        self.COLUMNS = ["temperature", "humidity", "soil_moisture", "soil_ph", "lux", "wind", "wind_avg", "water_level"]
        
        try:
            MODEL_PATH = r"D:\finalproject\KLTN\Backend\Research\weather_prediction.h5"
            SCALER_PATH = r"D:\finalproject\KLTN\Backend\Research\scaler_weather.pkl"

            self.model = keras.models.load_model(MODEL_PATH, compile=False, custom_objects=None)
            self.scaler = joblib.load(SCALER_PATH)
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình hoặc scaler: {e}")
            self.model = None
            self.scaler = None

    def get_forecast(self, raw_iot_df, n_forecast_days=3):
        """
        Thực hiện toàn bộ quy trình: Aggregation -> Scaling -> Prediction (Recursive)
        """
        if self.model is None or self.scaler is None:
            return pd.DataFrame() 

        latest_daily_df = aggregate_hourly_to_daily(raw_iot_df)
        
        N_HAVE = len(latest_daily_df)
        
        if N_HAVE < self.N_STEPS:
            # Nếu thiếu, KHÔNG THỂ BÙ TRỪ TRONG LỚP NÀY VÌ THIẾU IoTService
            # Chúng ta sẽ sửa lại logic này trong user_routes để xử lý việc bù trừ
            logger.warning(f"Chỉ có {N_HAVE} ngày dữ liệu Daily. Cần {self.N_STEPS} ngày.")
            return pd.DataFrame() 
        
        data_for_forecast_combined = latest_daily_df.tail(self.N_STEPS)

        scaled_input = self.scaler.transform(data_for_forecast_combined)
        forecast_input = scaled_input.reshape(1, self.N_STEPS, self.N_FEATURES)
        
        forecast_results_scaled = []
        current_input = forecast_input

        for i in range(n_forecast_days):
            one_step_forecast_scaled = self.model.predict(current_input, verbose=0)
            forecast_results_scaled.append(one_step_forecast_scaled[0])
             
            new_input = np.roll(current_input[0], -1, axis=0) 
            new_input[-1] = one_step_forecast_scaled[0]
            current_input = new_input.reshape(1, self.N_STEPS, self.N_FEATURES)

        forecast_results_real = self.scaler.inverse_transform(np.array(forecast_results_scaled))
        
        forecast_dates = pd.date_range(
            start=latest_daily_df.index.max() + timedelta(days=1), 
            periods=n_forecast_days
        )
        
        df_forecast = pd.DataFrame(
            forecast_results_real, 
            index=forecast_dates, 
            columns=self.COLUMNS
        ).round(1)
        
        return df_forecast