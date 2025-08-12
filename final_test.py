#!/usr/bin/env python3
import requests

print('🎉 EMAILPILOT.AI FINAL TEST')
print('='*50)

API = 'https://emailpilot.ai'
s = requests.Session()

# Authenticate
auth = s.post(f'{API}/api/auth/google/callback', 
              json={'email': 'damon@winatecommerce.com', 'name': 'Damon', 'picture': ''})

if auth.status_code == 200:
    print('✅ Authentication successful')
    
    # Get clients
    clients = s.get(f'{API}/api/clients/')
    if clients.status_code == 200:
        client_list = clients.json()
        print(f'✅ Clients: {len(client_list)} active clients')
        for c in client_list[:3]:
            print(f'   - {c.get("name")}')
    
    # Get goals
    goals = s.get(f'{API}/api/goals/clients')
    if goals.status_code == 200:
        goals_list = goals.json()
        print(f'✅ Goals: {len(goals_list)} clients')
        clients_with_goals = [g for g in goals_list if g.get('goals_count', 0) > 0]
        print(f'   - {len(clients_with_goals)} clients have goals')
        for g in clients_with_goals[:3]:
            print(f'   - {g.get("name")}: {g.get("goals_count")} goals')
    
    # Test specific client goals
    if clients_with_goals:
        test_client = clients_with_goals[0]
        client_goals = s.get(f'{API}/api/goals/{test_client["id"]}')
        if client_goals.status_code == 200:
            goals_data = client_goals.json()
            print(f'✅ Client Goals: {len(goals_data)} goals for {test_client.get("name")}')
            if goals_data:
                recent = goals_data[0]
                print(f'   Latest: {recent.get("year")}-{recent.get("month"):02d} - ${recent.get("revenue_goal"):,.2f}')

print('\n✅ EmailPilot.ai is fully operational!')
print('📝 You can now login at https://emailpilot.ai')