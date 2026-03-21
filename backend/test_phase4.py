"""Test script for Phase 4 Playbook API."""
import httpx
import asyncio
import json

async def test_playbooks():
    base = 'http://localhost:8000/api/v1'
    results = []
    
    async with httpx.AsyncClient() as client:
        # Login
        login_resp = await client.post(
            f'{base}/auth/login',
            data={'username': 'test@contrared.ai', 'password': 'Test123!'}
        )
        
        if login_resp.status_code != 200:
            results.append(f'Login failed: {login_resp.status_code}')
            with open('test_playbook_results.txt', 'w') as f:
                f.write('\n'.join(results))
            return
            
        token = login_resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        results.append('✅ Login OK')
        
        # Test 1: List playbooks
        list_resp = await client.get(f'{base}/playbooks/', headers=headers)
        results.append(f'List playbooks: {list_resp.status_code}')
        playbooks = list_resp.json() if list_resp.status_code == 200 else []
        results.append(f'   Found {len(playbooks)} playbooks')
        
        # Test 2: Create playbook
        create_resp = await client.post(
            f'{base}/playbooks/',
            json={'name': 'My SaaS Playbook', 'description': 'Custom rules for SaaS contracts', 'category': 'saas'},
            headers=headers
        )
        results.append(f'Create playbook: {create_resp.status_code}')
        
        if create_resp.status_code == 201:
            playbook = create_resp.json()
            playbook_id = playbook['id']
            results.append(f'   Created: {playbook["name"]} (ID: {playbook_id[:8]}...)')
            
            # Test 3: Add rule
            rule_resp = await client.post(
                f'{base}/playbooks/{playbook_id}/rules',
                json={
                    'clause_type': 'Custom Liability Cap',
                    'primary_position': 'Liability capped at 6 months',
                    'risk_level': 'red',
                    'is_deal_breaker': True,
                    'detection_patterns': ['uncapped liability', 'no liability limit']
                },
                headers=headers
            )
            results.append(f'Add rule: {rule_resp.status_code}')
            
            if rule_resp.status_code == 201:
                rule = rule_resp.json()
                results.append(f'   Rule: {rule["clause_type"]} ({rule["risk_level"]})')
                rule_id = rule['id']
                
                # Test 4: Get playbook with rules
                get_resp = await client.get(f'{base}/playbooks/{playbook_id}', headers=headers)
                if get_resp.status_code == 200:
                    detail = get_resp.json()
                    results.append(f'Get playbook: {len(detail["rules"])} rules')
            
            # Test 5: Update playbook
            update_resp = await client.put(
                f'{base}/playbooks/{playbook_id}',
                json={'name': 'My Updated SaaS Playbook'},
                headers=headers
            )
            results.append(f'Update playbook: {update_resp.status_code}')
            
            # Test 6: Toggle publish
            publish_resp = await client.post(f'{base}/playbooks/{playbook_id}/publish', headers=headers)
            if publish_resp.status_code == 200:
                pub_data = publish_resp.json()
                results.append(f'Toggle publish: is_public = {pub_data["is_public"]}')
            
            # Test 7: Analyze with playbook
            analyze_resp = await client.post(
                f'{base}/documents/analyze',
                json={
                    'text': 'This agreement has uncapped liability and no liability limit shall apply.',
                    'filename': 'test.docx',
                    'playbook_id': playbook_id
                },
                headers=headers
            )
            results.append(f'Analyze with playbook: {analyze_resp.status_code}')
            if analyze_resp.status_code == 200:
                analysis = analyze_resp.json()
                results.append(f'   Risks detected: {analysis["total_risks"]}')
                for risk in analysis['risks'][:3]:
                    results.append(f'   - [{risk["risk_level"]}] {risk["rule_name"]}')
            
            # Cleanup: Delete playbook
            delete_resp = await client.delete(f'{base}/playbooks/{playbook_id}', headers=headers)
            results.append(f'Delete playbook: {delete_resp.status_code}')
        else:
            results.append(f'   Error: {create_resp.text}')
    
    with open('test_playbook_results.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))
    print('Results written to test_playbook_results.txt')

if __name__ == '__main__':
    asyncio.run(test_playbooks())
