#!/usr/bin/env node

// Test script to verify component loading
const puppeteer = require('puppeteer');

async function testComponentLoading() {
    console.log('Testing CalendarView component loading...');
    
    let browser;
    try {
        browser = await puppeteer.launch({ 
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        const page = await browser.newPage();
        
        // Navigate to the application
        await page.goto('http://localhost:8000', { 
            waitUntil: 'networkidle0',
            timeout: 10000 
        });
        
        // Wait a moment for scripts to load
        await page.waitForTimeout(3000);
        
        // Check component availability
        const componentStatus = await page.evaluate(() => {
            return {
                CalendarViewSimple: typeof window.CalendarViewSimple,
                CalendarView: typeof window.CalendarView,
                Calendar: typeof window.Calendar,
                EventModal: typeof window.EventModal,
                CalendarViewLocal: typeof window.CalendarViewLocal,
                FirebaseCalendarService: typeof window.FirebaseCalendarService,
                GeminiChatService: typeof window.GeminiChatService,
                CAMPAIGN_COLORS: typeof window.CAMPAIGN_COLORS
            };
        });
        
        console.log('\n📊 Component Loading Status:');
        console.log('================================');
        
        Object.entries(componentStatus).forEach(([name, type]) => {
            const status = type === 'function' ? '✅ Loaded' : 
                          type === 'object' ? '📋 Available' : 
                          `❌ Missing (${type})`;
            console.log(`${name.padEnd(22)}: ${status}`);
        });
        
        // Check for any console errors
        const logs = await page.evaluate(() => {
            return window.componentLoadingLogs || [];
        });
        
        if (logs.length > 0) {
            console.log('\n📝 Component Loading Logs:');
            logs.forEach(log => console.log(`  ${log}`));
        }
        
        // Summary
        const loadedCount = Object.values(componentStatus).filter(type => 
            type === 'function' || type === 'object'
        ).length;
        const totalCount = Object.keys(componentStatus).length;
        
        console.log(`\n📈 Summary: ${loadedCount}/${totalCount} components loaded successfully`);
        
        if (componentStatus.CalendarView === 'function' && 
            componentStatus.Calendar === 'function' && 
            componentStatus.EventModal === 'function') {
            console.log('🎉 SUCCESS: All critical calendar components are loaded!');
            return true;
        } else {
            console.log('⚠️  ISSUE: Some critical components are missing');
            return false;
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        return false;
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

// Check if puppeteer is available, otherwise fall back to curl test
async function simpleCurlTest() {
    console.log('Testing component loading with curl...');
    
    const { exec } = require('child_process');
    const util = require('util');
    const execAsync = util.promisify(exec);
    
    try {
        // Test if we can load the page
        const { stdout, stderr } = await execAsync('curl -s http://localhost:8000/');
        
        if (stdout.includes('CalendarView') && 
            stdout.includes('Calendar.js') && 
            stdout.includes('EventModal.js')) {
            console.log('✅ Basic component loading verification passed');
            console.log('   - Page loads successfully');
            console.log('   - Component scripts are referenced');
            console.log('   - HTML structure looks correct');
            return true;
        } else {
            console.log('❌ Basic verification failed - missing component references');
            return false;
        }
    } catch (error) {
        console.error('❌ Curl test failed:', error.message);
        return false;
    }
}

// Main execution
async function main() {
    console.log('🔍 Calendar Component Loading Test\n');
    
    try {
        // Try puppeteer first, fall back to curl
        const hasServerRunning = await new Promise((resolve) => {
            const http = require('http');
            const req = http.get('http://localhost:8000/', (res) => {
                resolve(true);
            });
            req.on('error', () => resolve(false));
            req.setTimeout(2000, () => {
                req.destroy();
                resolve(false);
            });
        });
        
        if (!hasServerRunning) {
            console.log('❌ Server not running on http://localhost:8000');
            console.log('   Please run: make dev');
            process.exit(1);
        }
        
        let success = false;
        
        try {
            success = await testComponentLoading();
        } catch (error) {
            console.log('ℹ️  Puppeteer not available, falling back to simple test...');
            success = await simpleCurlTest();
        }
        
        process.exit(success ? 0 : 1);
        
    } catch (error) {
        console.error('❌ Test execution failed:', error.message);
        process.exit(1);
    }
}

main();