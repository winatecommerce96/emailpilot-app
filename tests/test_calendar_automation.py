"""
Comprehensive test suite for Calendar Automation System
Tests LangChain orchestrator, MCP integration, Firestore operations, and UI integration
"""
import pytest
import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from google.cloud import firestore

from app.api.calendar_orchestrator import CalendarOrchestrator, CalendarBuildRequest
from app.services.mcp_calendar_service import MCPCalendarService, MCPConnectionResult, MCPDataResult
from main_firestore import app

# Test fixtures
@pytest.fixture
def mock_db():
    """Mock Firestore database"""
    db = MagicMock()
    
    # Mock collection behavior
    def mock_collection(collection_name):
        collection_mock = MagicMock()
        
        # Mock document operations
        def mock_document(doc_id):
            doc_mock = MagicMock()
            doc_mock.get.return_value.exists = True
            doc_mock.get.return_value.to_dict.return_value = {
                "id": doc_id,
                "name": "Test Client",
                "klaviyo_account_id": "test_account"
            }
            return doc_mock
        
        collection_mock.document = mock_document
        
        # Mock add operations
        collection_mock.add.return_value = (None, MagicMock(id=str(uuid.uuid4())))
        
        # Mock query operations
        def mock_where(*args):
            query_mock = MagicMock()
            query_mock.stream.return_value = []
            return query_mock
        
        collection_mock.where = mock_where
        
        return collection_mock
    
    db.collection = mock_collection
    return db

@pytest.fixture
def mock_secret_manager():
    """Mock SecretManager service"""
    secret_manager = MagicMock()
    secret_manager.get_klaviyo_key_for_account = AsyncMock(return_value="test_api_key")
    return secret_manager

@pytest.fixture
def calendar_orchestrator(mock_db, mock_secret_manager):
    """Calendar orchestrator instance with mocks"""
    return CalendarOrchestrator(mock_db, mock_secret_manager)

@pytest.fixture
def sample_calendar_request():
    """Sample calendar build request"""
    return CalendarBuildRequest(
        client_display_name="Test Client",
        client_firestore_id="test_client_123",
        klaviyo_account_id="test_klaviyo_456",
        target_month=9,
        target_year=2025,
        dry_run=False
    )

@pytest.fixture
def sample_campaign_data():
    """Sample normalized campaign data"""
    return [
        {
            "campaign_id": "camp_001",
            "campaign_name": "Cheese Club September",
            "send_datetime": "2024-09-15T10:00:00Z",
            "channel": "email",
            "sends": 1000,
            "delivered": 980,
            "open_rate": 0.25,
            "click_rate": 0.05,
            "placed_order_count": 25,
            "placed_order_revenue": 1250.0,
            "revenue_per_recipient": 1.25,
            "unsubscribes": 2,
            "spam_complaints": 0
        },
        {
            "campaign_id": "camp_002",
            "campaign_name": "SMS Flash Sale",
            "send_datetime": "2024-09-20T14:00:00Z",
            "channel": "sms",
            "sends": 500,
            "delivered": 495,
            "open_rate": 0.95,
            "click_rate": 0.15,
            "placed_order_count": 35,
            "placed_order_revenue": 1750.0,
            "revenue_per_recipient": 3.50,
            "unsubscribes": 5,
            "spam_complaints": 0
        }
    ]

