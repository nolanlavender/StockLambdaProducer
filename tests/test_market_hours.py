import pytest
import pytz
from datetime import datetime, time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from market_hours import MarketHours


class TestMarketHours:
    """Test cases for MarketHours class"""
    
    def setup_method(self):
        """Setup test instance"""
        self.market_hours = MarketHours()
    
    def test_market_timezone(self):
        """Test that market timezone is Eastern Time"""
        assert self.market_hours.market_timezone.zone == 'America/New_York'
    
    def test_market_hours_definition(self):
        """Test market hours are correctly defined"""
        assert self.market_hours.market_open_time == time(9, 30)
        assert self.market_hours.market_close_time == time(16, 0)
    
    def test_get_current_market_time(self):
        """Test getting current market time"""
        current_time = self.market_hours.get_current_market_time()
        assert current_time.tzinfo == self.market_hours.market_timezone
    
    def test_is_weekday(self):
        """Test weekday detection"""
        # Monday (0) to Friday (4) should be weekdays
        monday = datetime(2024, 1, 1)  # This is a Monday
        friday = datetime(2024, 1, 5)  # This is a Friday
        saturday = datetime(2024, 1, 6)  # This is a Saturday
        sunday = datetime(2024, 1, 7)  # This is a Sunday
        
        assert self.market_hours.is_weekday(monday) is True
        assert self.market_hours.is_weekday(friday) is True
        assert self.market_hours.is_weekday(saturday) is False
        assert self.market_hours.is_weekday(sunday) is False
    
    def test_is_market_holiday_2024(self):
        """Test 2024 holiday detection"""
        # Test New Year's Day 2024
        new_years = datetime(2024, 1, 1)
        assert self.market_hours.is_market_holiday(new_years) is True
        
        # Test Christmas 2024
        christmas = datetime(2024, 12, 25)
        assert self.market_hours.is_market_holiday(christmas) is True
        
        # Test regular day
        regular_day = datetime(2024, 3, 15)
        assert self.market_hours.is_market_holiday(regular_day) is False
    
    def test_is_market_holiday_2025(self):
        """Test 2025 holiday detection"""
        # Test New Year's Day 2025
        new_years = datetime(2025, 1, 1)
        assert self.market_hours.is_market_holiday(new_years) is True
        
        # Test regular day
        regular_day = datetime(2025, 6, 15)
        assert self.market_hours.is_market_holiday(regular_day) is False
    
    def test_market_open_during_hours(self):
        """Test market is open during trading hours on weekday"""
        # Tuesday, March 5, 2024 at 2:00 PM EST (during market hours)
        market_time = datetime(2024, 3, 5, 14, 0, 0)
        market_time = self.market_hours.market_timezone.localize(market_time)
        
        is_open, reason = self.market_hours.is_market_open(market_time)
        assert is_open is True
        assert "Market open" in reason
    
    def test_market_closed_before_hours(self):
        """Test market is closed before trading hours"""
        # Tuesday, March 5, 2024 at 8:00 AM EST (before market hours)
        market_time = datetime(2024, 3, 5, 8, 0, 0)
        market_time = self.market_hours.market_timezone.localize(market_time)
        
        is_open, reason = self.market_hours.is_market_open(market_time)
        assert is_open is False
        assert "Before opening hours" in reason
    
    def test_market_closed_after_hours(self):
        """Test market is closed after trading hours"""
        # Tuesday, March 5, 2024 at 5:00 PM EST (after market hours)
        market_time = datetime(2024, 3, 5, 17, 0, 0)
        market_time = self.market_hours.market_timezone.localize(market_time)
        
        is_open, reason = self.market_hours.is_market_open(market_time)
        assert is_open is False
        assert "After closing hours" in reason
    
    def test_market_closed_weekend(self):
        """Test market is closed on weekend"""
        # Saturday, March 2, 2024 at 2:00 PM EST
        weekend_time = datetime(2024, 3, 2, 14, 0, 0)
        weekend_time = self.market_hours.market_timezone.localize(weekend_time)
        
        is_open, reason = self.market_hours.is_market_open(weekend_time)
        assert is_open is False
        assert "Weekend" in reason
        assert "Saturday" in reason
    
    def test_market_closed_holiday(self):
        """Test market is closed on holiday"""
        # Christmas Day 2024 at 2:00 PM EST (would be during market hours normally)
        holiday_time = datetime(2024, 12, 25, 14, 0, 0)
        holiday_time = self.market_hours.market_timezone.localize(holiday_time)
        
        is_open, reason = self.market_hours.is_market_open(holiday_time)
        assert is_open is False
        assert "Holiday" in reason
    
    def test_market_boundary_times(self):
        """Test market status at boundary times"""
        # Tuesday, March 5, 2024 at exactly 9:30 AM EST (market open)
        open_time = datetime(2024, 3, 5, 9, 30, 0)
        open_time = self.market_hours.market_timezone.localize(open_time)
        
        is_open, reason = self.market_hours.is_market_open(open_time)
        assert is_open is True
        
        # Tuesday, March 5, 2024 at exactly 4:00 PM EST (market close)
        close_time = datetime(2024, 3, 5, 16, 0, 0)
        close_time = self.market_hours.market_timezone.localize(close_time)
        
        is_open, reason = self.market_hours.is_market_open(close_time)
        assert is_open is False
        assert "After closing hours" in reason
    
    def test_timezone_conversion(self):
        """Test that timezone conversion works correctly"""
        # Test with UTC time
        utc_time = datetime(2024, 3, 5, 19, 30, 0, tzinfo=pytz.UTC)  # 2:30 PM EST
        
        is_open, reason = self.market_hours.is_market_open(utc_time)
        assert is_open is True
        assert "Market open" in reason
    
    def test_get_next_market_open(self):
        """Test getting next market open time"""
        # Friday after market close
        friday_after_close = datetime(2024, 3, 1, 17, 0, 0)
        friday_after_close = self.market_hours.market_timezone.localize(friday_after_close)
        
        next_open = self.market_hours.get_next_market_open(friday_after_close)
        
        # Should be Monday 9:30 AM
        assert next_open.weekday() == 0  # Monday
        assert next_open.time() == time(9, 30)
        assert next_open.date().day == 4  # March 4, 2024 is a Monday
    
    def test_get_next_market_open_skip_holiday(self):
        """Test that next market open skips holidays"""
        # December 24, 2024 (day before Christmas)
        before_christmas = datetime(2024, 12, 24, 17, 0, 0)
        before_christmas = self.market_hours.market_timezone.localize(before_christmas)
        
        next_open = self.market_hours.get_next_market_open(before_christmas)
        
        # Should skip Christmas (Dec 25) and go to Dec 26
        assert next_open.date().day == 26
        assert next_open.time() == time(9, 30)
    
    def test_naive_datetime_handling(self):
        """Test handling of timezone-naive datetime"""
        # Timezone-naive datetime (assumed to be in market timezone)
        naive_time = datetime(2024, 3, 5, 14, 0, 0)
        
        is_open, reason = self.market_hours.is_market_open(naive_time)
        assert is_open is True
        assert "Market open" in reason