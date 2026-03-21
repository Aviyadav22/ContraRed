"""Test script for bad regex handling and override test."""
import httpx
import asyncio

async def test_bad_regex():
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
            return results
            
        token = login_resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        results.append('✅ Login OK')
        
        # Create playbook with BAD REGEX
        create_resp = await client.post(
            f'{base}/playbooks/',
            json={'name': 'Bad Regex Test Playbook'},
            headers=headers
        )
        
        if create_resp.status_code != 201:
            results.append(f'Create failed: {create_resp.text}')
            return results
            
        playbook = create_resp.json()
        playbook_id = playbook['id']
        results.append(f'Created playbook: {playbook_id[:8]}...')
        
        # Add rule with BROKEN REGEX pattern: (Liability - unclosed parenthesis
        rule_resp = await client.post(
            f'{base}/playbooks/{playbook_id}/rules',
            json={
                'clause_type': 'Broken Regex Rule',
                'primary_position': 'Fix this broken regex',
                'risk_level': 'red',
                'match_type': 'regex',  # Force regex mode
                'detection_patterns': ['(Liability', 'valid pattern']  # First one is broken
            },
            headers=headers
        )
        results.append(f'Add bad regex rule: {rule_resp.status_code}')
        
        # Now try to ANALYZE - this should NOT crash
        analyze_resp = await client.post(
            f'{base}/documents/analyze',
            json={
                'text': 'This contract has a Liability clause and a valid pattern here.',
                'filename': 'test.docx',
                'playbook_id': playbook_id
            },
            headers=headers
        )
        
        if analyze_resp.status_code == 200:
            results.append('✅ BAD REGEX TEST PASSED: Server did not crash')
            analysis = analyze_resp.json()
            results.append(f'   Risks detected: {analysis["total_risks"]}')
        else:
            results.append(f'❌ BAD REGEX TEST FAILED: Status {analyze_resp.status_code}')
            results.append(f'   Error: {analyze_resp.text}')
        
        # Cleanup
        await client.delete(f'{base}/playbooks/{playbook_id}', headers=headers)
        results.append('Cleanup: Deleted test playbook')
        
        # === OVERRIDE TEST ===
        results.append('\n--- OVERRIDE TEST ---')
        
        # Create playbook that overrides Governing Law to RED
        override_resp = await client.post(
            f'{base}/playbooks/',
            json={'name': 'Override Test Playbook'},
            headers=headers
        )
        override_playbook = override_resp.json()
        override_id = override_playbook['id']
        
        # Add rule: Governing Law = RED (default is GREEN)
        await client.post(
            f'{base}/playbooks/{override_id}/rules',
            json={
                'clause_type': 'Governing Law Override',
                'primary_position': 'Changed to RED in custom playbook',
                'risk_level': 'red',
                'is_deal_breaker': True,
                'match_type': 'exact',
                'detection_patterns': ['governed by', 'laws of', 'governing law']
            },
            headers=headers
        )
        results.append('Created override playbook with Governing Law = RED')
        
        # Analyze WITH custom playbook
        analyze_override = await client.post(
            f'{base}/documents/analyze',
            json={
                'text': 'This Agreement shall be governed by the laws of Delaware.',
                'filename': 'test.docx',
                'playbook_id': override_id
            },
            headers=headers
        )
        
        if analyze_override.status_code == 200:
            data = analyze_override.json()
            risks = data.get('risks', [])
            
            # Check if result is RED (override worked)
            red_risks = [r for r in risks if r['risk_level'] == 'RED']
            if red_risks:
                results.append('✅ OVERRIDE TEST PASSED: Governing Law detected as RED')
                results.append(f'   Found {len(red_risks)} RED risk(s)')
            else:
                # Check what we got
                all_levels = [r['risk_level'] for r in risks]
                results.append(f'⚠️ OVERRIDE TEST: Got risk levels {all_levels}')
        else:
            results.append(f'❌ Override analysis failed: {analyze_override.status_code}')
        
        # Cleanup
        await client.delete(f'{base}/playbooks/{override_id}', headers=headers)
        results.append('Cleanup: Deleted override playbook')
    
    return results

async def main():
    results = await test_bad_regex()
    output = '\n'.join(results)
    with open('test_safety_results.txt', 'w', encoding='utf-8') as f:
        f.write(output)
    print(output)

if __name__ == '__main__':
    asyncio.run(main())