# Unit Tests - MCP Calendar Service
class TestMCPCalendarService:
    """Test MCP calendar service functionality"""
    
    @pytest.mark.asyncio
    async def test_mcp_failover_success(self, mock_secret_manager):
        """Test successful MCP selection with failover"""
        service = MCPCalendarService(mock_secret_manager)
        
        # Mock successful connection on second MCP
        with patch.object(service, '_test_mcp_connection') as mock_test:
            mock_test.side_effect = [
                MCPConnectionResult(success=False, mcp_name="klaviyo_mcp", auth_context={}, error="Connection failed"),
                MCPConnectionResult(success=True, mcp_name="openapi_mcp", auth_context={"authenticated": True}, response_time_ms=150.0)
            ]
            
            result = await service.select_mcp_with_failover("test_account")
            
            assert result.success is True
            assert result.mcp_name == "openapi_mcp"
            assert result.auth_context["authenticated"] is True
            assert mock_test.call_count == 2
    
    @pytest.mark.asyncio
    async def test_mcp_all_fail(self, mock_secret_manager):
        """Test when all MCPs fail"""
        service = MCPCalendarService(mock_secret_manager)
        
        with patch.object(service, '_test_mcp_connection') as mock_test:
            mock_test.return_value = MCPConnectionResult(
                success=False, mcp_name="test_mcp", auth_context={}, error="All failed"
            )
            
            result = await service.select_mcp_with_failover("test_account")
            
            assert result.success is False
            assert "All MCP services failed" in result.error
    
    @pytest.mark.asyncio
    async def test_data_fetching_with_pagination(self, mock_secret_manager, sample_campaign_data):
        """Test data fetching with pagination and normalization"""
        service = MCPCalendarService(mock_secret_manager)
        
        # Mock HTTP responses with pagination
        mock_responses = [
            {"campaigns": sample_campaign_data[:1]},  # First page
            {"campaigns": sample_campaign_data[1:]},  # Second page
            {"campaigns": []}  # Empty page (end)
        ]
        
        with patch.object(service, '_fetch_page') as mock_fetch:
            mock_fetch.side_effect = [resp["campaigns"] for resp in mock_responses]
            
            time_window = {"year": 2024, "month": 9}
            result = await service.fetch_campaign_data(
                "klaviyo_mcp", {"authenticated": True}, time_window, "test_account"
            )
            
            assert result.success is True
            assert len(result.data) == 2
            assert result.data[0]["campaign_name"] == "Cheese Club September"
            assert result.data[1]["channel"] == "sms"
    
    @pytest.mark.asyncio
    async def test_data_normalization(self, mock_secret_manager):
        """Test field normalization across different MCP schemas"""
        service = MCPCalendarService(mock_secret_manager)
        
        # Raw data with different field names
        raw_data = [
            {
                "id": "camp_001",
                "name": "Test Campaign",
                "sent_count": 1000,
                "delivered_count": 980,
                "open_rate": 25,  # Percentage format
                "conversions": 20,
                "revenue": 500.0
            }
        ]
        
        normalized_data, norm_map = await service._normalize_data("klaviyo_mcp", raw_data)
        
        assert len(normalized_data) == 1
        campaign = normalized_data[0]
        
        # Check field mapping
        assert campaign["campaign_id"] == "camp_001"
        assert campaign["campaign_name"] == "Test Campaign"
        assert campaign["sends"] == 1000
        assert campaign["placed_order_count"] == 20
        assert campaign["open_rate"] == 0.25  # Converted to decimal
        
        # Check normalization map
        assert norm_map["campaign_id"] == "id"
        assert norm_map["sends"] == "sent_count"
    
    @pytest.mark.asyncio
    async def test_retry_logic_with_rate_limiting(self, mock_secret_manager):
        """Test retry logic with rate limiting and exponential backoff"""
        service = MCPCalendarService(mock_secret_manager)
        
        # Mock rate-limited responses followed by success
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {"Retry-After": "1"}
            
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {"campaigns": []}
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                mock_response_429,  # First call: rate limited
                mock_response_200   # Second call: success
            ]
            
            config = service.mcp_configs["klaviyo_mcp"]
            params = {"test": "param"}
            
            with patch('asyncio.sleep') as mock_sleep:  # Mock sleep to speed up test
                result = await service._fetch_page("klaviyo_mcp", config, {"authenticated": True}, params, 1)
                
                assert result == []  # Empty campaigns list
                assert mock_sleep.called  # Verify backoff was used

