import pandas as pd
from openai import OpenAI

from src.utils.config import CONFIG
from src.logging.logger import logger 

class BaseAgent:
    """
    Lớp agent cơ sở chứa các phương thức và thuộc tính chung
    mà các agent chuyên biệt khác sẽ kế thừa.
    """
    def __init__(self, weather_service, user_repo, analysis_repo, vector_store):
        if not vector_store or not weather_service or not user_repo or not analysis_repo:
            error_msg = f"{self.__class__.__name__} yêu cầu đầy đủ các services."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.vector_store = vector_store
        self.weather_service = weather_service
        self.user_repo = user_repo
        self.analysis_repo = analysis_repo

        self.api_key = CONFIG.OPENAI_API_KEY
        self.model_name = CONFIG.OPENAI_MODEL_NAME
        self.generation_config = CONFIG.OPENAI_GENERATION_CONFIG
        
        if not self.api_key:
            logger.warning(f"{self.__class__.__name__}: Không tìm thấy OPENAI_API_KEY. Client sẽ không được khởi tạo.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"{self.__class__.__name__} đã khởi tạo OpenAI client thành công!")
            except Exception as e:
                logger.error(f"{self.__class__.__name__}: Lỗi khi khởi tạo OpenAI client: {e}")
                self.client = None

    def _get_user_and_farm(self, farmer_id: str):
        """Lấy thông tin user và farm từ repository."""
        user = self.user_repo.get_user_with_farm(farmer_id)
        if not user or not user.farms.first():
            return None, None
        return user, user.farms.first()

    def _summarize_daily_forecast(self, hourly_data: list):
        """Tóm tắt dữ liệu thời tiết hàng giờ thành báo cáo hàng ngày."""
        if not hourly_data: return []
        df = pd.DataFrame(hourly_data)
        df['date'] = pd.to_datetime(df['date'])
        
        daily_summary = df.groupby(df['date'].dt.date).agg(
            min_temp=('temperature', 'min'),
            max_temp=('temperature', 'max'),
            avg_humidity=('humidity', lambda h: round(h.mean())),
            max_rain_chance=('rain_chance', 'max'),
            max_wind_kmh=('wind_kmh', 'max')
        ).reset_index()
        daily_summary['date'] = daily_summary['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
        
        return daily_summary.to_dict('records')