"""Test de-duplication - CLEAN test with single occurrences."""
import asyncio
import httpx

async def test_dedup():
    base = 'http://localhost:8000/api/v1'
    
    # Clean sample text - ONE occurrence of each pattern
    test_text = """
    MUTUAL NON-DISCLOSURE AGREEMENT

    1. CONFIDENTIALITY
    The Receiving Party agrees to maintain all Confidential 
    Information in perpetuity.
    
    2. RESTRICTIONS
    The Receiving Party shall not reverse engineer, decompile, or disassemble any 
    software or derive source code from any products.
    
    3. NON-SOLICITATION
    The Receiving Party shall not solicit, induce, recruit, or encourage any of 
    the employees to leave their employment.
    
    4. GOVERNING LAW
    This Agreement shall be governed by the laws of the State of Delaware.
    """
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Login
        login = await client.post(f'{base}/auth/login', 
            data={'username': 'test@contrared.ai', 'password': 'Test123!'})
        token = login.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Analyze
        result = await client.post(f'{base}/documents/analyze',
            json={'text': test_text, 'filename': 'clean_test.docx'},
            headers=headers)
        
        if result.status_code != 200:
            results.append(f'FAIL: Analysis failed: {result.text}')
            return results
        
        data = result.json()
        results.append(f'Total risks detected: {data["total_risks"]}')
        results.append('')
        
        # Group by rule
        rules = {}
        for risk in data['risks']:
            name = risk['rule_name']
            # Try different possible keys for match text
            text = risk.get('match_text') or risk.get('clause_text') or risk.get('text', 'N/A')
            if name not in rules:
                rules[name] = []
            rules[name].append(str(text)[:60] + '...')
        
        results.append('=== DETECTED RISKS ===')
        for name, texts in sorted(rules.items()):
            count = len(texts)
            status = 'OK' if count == 1 else f'DUPLICATE ({count}x)'
            results.append(f'\n[{status}] {name}:')
            for t in texts:
                results.append(f'  -> {t}')
        
        # Summary
        results.append('\n=== SUMMARY ===')
        total_dupes = sum(1 for v in rules.values() if len(v) > 1)
        results.append(f'Rules with no duplicates: {len(rules) - total_dupes}/{len(rules)}')
        
        if 'Non-Solicitation Clause' in rules:
            results.append('Non-Solicitation: DETECTED')
        else:
            results.append('Non-Solicitation: MISSING')
    
    return results

if __name__ == '__main__':
    results = asyncio.run(test_dedup())
    output = '\n'.join(results)
    print(output)
    with open('test_dedup_results.txt', 'w', encoding='utf-8') as f:
        f.write(output)
