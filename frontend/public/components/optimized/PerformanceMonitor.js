// Performance Monitor Component for EmailPilot Calendar
const { useState, useEffect, useRef, memo } = React;

const PerformanceMonitor = memo(({ enabled = false }) => {
    const [metrics, setMetrics] = useState({
        renderTime: 0,
        memoryUsage: 0,
        apiResponseTime: 0,
        cacheHitRate: 0,
        eventsCount: 0,
        reRenderCount: 0
    });
    
    const [isVisible, setIsVisible] = useState(false);
    const [alerts, setAlerts] = useState([]);
    const renderCount = useRef(0);
    const lastUpdate = useRef(0);
    
    const thresholds = {
        renderTime: 16,
        memoryUsage: 100,
        apiResponseTime: 500,
        cacheHitRate: 80,
        reRenderCount: 50
    };
    
    useEffect(() => {
        renderCount.current++;
        setMetrics(prev => ({
            ...prev,
            reRenderCount: renderCount.current
        }));
    });
    
    useEffect(() => {
        if (!enabled) return;
        
        let intervalId = setInterval(() => {
            const now = Date.now();
            
            if (now - lastUpdate.current < 500) return;
            lastUpdate.current = now;
            
            if (performance.memory) {
                const memoryUsage = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024);
                setMetrics(prev => ({
                    ...prev,
                    memoryUsage
                }));
            }
        }, 1000);
        
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [enabled]);
    
    const getPerformanceGrade = () => {
        let score = 100;
        
        if (metrics.renderTime > thresholds.renderTime) score -= 20;
        if (metrics.memoryUsage > thresholds.memoryUsage) score -= 25;
        if (metrics.apiResponseTime > thresholds.apiResponseTime) score -= 15;
        
        if (score >= 90) return { grade: 'A', color: 'text-green-600', bg: 'bg-green-100' };
        if (score >= 80) return { grade: 'B', color: 'text-blue-600', bg: 'bg-blue-100' };
        if (score >= 70) return { grade: 'C', color: 'text-yellow-600', bg: 'bg-yellow-100' };
        return { grade: 'F', color: 'text-red-600', bg: 'bg-red-100' };
    };
    
    if (!enabled || !window.location.hostname.includes('localhost')) {
        return null;
    }
    
    const performanceGrade = getPerformanceGrade();
    
    return (
        <div className="fixed bottom-4 right-4 z-50">
            <button
                onClick={() => setIsVisible(!isVisible)}
                className="mb-2 px-3 py-2 rounded-full shadow-lg text-sm font-medium transition-all bg-white border"
                title="Performance Monitor"
            >
                Perf {performanceGrade.grade}
            </button>
            
            {isVisible && (
                <div className="bg-white rounded-lg shadow-xl border border-gray-200 p-4 w-80">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-gray-900">Performance</h3>
                        <span className="text-xs px-2 py-1 rounded bg-gray-100">
                            Grade: {performanceGrade.grade}
                        </span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                        <div className="p-2 bg-gray-50 rounded">
                            <div className="text-xs text-gray-600">Memory</div>
                            <div className="text-sm font-bold">{metrics.memoryUsage}MB</div>
                        </div>
                        <div className="p-2 bg-gray-50 rounded">
                            <div className="text-xs text-gray-600">Renders</div>
                            <div className="text-sm font-bold">{metrics.reRenderCount}</div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
});

window.PerformanceMonitor = PerformanceMonitor;

export { PerformanceMonitor };
