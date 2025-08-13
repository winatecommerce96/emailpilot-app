#!/usr/bin/env python3
"""
EmailPilot Calendar Performance Testing Script
Tests the optimized calendar components for performance improvements
"""

import asyncio
import time
import json
import statistics
from typing import List, Dict, Any
import requests
import concurrent.futures
from datetime import datetime, timedelta

class CalendarPerformanceTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def test_api_response_times(self, num_requests: int = 50) -> Dict[str, float]:
        """Test API response times for calendar endpoints"""
        self.log(f"Testing API response times ({num_requests} requests)")
        
        endpoints = [
            "/api/calendar/health",
            "/api/calendar/events",
            "/api/admin/clients"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            self.log(f"Testing endpoint: {endpoint}")
            response_times = []
            
            for i in range(num_requests):
                start_time = time.time()
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        response_times.append(response_time)
                    else:
                        self.log(f"Request {i+1} failed: HTTP {response.status_code}", "WARNING")
                        
                except Exception as e:
                    self.log(f"Request {i+1} error: {e}", "ERROR")
                    
            if response_times:
                results[endpoint] = {
                    'avg_response_time': statistics.mean(response_times),
                    'min_response_time': min(response_times),
                    'max_response_time': max(response_times),
                    'p95_response_time': statistics.quantiles(response_times, n=20)[18],  # 95th percentile
                    'success_rate': len(response_times) / num_requests * 100
                }
                
                self.log(f"  Avg: {results[endpoint]['avg_response_time']:.2f}ms")
                self.log(f"  P95: {results[endpoint]['p95_response_time']:.2f}ms")
                self.log(f"  Success Rate: {results[endpoint]['success_rate']:.1f}%")
            else:
                self.log(f"All requests failed for {endpoint}", "ERROR")
                
        return results
        
    def test_concurrent_requests(self, num_threads: int = 10, requests_per_thread: int = 10) -> Dict[str, Any]:
        """Test concurrent request handling"""
        self.log(f"Testing concurrent requests ({num_threads} threads, {requests_per_thread} requests each)")
        
        def make_requests(thread_id: int) -> List[float]:
            thread_times = []
            for i in range(requests_per_thread):
                start_time = time.time()
                try:
                    response = self.session.get(f"{self.base_url}/api/calendar/events", timeout=15)
                    response_time = (time.time() - start_time) * 1000
                    if response.status_code == 200:
                        thread_times.append(response_time)
                except Exception as e:
                    self.log(f"Thread {thread_id}, Request {i+1} error: {e}", "WARNING")
            return thread_times
            
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_requests, i) for i in range(num_threads)]
            all_times = []
            
            for future in concurrent.futures.as_completed(futures):
                all_times.extend(future.result())
                
        total_time = time.time() - start_time
        
        if all_times:
            results = {
                'total_requests': len(all_times),
                'total_time': total_time,
                'requests_per_second': len(all_times) / total_time,
                'avg_response_time': statistics.mean(all_times),
                'p95_response_time': statistics.quantiles(all_times, n=20)[18],
                'success_rate': len(all_times) / (num_threads * requests_per_thread) * 100
            }
            
            self.log(f"  Throughput: {results['requests_per_second']:.2f} RPS")
            self.log(f"  Avg Response: {results['avg_response_time']:.2f}ms")
            self.log(f"  Success Rate: {results['success_rate']:.1f}%")
            
            return results
        else:
            return {"error": "All concurrent requests failed"}
            
    def test_bulk_operations(self) -> Dict[str, Any]:
        """Test bulk event creation performance"""
        self.log("Testing bulk event operations")
        
        # Create test client first
        client_data = {
            "name": "Performance Test Client",
            "email": "test@performance.com"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/calendar/clients",
                json=client_data,
                timeout=10
            )
            
            if response.status_code == 200:
                client_id = response.json().get("id")
                self.log(f"Created test client: {client_id}")
            else:
                self.log("Failed to create test client", "ERROR")
                return {"error": "Failed to create test client"}
                
        except Exception as e:
            self.log(f"Error creating test client: {e}", "ERROR")
            return {"error": str(e)}
            
        # Test bulk event creation
        event_counts = [10, 50, 100]
        results = {}
        
        for count in event_counts:
            self.log(f"Testing bulk creation of {count} events")
            
            # Generate test events
            events = []
            base_date = datetime.now()
            
            for i in range(count):
                event_date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
                events.append({
                    "title": f"Test Event {i+1}",
                    "date": event_date,
                    "client_id": client_id,
                    "content": f"Performance test event {i+1}",
                    "event_type": "email"
                })
            
            start_time = time.time()
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/calendar/events/bulk",
                    json={"client_id": client_id, "events": events},
                    timeout=30
                )
                
                creation_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    result_data = response.json()
                    results[f"{count}_events"] = {
                        "creation_time_ms": creation_time,
                        "events_per_second": count / (creation_time / 1000),
                        "created_count": result_data.get("total_created", 0),
                        "success": True
                    }
                    
                    self.log(f"  Created {count} events in {creation_time:.2f}ms")
                    self.log(f"  Rate: {results[f'{count}_events']['events_per_second']:.2f} events/sec")
                else:
                    self.log(f"Bulk creation failed: HTTP {response.status_code}", "ERROR")
                    results[f"{count}_events"] = {"error": f"HTTP {response.status_code}"}
                    
            except Exception as e:
                self.log(f"Error in bulk creation: {e}", "ERROR")
                results[f"{count}_events"] = {"error": str(e)}
                
        return results
        
    def test_cache_performance(self) -> Dict[str, Any]:
        """Test caching effectiveness"""
        self.log("Testing cache performance")
        
        endpoint = f"{self.base_url}/api/calendar/events"
        
        # First request (cache miss)
        start_time = time.time()
        try:
            response1 = self.session.get(endpoint, timeout=10)
            first_request_time = (time.time() - start_time) * 1000
        except Exception as e:
            return {"error": f"First request failed: {e}"}
            
        # Second request (should be cached)
        start_time = time.time()
        try:
            response2 = self.session.get(endpoint, timeout=10)
            second_request_time = (time.time() - start_time) * 1000
        except Exception as e:
            return {"error": f"Second request failed: {e}"}
            
        if response1.status_code == 200 and response2.status_code == 200:
            cache_improvement = ((first_request_time - second_request_time) / first_request_time) * 100
            
            results = {
                "first_request_ms": first_request_time,
                "second_request_ms": second_request_time,
                "cache_improvement_percent": cache_improvement,
                "likely_cached": second_request_time < first_request_time * 0.8
            }
            
            self.log(f"  First request: {first_request_time:.2f}ms")
            self.log(f"  Second request: {second_request_time:.2f}ms")
            self.log(f"  Cache improvement: {cache_improvement:.1f}%")
            
            return results
        else:
            return {"error": "Cache test requests failed"}
            
    def test_memory_usage(self) -> Dict[str, Any]:
        """Test server memory usage under load"""
        self.log("Testing memory usage under load")
        
        # Get initial stats
        try:
            response = self.session.get(f"{self.base_url}/api/calendar/stats/performance", timeout=10)
            if response.status_code == 200:
                initial_stats = response.json()
            else:
                return {"error": "Could not get initial performance stats"}
        except Exception as e:
            return {"error": f"Error getting initial stats: {e}"}
            
        # Generate load
        self.log("Generating load for memory test...")
        load_requests = 100
        
        for i in range(load_requests):
            try:
                self.session.get(f"{self.base_url}/api/calendar/events", timeout=5)
            except:
                pass  # Continue even if some requests fail
                
        # Get final stats
        try:
            response = self.session.get(f"{self.base_url}/api/calendar/stats/performance", timeout=10)
            if response.status_code == 200:
                final_stats = response.json()
            else:
                return {"error": "Could not get final performance stats"}
        except Exception as e:
            return {"error": f"Error getting final stats: {e}"}
            
        results = {
            "initial_stats": initial_stats,
            "final_stats": final_stats,
            "load_requests": load_requests
        }
        
        # Calculate improvements
        initial_metrics = initial_stats.get("metrics", {})
        final_metrics = final_stats.get("metrics", {})
        
        if "cache_hits" in initial_metrics and "cache_hits" in final_metrics:
            cache_hits_gained = final_metrics["cache_hits"] - initial_metrics["cache_hits"]
            results["cache_hits_gained"] = cache_hits_gained
            self.log(f"  Cache hits gained: {cache_hits_gained}")
            
        if "average_response_time" in final_metrics:
            self.log(f"  Average response time: {final_metrics['average_response_time']:.2f}ms")
            
        return results
        
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite"""
        self.log("🚀 Starting comprehensive performance test suite")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Check if server is running
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                return {"error": "Server health check failed"}
        except Exception as e:
            return {"error": f"Cannot connect to server: {e}"}
            
        self.log("✅ Server connection verified")
        
        # Run all tests
        test_results = {}
        
        # 1. API Response Times
        test_results["api_response_times"] = self.test_api_response_times()
        
        # 2. Concurrent Requests
        test_results["concurrent_requests"] = self.test_concurrent_requests()
        
        # 3. Bulk Operations
        test_results["bulk_operations"] = self.test_bulk_operations()
        
        # 4. Cache Performance
        test_results["cache_performance"] = self.test_cache_performance()
        
        # 5. Memory Usage
        test_results["memory_usage"] = self.test_memory_usage()
        
        total_time = time.time() - start_time
        test_results["test_duration"] = total_time
        
        self.log("=" * 60)
        self.log(f"🎯 Performance test suite completed in {total_time:.2f} seconds")
        
        return test_results
        
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a performance test report"""
        report = []
        report.append("📊 EmailPilot Calendar Performance Test Report")
        report.append("=" * 50)
        report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Test Duration: {results.get('test_duration', 0):.2f} seconds")
        report.append("")
        
        # API Response Times
        if "api_response_times" in results:
            report.append("🌐 API Response Times:")
            for endpoint, metrics in results["api_response_times"].items():
                if isinstance(metrics, dict):
                    report.append(f"  {endpoint}:")
                    report.append(f"    Average: {metrics['avg_response_time']:.2f}ms")
                    report.append(f"    P95: {metrics['p95_response_time']:.2f}ms")
                    report.append(f"    Success Rate: {metrics['success_rate']:.1f}%")
            report.append("")
            
        # Concurrent Requests
        if "concurrent_requests" in results:
            cr = results["concurrent_requests"]
            if "error" not in cr:
                report.append("⚡ Concurrent Request Performance:")
                report.append(f"  Throughput: {cr['requests_per_second']:.2f} requests/second")
                report.append(f"  Average Response: {cr['avg_response_time']:.2f}ms")
                report.append(f"  P95 Response: {cr['p95_response_time']:.2f}ms")
                report.append(f"  Success Rate: {cr['success_rate']:.1f}%")
                report.append("")
                
        # Performance Grade
        report.append("🏆 Performance Grade:")
        
        # Calculate overall grade
        api_avg = 0
        if "api_response_times" in results:
            api_times = [m.get('avg_response_time', 1000) for m in results["api_response_times"].values() if isinstance(m, dict)]
            api_avg = statistics.mean(api_times) if api_times else 1000
            
        concurrent_rps = results.get("concurrent_requests", {}).get("requests_per_second", 0)
        
        grade = "F"
        if api_avg < 100 and concurrent_rps > 50:
            grade = "A"
        elif api_avg < 200 and concurrent_rps > 30:
            grade = "B"
        elif api_avg < 500 and concurrent_rps > 10:
            grade = "C"
        elif api_avg < 1000:
            grade = "D"
            
        report.append(f"  Overall Grade: {grade}")
        report.append(f"  API Performance: {'Excellent' if api_avg < 100 else 'Good' if api_avg < 300 else 'Poor'}")
        report.append(f"  Throughput: {'High' if concurrent_rps > 30 else 'Medium' if concurrent_rps > 10 else 'Low'}")
        
        return "\n".join(report)

def main():
    """Main function to run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EmailPilot Calendar Performance Tester")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for testing")
    parser.add_argument("--output", default="performance_report.json", help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    tester = CalendarPerformanceTester(args.url)
    
    print("🚀 EmailPilot Calendar Performance Testing")
    print("=" * 50)
    
    # Run tests
    results = tester.run_comprehensive_test()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"💾 Results saved to: {args.output}")
    
    # Generate and display report
    report = tester.generate_report(results)
    print("\n" + report)
    
    # Save report
    report_file = args.output.replace('.json', '_report.txt')
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"📄 Report saved to: {report_file}")

if __name__ == "__main__":
    main()
