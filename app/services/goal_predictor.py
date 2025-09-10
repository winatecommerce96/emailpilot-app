"""
Goal Predictor Service - Predicts future goals based on historical performance
Supports multiple prediction models and confidence scoring
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics
import math

logger = logging.getLogger(__name__)

class GoalPredictor:
    """
    Predicts future goals based on historical data
    Supports multiple metrics and prediction models
    """
    
    def __init__(self):
        # Seasonal adjustment factors by month (1.0 = average)
        self.seasonal_factors = {
            1: 0.85,   # January - Post-holiday slowdown
            2: 0.90,   # February - Still recovering
            3: 0.95,   # March - Spring pickup
            4: 1.00,   # April - Average
            5: 1.05,   # May - Spring strong
            6: 0.95,   # June - Summer start
            7: 0.90,   # July - Summer slowdown
            8: 0.85,   # August - Summer low
            9: 1.00,   # September - Back to school
            10: 1.10,  # October - Pre-holiday
            11: 1.35,  # November - Black Friday/Cyber Monday
            12: 1.20   # December - Holiday season
        }
    
    def predict_from_history(
        self, 
        historical_data: List[Dict[str, Any]], 
        metric_type: str,
        target_year: int,
        target_month: Optional[int] = None,
        model: str = "yoy_growth"
    ) -> Dict[str, Any]:
        """
        Predict future goals based on historical data
        
        Args:
            historical_data: List of historical data points with 'month', 'year', 'value'
            metric_type: Type of metric (revenue, open_rate, etc.)
            target_year: Year to predict for
            target_month: Specific month or None for all months
            model: Prediction model to use
        
        Returns:
            Prediction with confidence score
        """
        try:
            if not historical_data:
                return {
                    "error": "No historical data available",
                    "predictions": []
                }
            
            # Choose prediction model
            if model == "yoy_growth":
                predictions = self._predict_yoy_growth(
                    historical_data, metric_type, target_year, target_month
                )
            elif model == "seasonal":
                predictions = self._predict_seasonal(
                    historical_data, metric_type, target_year, target_month
                )
            elif model == "moving_average":
                predictions = self._predict_moving_average(
                    historical_data, metric_type, target_year, target_month
                )
            elif model == "trend_analysis":
                predictions = self._predict_trend_analysis(
                    historical_data, metric_type, target_year, target_month
                )
            else:
                # Default to YoY growth
                predictions = self._predict_yoy_growth(
                    historical_data, metric_type, target_year, target_month
                )
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error in predict_from_history: {e}")
            return {
                "error": str(e),
                "predictions": []
            }
    
    def _predict_yoy_growth(
        self, 
        historical_data: List[Dict[str, Any]], 
        metric_type: str,
        target_year: int,
        target_month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Year-over-Year growth prediction model
        """
        try:
            # Calculate YoY growth rate
            growth_rate = self._calculate_yoy_growth_rate(historical_data)
            
            # Get prior year data
            prior_year = target_year - 1
            prior_year_data = [
                d for d in historical_data 
                if d.get('year') == prior_year
            ]
            
            predictions = []
            
            if target_month:
                # Predict single month
                prior_month_data = next(
                    (d for d in prior_year_data if d.get('month') == target_month),
                    None
                )
                
                if prior_month_data:
                    predicted_value = prior_month_data['value'] * (1 + growth_rate)
                    
                    # Apply seasonal adjustment for certain metrics
                    if metric_type in ['revenue', 'conversions']:
                        predicted_value *= self.seasonal_factors.get(target_month, 1.0)
                    
                    confidence = self._calculate_confidence(historical_data, metric_type)
                    
                    predictions.append({
                        'year': target_year,
                        'month': target_month,
                        'predicted_value': round(predicted_value, 2),
                        'historical_basis': prior_month_data['value'],
                        'growth_rate': growth_rate,
                        'confidence': confidence,
                        'confidence_score': self._get_confidence_score(confidence)
                    })
            else:
                # Predict all months
                for month in range(1, 13):
                    prior_month_data = next(
                        (d for d in prior_year_data if d.get('month') == month),
                        None
                    )
                    
                    if prior_month_data:
                        predicted_value = prior_month_data['value'] * (1 + growth_rate)
                        
                        # Apply seasonal adjustment
                        if metric_type in ['revenue', 'conversions']:
                            predicted_value *= self.seasonal_factors.get(month, 1.0)
                        
                        confidence = self._calculate_confidence(historical_data, metric_type)
                        
                        predictions.append({
                            'year': target_year,
                            'month': month,
                            'predicted_value': round(predicted_value, 2),
                            'historical_basis': prior_month_data['value'],
                            'growth_rate': growth_rate,
                            'confidence': confidence,
                            'confidence_score': self._get_confidence_score(confidence)
                        })
            
            return {
                'model': 'yoy_growth',
                'predictions': predictions,
                'overall_growth_rate': growth_rate,
                'metric_type': metric_type
            }
            
        except Exception as e:
            logger.error(f"Error in YoY growth prediction: {e}")
            return {'error': str(e), 'predictions': []}
    
    def _predict_seasonal(
        self, 
        historical_data: List[Dict[str, Any]], 
        metric_type: str,
        target_year: int,
        target_month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Seasonal adjustment prediction model
        """
        try:
            # Calculate monthly averages across all years
            monthly_averages = {}
            for month in range(1, 13):
                month_values = [
                    d['value'] for d in historical_data 
                    if d.get('month') == month
                ]
                if month_values:
                    monthly_averages[month] = statistics.mean(month_values)
            
            # Calculate overall trend
            yearly_totals = {}
            for d in historical_data:
                year = d.get('year')
                if year:
                    yearly_totals[year] = yearly_totals.get(year, 0) + d['value']
            
            # Calculate growth trend
            years = sorted(yearly_totals.keys())
            if len(years) > 1:
                growth_rate = (yearly_totals[years[-1]] - yearly_totals[years[0]]) / yearly_totals[years[0]] / len(years)
            else:
                growth_rate = 0.05  # Default 5% growth
            
            predictions = []
            months_to_predict = [target_month] if target_month else range(1, 13)
            
            for month in months_to_predict:
                if month in monthly_averages:
                    # Apply growth and seasonal factors
                    base_value = monthly_averages[month]
                    years_ahead = target_year - max(years) if years else 1
                    predicted_value = base_value * (1 + growth_rate * years_ahead)
                    predicted_value *= self.seasonal_factors.get(month, 1.0)
                    
                    confidence = self._calculate_confidence(historical_data, metric_type)
                    
                    predictions.append({
                        'year': target_year,
                        'month': month,
                        'predicted_value': round(predicted_value, 2),
                        'seasonal_factor': self.seasonal_factors.get(month, 1.0),
                        'confidence': confidence,
                        'confidence_score': self._get_confidence_score(confidence)
                    })
            
            return {
                'model': 'seasonal',
                'predictions': predictions,
                'metric_type': metric_type
            }
            
        except Exception as e:
            logger.error(f"Error in seasonal prediction: {e}")
            return {'error': str(e), 'predictions': []}
    
    def _predict_moving_average(
        self, 
        historical_data: List[Dict[str, Any]], 
        metric_type: str,
        target_year: int,
        target_month: Optional[int] = None,
        window: int = 3
    ) -> Dict[str, Any]:
        """
        Moving average prediction model
        """
        try:
            # Sort data chronologically
            sorted_data = sorted(
                historical_data, 
                key=lambda x: (x.get('year', 0), x.get('month', 0))
            )
            
            # Calculate moving averages
            predictions = []
            months_to_predict = [target_month] if target_month else range(1, 13)
            
            for month in months_to_predict:
                # Get last 'window' values for this month
                month_values = [
                    d['value'] for d in sorted_data 
                    if d.get('month') == month
                ][-window:]
                
                if month_values:
                    # Calculate moving average
                    predicted_value = statistics.mean(month_values)
                    
                    # Apply slight growth factor
                    growth_factor = 1.02  # 2% growth
                    predicted_value *= growth_factor
                    
                    confidence = self._calculate_confidence(historical_data, metric_type)
                    
                    predictions.append({
                        'year': target_year,
                        'month': month,
                        'predicted_value': round(predicted_value, 2),
                        'window_size': len(month_values),
                        'confidence': confidence,
                        'confidence_score': self._get_confidence_score(confidence)
                    })
            
            return {
                'model': 'moving_average',
                'predictions': predictions,
                'window': window,
                'metric_type': metric_type
            }
            
        except Exception as e:
            logger.error(f"Error in moving average prediction: {e}")
            return {'error': str(e), 'predictions': []}
    
    def _predict_trend_analysis(
        self, 
        historical_data: List[Dict[str, Any]], 
        metric_type: str,
        target_year: int,
        target_month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Trend analysis with linear regression
        """
        try:
            # Prepare data for linear regression
            data_points = []
            for d in historical_data:
                year = d.get('year', 0)
                month = d.get('month', 0)
                if year and month:
                    # Convert to months since start
                    months_since_start = (year - min(d.get('year', 0) for d in historical_data)) * 12 + month
                    data_points.append((months_since_start, d['value']))
            
            if len(data_points) < 2:
                return {'error': 'Insufficient data for trend analysis', 'predictions': []}
            
            # Calculate linear regression
            n = len(data_points)
            sum_x = sum(x for x, _ in data_points)
            sum_y = sum(y for _, y in data_points)
            sum_xx = sum(x * x for x, _ in data_points)
            sum_xy = sum(x * y for x, y in data_points)
            
            # Calculate slope and intercept
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
            
            # Make predictions
            predictions = []
            min_year = min(d.get('year', 0) for d in historical_data)
            months_to_predict = [target_month] if target_month else range(1, 13)
            
            for month in months_to_predict:
                months_since_start = (target_year - min_year) * 12 + month
                predicted_value = slope * months_since_start + intercept
                
                # Apply bounds checking for percentage metrics
                if metric_type in ['open_rate', 'click_rate', 'bounce_rate']:
                    predicted_value = max(0, min(100, predicted_value))
                
                confidence = self._calculate_confidence(historical_data, metric_type)
                
                predictions.append({
                    'year': target_year,
                    'month': month,
                    'predicted_value': round(predicted_value, 2),
                    'trend_slope': slope,
                    'confidence': confidence,
                    'confidence_score': self._get_confidence_score(confidence)
                })
            
            return {
                'model': 'trend_analysis',
                'predictions': predictions,
                'trend_direction': 'increasing' if slope > 0 else 'decreasing',
                'metric_type': metric_type
            }
            
        except Exception as e:
            logger.error(f"Error in trend analysis prediction: {e}")
            return {'error': str(e), 'predictions': []}
    
    def _calculate_yoy_growth_rate(self, historical_data: List[Dict[str, Any]]) -> float:
        """
        Calculate year-over-year growth rate from historical data
        """
        try:
            # Group data by year
            yearly_totals = {}
            for d in historical_data:
                year = d.get('year')
                if year:
                    yearly_totals[year] = yearly_totals.get(year, 0) + d.get('value', 0)
            
            if len(yearly_totals) < 2:
                return 0.05  # Default 5% growth if insufficient data
            
            # Calculate growth rates between consecutive years
            years = sorted(yearly_totals.keys())
            growth_rates = []
            
            for i in range(1, len(years)):
                if yearly_totals[years[i-1]] > 0:
                    rate = (yearly_totals[years[i]] - yearly_totals[years[i-1]]) / yearly_totals[years[i-1]]
                    growth_rates.append(rate)
            
            # Return average growth rate
            if growth_rates:
                return statistics.mean(growth_rates)
            else:
                return 0.05  # Default 5% growth
                
        except Exception as e:
            logger.error(f"Error calculating YoY growth rate: {e}")
            return 0.05
    
    def _calculate_confidence(
        self, 
        historical_data: List[Dict[str, Any]], 
        metric_type: str
    ) -> str:
        """
        Calculate confidence level based on data consistency and variance
        """
        try:
            if len(historical_data) < 6:
                return "low"
            
            # Calculate coefficient of variation
            values = [d.get('value', 0) for d in historical_data]
            if not values:
                return "low"
            
            mean_val = statistics.mean(values)
            if mean_val == 0:
                return "low"
            
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            cv = std_dev / mean_val
            
            # Determine confidence based on variation
            if cv < 0.15:
                return "high"
            elif cv < 0.30:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return "low"
    
    def _get_confidence_score(self, confidence: str) -> float:
        """
        Convert confidence level to numeric score
        """
        confidence_scores = {
            "high": 0.85,
            "medium": 0.65,
            "low": 0.45
        }
        return confidence_scores.get(confidence, 0.5)
    
    def calculate_goal_from_prediction(
        self, 
        prediction: Dict[str, Any], 
        adjustment_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Convert a prediction into a goal with optional adjustment
        
        Args:
            prediction: Prediction data
            adjustment_factor: Manual adjustment factor (1.0 = no change)
        
        Returns:
            Goal data ready for storage
        """
        try:
            predicted_value = prediction.get('predicted_value', 0)
            goal_value = predicted_value * adjustment_factor
            
            return {
                'goal_value': round(goal_value, 2),
                'predicted_value': predicted_value,
                'adjustment_factor': adjustment_factor,
                'calculation_method': 'ai_suggested',
                'confidence': prediction.get('confidence', 'medium'),
                'confidence_score': prediction.get('confidence_score', 0.65),
                'historical_basis': prediction.get('historical_basis'),
                'growth_rate': prediction.get('growth_rate'),
                'model_used': prediction.get('model', 'yoy_growth')
            }
            
        except Exception as e:
            logger.error(f"Error calculating goal from prediction: {e}")
            return {
                'goal_value': 0,
                'error': str(e)
            }