import requests
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import unidecode
import random
from src.utils.config import CONFIG
from src.logging.logger import logger

class WeatherService:
    """
    Dịch vụ chịu trách nhiệm lấy và cache dữ liệu thời tiết.
    """
    def __init__(self):
        self.cache_path = CONFIG.WEATHER_CACHE_PATH
        self.cache_duration_hours = CONFIG.WEATHER_CACHE_DURATION_HOURS
        
        self.base_url = "https://baomoi.com/tien-ich/thoi-tiet-"
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        ]
        
        self.weather_cache = self._load_cache_from_disk()

    def _load_cache_from_disk(self):
        """Tải dữ liệu cache từ file JSON trên đĩa."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    logger.info(f"Đã tải cache thời tiết từ: {self.cache_path}")
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Lỗi đọc file cache thời tiết: {e}. Bắt đầu với cache rỗng.")
                return {}
        return {}

    def _save_cache_to_disk(self):
        """Lưu dữ liệu cache hiện tại vào file JSON."""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.weather_cache, f, ensure_ascii=False, indent=4)
        except IOError as e:
            logger.error(f"Lỗi khi lưu cache thời tiết ra file: {e}")

    def _format_province_for_url(self, province: str) -> str:
        """Chuyển đổi tên tỉnh thành định dạng cho URL."""
        no_diacritics = unidecode.unidecode(province)
        return no_diacritics.lower().replace(" ", "-")

    def _crawl_weather_data(self, province: str):
        """Cào dữ liệu thời tiết từ nguồn bên ngoài."""
        province_url_part = self._format_province_for_url(province)
        url = f"{self.base_url}{province_url_part}.epi"
        logger.info(f"CACHE MISS: Đang lấy dữ liệu thời tiết từ: {url}...")
        try:
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
            if not next_data_script:
                logger.error(f"Không tìm thấy thẻ '__NEXT_DATA__' khi crawl trang thời tiết cho {province}.")
                return None

            data = json.loads(next_data_script.string)
            forecast_entries = data.get('props', {}).get('pageProps', {}).get('resp', {}).get('data', {}).get('content', {}).get('activeBoard', {}).get('entries', [])
            if not forecast_entries:
                logger.warning(f"Dữ liệu thời tiết trả về cho {province} bị rỗng hoặc có cấu trúc không mong muốn.")
                return None

            all_hourly_forecasts = []
            for daily_entry in forecast_entries:
                current_date = datetime.strptime(daily_entry.get('date'), '%d/%m/%Y').strftime('%Y-%m-%d')
                for hourly_entry in daily_entry.get('hours', []):
                    all_hourly_forecasts.append({
                        'province': province, 'date': current_date, 'hour': hourly_entry.get('hours'),
                        'temperature': hourly_entry.get('temperature'), 'humidity': hourly_entry.get('humidity'),
                        'wind_kmh': hourly_entry.get('wind'), 'rain_chance': hourly_entry.get('pop'),
                        'description': hourly_entry.get('status')
                    })
            return all_hourly_forecasts
        except Exception as e:
            logger.error(f"Lỗi không xác định khi crawl dữ liệu thời tiết cho {province}: {e}")
            return None

    def get_forecast(self, province: str):
        """Lấy dữ liệu dự báo, ưu tiên từ cache."""
        now = datetime.now()
        
        if province in self.weather_cache:
            cache_entry = self.weather_cache.get(province, {})
            cache_time_str = cache_entry.get('cache_time')
            if cache_time_str:
                cache_time = datetime.fromisoformat(cache_time_str)
                if now - cache_time < timedelta(hours=self.cache_duration_hours):
                    logger.info(f"CACHE HIT: Sử dụng dữ liệu thời tiết đã cache cho {province}.")
                    return cache_entry.get('data')

        fresh_data = self._crawl_weather_data(province)
        
        if fresh_data:
            self.weather_cache[province] = {'cache_time': now.isoformat(), 'data': fresh_data}
            self._save_cache_to_disk()
            
            delay = random.uniform(2, 5)
            logger.info(f"Đã crawl xong, tạm dừng {delay:.2f} giây...")
            time.sleep(delay)
            
            return fresh_data
        
        logger.warning(f"Crawl dữ liệu mới cho {province} thất bại. Sử dụng dữ liệu cũ trong cache (nếu có).")
        return self.weather_cache.get(province, {}).get('data')
