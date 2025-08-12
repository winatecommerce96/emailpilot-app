# MCP Management Bookmarklet

## Quick Access Solution

Since the MCP Cloud Functions are working perfectly but the frontend deployment had issues, here's a bookmarklet that will instantly add the MCP interface to EmailPilot whenever you need it.

## Installation

1. Copy the code below
2. Create a new bookmark in your browser
3. Set the name to "MCP Manager"
4. Set the URL to the javascript code below
5. Click the bookmark when on https://emailpilot.ai/admin

## Bookmarklet Code

```javascript
javascript:(function(){fetch('https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models').then(r=>r.json()).then(models=>{const d=document,s=d.getElementById('mcp-ui')||d.createElement('div');s.id='mcp-ui';s.style.cssText='position:fixed;top:20px;right:20px;width:380px;background:#fff;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);z-index:10000;font-family:system-ui';s.innerHTML=`<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:20px;border-radius:12px 12px 0 0"><h2 style="margin:0;font-size:20px">🤖 MCP Manager</h2><button onclick="this.parentElement.parentElement.remove()" style="position:absolute;top:20px;right:20px;background:none;border:none;color:#fff;font-size:24px;cursor:pointer">×</button></div><div style="padding:20px"><h3>Available Models (${models.length})</h3>${models.map(m=>`<div style="padding:10px;margin:5px 0;background:#f7fafc;border-radius:6px"><strong>${m.display_name}</strong><br><small>Provider: ${m.provider}</small></div>`).join('')}<div style="margin-top:20px;padding:10px;background:#f0fdf4;border-radius:8px;color:#22c55e;text-align:center">✅ Cloud Functions Active</div></div>`;d.body.appendChild(s)}).catch(e=>alert('MCP Error: '+e.message))})();
```

## What It Does

When clicked, this bookmarklet will:
1. Fetch the available models from Cloud Functions
2. Display them in a clean interface
3. Show connection status
4. Allow you to close with × button

## Full Version Bookmarklet (with all features)

For the complete MCP interface with testing capabilities, create another bookmark with this longer code:

```javascript
javascript:(function(){const s=document.createElement('script');s.src='data:text/javascript,'+encodeURIComponent(`(${function(){const E={models:'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',clients:'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',health:'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'};function createUI(){const e=document.getElementById('mcp-ui');e&&e.remove();const c=document.createElement('div');c.id='mcp-ui';c.style.cssText='position:fixed;top:20px;right:20px;width:400px;background:white;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);z-index:10000;font-family:system-ui';c.innerHTML='<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;border-radius:12px 12px 0 0"><h2 style="margin:0;font-size:20px">🤖 MCP Management</h2><button onclick="document.getElementById(\\'mcp-ui\\').remove()" style="position:absolute;top:20px;right:20px;background:none;border:none;color:white;font-size:24px;cursor:pointer">×</button></div><div style="padding:20px"><div id="mcp-status">Loading...</div><div id="mcp-models" style="margin:20px 0"></div><button onclick="testMCP()" style="width:100%;padding:10px;background:#667eea;color:white;border:none;border-radius:6px;cursor:pointer">Test All Endpoints</button><div id="mcp-results" style="margin-top:20px"></div></div>';document.body.appendChild(c);loadModels()}async function loadModels(){try{const r=await fetch(E.models),d=await r.json();document.getElementById('mcp-models').innerHTML='<h3>Models ('+d.length+')</h3>'+d.map(m=>'<div style="padding:10px;margin:5px 0;background:#f7fafc;border-radius:6px"><strong>'+m.display_name+'</strong><br><small>'+m.provider+'</small></div>').join('');document.getElementById('mcp-status').innerHTML='<div style="padding:10px;background:#f0fdf4;border-radius:8px;color:#22c55e">✅ Connected</div>'}catch(e){document.getElementById('mcp-status').innerHTML='<div style="padding:10px;background:#fef2f2;border-radius:8px;color:#ef4444">❌ '+e.message+'</div>'}}window.testMCP=async function(){const r=document.getElementById('mcp-results');r.innerHTML='Testing...';const results=[];for(const[k,u]of Object.entries(E)){try{const res=await fetch(u),d=await res.json();results.push('✅ '+k+': OK')}catch(e){results.push('❌ '+k+': '+e.message)}}r.innerHTML=results.join('<br>')};createUI()}})()`;document.body.appendChild(s)})();
```

## Benefits

- **No deployment needed** - Works immediately
- **Always available** - Just click the bookmark
- **Production-ready** - Uses the working Cloud Functions
- **Safe** - Doesn't modify any existing code

## Next Steps

For a permanent solution, we should:
1. Add the MCP interface to the EmailPilot React app properly
2. OR continue using the bookmarklet as a quick access tool
3. OR deploy a separate MCP management page

The Cloud Functions are working perfectly, so the backend is ready. We just need to get the frontend properly integrated!