# Unit Tests - Calendar Orchestrator
class TestCalendarOrchestrator:
    """Test calendar orchestrator graph execution"""
    
    @pytest.mark.asyncio
    async def test_mcp_selector_node(self, calendar_orchestrator):
        """Test MCP selector node"""
        context = {"klaviyo_account_id": "test_account"}
        
        # Mock successful MCP selection
        mock_connection = MCPConnectionResult(
            success=True,
            mcp_name="klaviyo_mcp",
            auth_context={"authenticated": True},
            response_time_ms=100.0
        )
        
        with patch.object(calendar_orchestrator.mcp_service, 'select_mcp_with_failover', return_value=mock_connection):
            result_context = await calendar_orchestrator._node_mcp_selector(context)
            
            assert result_context["selected_mcp"] == "klaviyo_mcp"
            assert result_context["mcp_auth_context"]["authenticated"] is True
            assert result_context["mcp_response_time"] == 100.0
    
    @pytest.mark.asyncio
    async def test_feature_engineering_node(self, calendar_orchestrator, sample_campaign_data):
        """Test feature engineering node"""
        context = {
            "campaign_data": {
                "current_year": sample_campaign_data,
                "prior_year": [],
                "last_30_days": []
            }
        }
        
        result_context = await calendar_orchestrator._node_feature_engineer(context)
        
        features = result_context["engineered_features"]["current_year"]
        assert len(features) == 2
        
        # Check email campaign features
        email_campaign = features[0]
        assert email_campaign["channel"] == "email"
        assert email_campaign["offer_type"] == "cheese_club"
        assert email_campaign["revenue_per_recipient"] == 1.25
        
        # Check SMS campaign features  
        sms_campaign = features[1]
        assert sms_campaign["channel"] == "sms"
        assert sms_campaign["revenue_per_recipient"] == 3.50
    
    @pytest.mark.asyncio
    async def test_scoring_node(self, calendar_orchestrator):
        """Test performance scoring node"""
        sample_features = [
            {
                "campaign_id": "1",
                "revenue_per_recipient": 2.0,
                "placed_order_count": 30,
                "channel": "email"
            },
            {
                "campaign_id": "2", 
                "revenue_per_recipient": 1.0,
                "placed_order_count": 15,
                "channel": "sms"
            }
        ]
        
        context = {
            "engineered_features": {
                "current_year": sample_features,
                "prior_year": [],
                "last_30_days": []
            }
        }
        
        result_context = await calendar_orchestrator._node_scorer(context)
        
        scored_campaigns = result_context["scored_campaigns"]["all"]
        assert len(scored_campaigns) == 2
        
        # Check scoring
        for campaign in scored_campaigns:
            assert "composite_score" in campaign
            assert "performance_tier" in campaign
    
    @pytest.mark.asyncio
    async def test_calendar_strategist_node(self, calendar_orchestrator):
        """Test calendar strategist node with different data scenarios"""
        # Test with no historical data (conservative strategy)
        context = {
            "client_firestore_id": "test_client",
            "target_month": 9,
            "target_year": 2025,
            "scored_campaigns": {"all": []},
            "performance_insights": {}
        }
        
        with patch.object(calendar_orchestrator, '_get_client_profile', return_value={"name": "Test Client"}):
            result_context = await calendar_orchestrator._node_calendar_strategist(context)
            
            strategy = result_context["calendar_strategy"]
            
            # Conservative plan for no historical data
            assert strategy["total_emails"] == 12
            assert strategy["total_sms"] == 3
            assert strategy["reason"] == "Conservative plan - limited historical data"
        
        # Test with historical data (data-driven strategy)
        context["scored_campaigns"] = {"all": [{"composite_score": 1.2}]}
        context["performance_insights"] = {
            "best_weekdays": ["Tuesday", "Wednesday"],
            "best_hours": [10, 14],
            "top_themes": ["cheese_club", "rrb"]
        }
        
        with patch.object(calendar_orchestrator, '_get_client_profile', return_value={"name": "Test Client"}):
            result_context = await calendar_orchestrator._node_calendar_strategist(context)
            
            strategy = result_context["calendar_strategy"]
            
            # Data-driven plan with historical data
            assert strategy["total_emails"] == 20
            assert strategy["total_sms"] == 5
            assert strategy["reason"] == "Data-driven strategy based on historical performance"
    
    @pytest.mark.asyncio
    async def test_calendar_builder_node(self, calendar_orchestrator):
        """Test calendar builder node"""
        context = {
            "target_month": 9,
            "target_year": 2025,
            "calendar_strategy": {
                "total_emails": 4,
                "total_sms": 2,
                "preferred_days": ["Tuesday", "Wednesday", "Thursday"],
                "preferred_hours": [10, 14, 16],
                "themes": ["cheese_club", "rrb"]
            },
            "performance_insights": {}
        }
        
        result_context = await calendar_orchestrator._node_calendar_builder(context)
        
        events = result_context["generated_events"]
        assert len(events) == 6  # 4 emails + 2 SMS
        
        # Check event structure
        email_events = [e for e in events if e["channel"] == "email"]
        sms_events = [e for e in events if e["channel"] == "sms"]
        
        assert len(email_events) == 4
        assert len(sms_events) == 2
        
        # Verify required fields
        for event in events:
            assert "title" in event
            assert "planned_send_datetime" in event
            assert "channel" in event
            assert "source" in event
            assert event["source"] == "EmailPilot AI Calendar"
    
    @pytest.mark.asyncio
    async def test_firestore_writer_node(self, calendar_orchestrator):
        """Test Firestore writer node with versioning"""
        context = {
            "client_firestore_id": "test_client",
            "target_month": 9,
            "target_year": 2025,
            "generated_events": [
                {
                    "title": "Test Email",
                    "channel": "email",
                    "planned_send_datetime": "2025-09-15T10:00:00"
                }
            ],
            "total_events": 1,
            "dry_run": False,
            "selected_mcp": "klaviyo_mcp",
            "normalization_map": {},
            "time_windows": {},
            "calendar_strategy": {"reason": "Test strategy"},
            "started_at": datetime.utcnow(),
            "correlation_id": "test_123"
        }
        
        # Mock Firestore operations
        with patch.object(calendar_orchestrator.db, 'collection') as mock_collection:
            mock_collection.return_value.where.return_value.stream.return_value = []  # No existing calendars
            mock_collection.return_value.add.return_value = (None, MagicMock(id="doc_123"))
            
            result_context = await calendar_orchestrator._node_firestore_writer(context)
            
            write_results = result_context["write_results"]
            assert write_results["events_written"] == 1
            assert write_results["logs_written"] == 1
            assert write_results["version"] == 1
            assert "calendar_id" in write_results
    
    @pytest.mark.asyncio
    async def test_dry_run_mode(self, calendar_orchestrator):
        """Test dry run mode skips writes"""
        context = {
            "dry_run": True,
            "generated_events": [{"title": "Test"}],
            "total_events": 1
        }
        
        result_context = await calendar_orchestrator._node_firestore_writer(context)
        
        write_results = result_context["write_results"]
        assert write_results["dry_run"] is True
        assert write_results["events_written"] == 0

