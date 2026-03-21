"""Test script for Phase 2 API - Outputs to file."""
import httpx
import asyncio
import json

async def test_api():
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
            with open('test_results.txt', 'w') as f:
                f.write('\n'.join(results))
            return
            
        token = login_resp.json()['access_token']
        results.append(f'Login OK')
        
        # Test analyze
        test_text = '''The Vendor shall have unlimited liability for all damages arising from this Agreement. This Agreement shall automatically renew for successive one-year terms unless terminated with 30 days notice. The Vendor may terminate this Agreement at any time without cause. This Agreement shall be governed by the laws of Delaware.'''
        
        analyze_resp = await client.post(
            f'{base}/documents/analyze',
            json={'text': test_text, 'filename': 'test_contract.docx'},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        results.append(f'Analyze status: {analyze_resp.status_code}')
        
        if analyze_resp.status_code == 200:
            data = analyze_resp.json()
            results.append(f'Total risks: {data["total_risks"]}')
            results.append(f'Risk summary: {json.dumps(data["risk_summary"])}')
            results.append('')
            results.append('Risks found:')
            for i, risk in enumerate(data['risks'][:5]):
                results.append(f'{i+1}. [{risk["risk_level"]}] {risk["rule_name"]}')
                results.append(f'   Clause: {risk["clause_text"][:100]}...')
                results.append(f'   Explanation: {risk["ai_explanation"] or "N/A"}')
                results.append(f'   Suggested Fix: {risk["suggested_fix"][:80] if risk.get("suggested_fix") else "N/A"}')
                results.append('')
        else:
            results.append(f'Error: {analyze_resp.text}')
    
    with open('test_results.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))
    print('Results written to test_results.txt')

if __name__ == '__main__':
    asyncio.run(test_api())
