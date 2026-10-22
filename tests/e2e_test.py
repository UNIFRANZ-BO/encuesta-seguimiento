"""Prueba de punta a punta de la app con un backend simulado (no toca la hoja real).
Requisitos: pip install playwright && playwright install chromium
Uso: python3 tests/e2e_test.py        (genera capturas en tests/shots/)
"""
import asyncio, json, pathlib, sys
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SHOTS = RAIZ / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True)
API = 'https://script.google.com/macros/s/TESTID/exec'
W = int(sys.argv[1]) if len(sys.argv) > 1 else 390
DB, DONE = {}, {'lpze.ya.respondio.xx@unifranz.edu.bo'}
ROSTER = {'cbbe.juanperez.lopez.ga@unifranz.edu.bo': {'nombre': 'Juan', 'sede': 'CBB', 'sede_nombre': 'Cochabamba', 'carrera_cod': 'NGE',
          'carrera': 'Negocios y Gestión Empresarial', 'semestre': '', 'plan': 2026, 'modalidad': ''}}   # la base actual no trae semestre

async def backend(route, req):
    q = parse_qs(urlparse(req.url).query)
    if req.method == 'POST':
        d = json.loads(req.post_data)['data']
        out = {'ok': False, 'codigo': 'ya_respondio', 'fecha': '07/10/2026'} if d['correo'] in DONE else {'ok': True, 'id': d['id']}
        if out['ok']: DB[d['id']] = d; DONE.add(d['correo'])
        return await route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}, body=json.dumps(out))
    a, cb = q.get('action', ['ping'])[0], q.get('callback', [''])[0]
    if a == 'validar':
        c = q['correo'][0]
        out = ({'ok': True, 'habilitado': False, 'motivo': 'ya_respondio', 'fecha': '07/10/2026'} if c in DONE else
               {'ok': True, 'habilitado': True, 'estudiante': ROSTER[c], 'carreras': []} if c in ROSTER else
               {'ok': True, 'habilitado': False, 'motivo': 'no_encontrado'})
    else:
        out = {'ok': True, 'existe': q.get('id', [''])[0] in DB}
    await route.fulfill(status=200, headers={'Content-Type': 'application/javascript'}, body=f'{cb}({json.dumps(out)});')

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await (await b.new_context(viewport={'width': W, 'height': 844 if W < 600 else 800}, is_mobile=W < 600, has_touch=W < 600)).new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.route('https://script.google.com/**', backend)
        await pg.goto((RAIZ / 'index.html').as_uri() + '?api=' + API); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(SHOTS / f'{W}_00_bienvenida.png'))
        await pg.evaluate("autoNext=()=>{}")
        await pg.click('#start'); await pg.wait_for_timeout(1200)
        await pg.fill('#mailIn', 'nadie@unifranz.edu.bo'); await pg.click('#btnVerify'); await pg.wait_for_timeout(1500)
        assert 'No encontramos' in await pg.inner_text('#mailMsg')
        await pg.fill('#mailIn', 'CBBE.JuanPerez.Lopez.ga@unifranz.edu.bo '); await pg.click('#btnVerify'); await pg.wait_for_timeout(2600)
        assert await pg.evaluate("STEPS[S.i].k") == 'm2'
        ANS = {'p05': 4, 'p06': 3, 'p07': 5, 'p08': 4, 'p10': 4, 'p11': 5}
        for _ in range(40):
            k = await pg.evaluate("STEPS[S.i].k")
            if k == 'review': break
            if k == 'p03': await pg.click('.opt[data-v="Segundo"]')
            elif k == 'p04':
                assert await pg.locator('.opt').count() == 3
                await pg.click('.opt >> nth=1')
            elif k == 'r02':
                assert await pg.locator('.orb').count() == 0 and (await pg.inner_text('.opt >> nth=0')).find('En todas o casi todas') >= 0
                await pg.click('.opt[data-n="4"]')
            elif k == 'r03':
                assert await pg.locator('.opt').count() == 5
                await pg.click('.opt[data-n="5"]')
            elif k in ANS: await pg.click(f'.orb[data-n="{ANS[k]}"]')
            elif k == 'p09': await pg.click('.opt[data-v="Aprendizaje"]')
            elif k == 'r01':
                for i in [0, 2, 6, 8]: await pg.click(f'.opt[data-i="{i}"]')
                assert await pg.evaluate("S.a.r01.length") == 3, 'r01 debe limitar a 3'
            await pg.wait_for_timeout(600)
            await pg.screenshot(path=str(SHOTS / f'{W}_{k}.png'))
            if k.startswith('m'): await pg.click('[data-act=next]')
            else: await pg.wait_for_timeout(250); await pg.click('#btnNext')
            await pg.wait_for_timeout(1100)
        await pg.screenshot(path=str(SHOTS / f'{W}_revision.png'), full_page=True)
        await pg.click('#btnSend'); await pg.wait_for_timeout(2500)
        assert len(DB) == 1, 'la respuesta no llegó al backend'
        d = list(DB.values())[0]
        print(json.dumps(d, ensure_ascii=False))
        esper = {'semestre': 2, 'p03': 'Segundo', 'p04': 'Tengo algo de conocimiento, pero requiero más información', 'p09': 'Aprendizaje', 'r02': 4, 'r03': 5, 'r01_idx': [1, 3, 7]}
        for k, v in esper.items(): assert d[k] == v, (k, d[k], v)
        assert not errs, errs
        print('OK · errores JS:', errs)
        await b.close()

asyncio.run(main())