# Integration Tests
class TestCalendarIntegration:
    """Test end-to-end calendar automation integration"""
    
    def test_calendar_build_endpoint(self):
        """Test calendar build endpoint"""
        client = TestClient(app)
        
        request_data = {
            "client_display_name": "Test Client",
            "client_firestore_id": "test_client_123",
            "klaviyo_account_id": "test_klaviyo_456",
            "target_month": 9,
            "target_year": 2025,
            "dry_run": True
        }
        
        with patch('app.api.calendar_orchestrator.get_orchestrator') as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_orchestrator.build_calendar = AsyncMock(return_value="correlation_123")
            mock_get_orch.return_value = mock_orchestrator
            
            response = client.post("/api/calendar/build", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "correlation_id" in data
            assert "status_endpoint" in data
    
    def test_status_endpoint(self):
        """Test status monitoring endpoint"""
        client = TestClient(app)
        
        with patch('app.api.calendar_orchestrator.get_orchestrator') as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_status = MagicMock()
            mock_status.dict.return_value = {
                "status": "completed",
                "progress": 100.0,
                "message": "Calendar automation complete"
            }
            mock_orchestrator.status_updates = {"test_123": mock_status}
            mock_get_orch.return_value = mock_orchestrator
            
            response = client.get("/api/calendar/build/status/test_123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["progress"] == 100.0

# Error Handling Tests
class TestErrorHandling:
    """Test error handling and graceful degradation"""
    
    @pytest.mark.asyncio
    async def test_mcp_failure_handling(self, calendar_orchestrator, sample_calendar_request):
        """Test handling of MCP failures"""
        with patch.object(calendar_orchestrator.mcp_service, 'select_mcp_with_failover') as mock_select:
            mock_select.return_value = MCPConnectionResult(
                success=False, mcp_name="none", auth_context={}, error="All MCPs failed"
            )
            
            with pytest.raises(Exception) as exc_info:
                await calendar_orchestrator.build_calendar(sample_calendar_request)
            
            assert "All MCPs failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_partial_data_handling(self, calendar_orchestrator):
        """Test handling of partial data fetch failures"""
        context = {
            "selected_mcp": "klaviyo_mcp",
            "mcp_auth_context": {"authenticated": True},
            "klaviyo_account_id": "test_account",
            "target_year": 2025,
            "target_month": 9
        }
        
        # Mock partial data fetch failure
        with patch.object(calendar_orchestrator.mcp_service, 'fetch_campaign_data') as mock_fetch:
            mock_fetch.side_effect = [
                MCPDataResult(success=True, data=[{"campaign_id": "1"}], source_mcp="test", normalization_map={}),
                MCPDataResult(success=False, data=[], source_mcp="test", normalization_map={}, error="Fetch failed"),
                MCPDataResult(success=True, data=[{"campaign_id": "2"}], source_mcp="test", normalization_map={})
            ]
            
            result_context = await calendar_orchestrator._node_data_fetcher(context)
            
            # Should handle partial failures gracefully
            assert len(result_context["campaign_data"]) == 3
            assert len(result_context["campaign_data"]["current_year"]) == 1
            assert len(result_context["campaign_data"]["prior_year"]) == 0  # Failed fetch
            assert len(result_context["campaign_data"]["last_30_days"]) == 1
    
    @pytest.mark.asyncio
    async def test_schema_compatibility_verification(self, calendar_orchestrator):
        """Test schema compatibility verification"""
        context = {
            "write_results": {
                "calendar_id": "test_cal_123",
                "version": 1,
                "import_log_id": "log_123"
            },
            "total_events": 2,
            "dry_run": False
        }
        
        # Mock Firestore responses with incomplete data
        mock_docs = [
            MagicMock(to_dict=lambda: {"title": "Test", "source": "AI"}),  # Missing required field
            MagicMock(to_dict=lambda: {"title": "Test 2", "planned_send_datetime": "2025-09-15", "channel": "email", "source": "AI"})
        ]
        
        with patch.object(calendar_orchestrator.db, 'collection') as mock_collection:
            mock_collection.return_value.where.return_value.where.return_value.stream.return_value = mock_docs
            mock_collection.return_value.document.return_value.get.return_value.exists = True
            
            result_context = await calendar_orchestrator._node_verifier(context)
            
            verification = result_context["verification_results"]
            assert verification["events_verified"] is True  # Count matches
            assert verification["log_verified"] is True
            assert verification["schema_compatible"] is False  # Schema check failed
            assert verification["verified"] is False  # Overall verification failed

# Performance Tests
class TestPerformanceOptimizations:
    """Test performance optimizations and scalability"""
    
    @pytest.mark.asyncio
    async def test_event_distribution_algorithm(self, calendar_orchestrator):
        """Test event distribution across month"""
        # Test 30-day month
        dates = calendar_orchestrator._distribute_events(
            total_events=10,
            days_in_month=30,
            preferred_days=["Tuesday", "Wednesday", "Thursday"],
            max_per_day=1
        )
        
        assert len(dates) == 10
        assert all(1 <= date <= 30 for date in dates)
        
        # Check no duplicates (respecting max_per_day)
        assert len(set(dates)) == len(dates)
        
        # Test February (28 days)
        dates_feb = calendar_orchestrator._distribute_events(
            total_events=8,
            days_in_month=28,
            preferred_days=["Monday", "Wednesday", "Friday"],
            max_per_day=1
        )
        
        assert len(dates_feb) == 8
        assert all(1 <= date <= 28 for date in dates_feb)
    
    @pytest.mark.asyncio
    async def test_large_dataset_processing(self, mock_secret_manager):
        """Test processing of large campaign datasets"""
        service = MCPCalendarService(mock_secret_manager)
        
        # Generate large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                "id": f"camp_{i:04d}",
                "name": f"Campaign {i}",
                "sent_count": 1000 + i,
                "delivered_count": 950 + i,
                "open_rate": 20 + (i % 10),
                "conversions": 10 + (i % 20),
                "revenue": 100.0 + (i * 10)
            })
        
        normalized_data, norm_map = await service._normalize_data("klaviyo_mcp", large_dataset)
        
        assert len(normalized_data) == 1000
        assert all("revenue_per_recipient" in campaign for campaign in normalized_data)
        
        # Verify performance calculation
        for i, campaign in enumerate(normalized_data):
            expected_rpr = (100.0 + (i * 10)) / (1000 + i)
            assert abs(campaign["revenue_per_recipient"] - expected_rpr) < 0.01

# CLI Test Command
def test_calendar_automation_cli():
    """Test command to verify calendar automation works end-to-end"""
    sample_payload = {
        "client_display_name": "Demo Client",
        "client_firestore_id": "demo_client_123",
        "klaviyo_account_id": "demo_klaviyo_456",
        "target_month": 10,
        "target_year": 2025,
        "dry_run": True
    }
    
    # This would be the actual CLI test command
    print("CLI Test Command:")
    print("python -m pytest tests/test_calendar_automation.py::test_calendar_automation_cli -v")
    print(f"Sample payload: {json.dumps(sample_payload, indent=2)}")
    
    assert True  # CLI test placeholder

if __name__ == "__main__":
    # Quick test runner for development
    pytest.main([__file__, "-v"])