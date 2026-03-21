"""Quick test for billing API endpoints."""
import httpx
import asyncio

async def test_billing():
    base = 'http://localhost:8000/api/v1'
    results = []
    
    async with httpx.AsyncClient() as client:
        # Login
        login_resp = await client.post(
            f'{base}/auth/login',
            data={'username': 'test@contrared.ai', 'password': 'Test123!'}
        )
        
        if login_resp.status_code != 200:
            results.append(f'❌ Login failed: {login_resp.status_code}')
            return results
            
        token = login_resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        results.append('✅ Login OK')
        
        # Test 1: Get plans
        plans_resp = await client.get(f'{base}/billing/plans')
        if plans_resp.status_code == 200:
            plans = plans_resp.json()
            results.append(f'✅ GET /billing/plans: {len(plans)} plans')
            for plan in plans:
                results.append(f'   - {plan["name"]}: ₹{plan["price"]/100}')
        else:
            results.append(f'❌ GET /billing/plans: {plans_resp.status_code}')
        
        # Test 2: Get subscription
        sub_resp = await client.get(f'{base}/billing/subscription', headers=headers)
        if sub_resp.status_code == 200:
            sub = sub_resp.json()
            results.append(f'✅ GET /billing/subscription:')
            results.append(f'   Plan: {sub["plan"]}')
            results.append(f'   Status: {sub["status"]}')
            results.append(f'   Used: {sub["documents_used"]}/{sub["documents_limit"]} docs')
        else:
            results.append(f'❌ GET /billing/subscription: {sub_resp.status_code} - {sub_resp.text}')
        
        # Test 3: Get invoices
        inv_resp = await client.get(f'{base}/billing/invoices', headers=headers)
        if inv_resp.status_code == 200:
            invoices = inv_resp.json()
            results.append(f'✅ GET /billing/invoices: {len(invoices)} invoices')
        else:
            results.append(f'❌ GET /billing/invoices: {inv_resp.status_code}')
    
    return results

async def main():
    results = await test_billing()
    output = '\n'.join(results)
    print(output)
    with open('test_billing_results.txt', 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == '__main__':
    asyncio.run(main())
