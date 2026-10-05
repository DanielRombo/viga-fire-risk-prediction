// Respostas HTTP reais exportadas da API isolada; restantes áreas simuladas.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { preparar } from '../../frontend/tests/dashboard.browser.mjs'
const ler = async nome => JSON.parse(await readFile(new URL(`evidencias/${nome}`,import.meta.url),'utf8'))

test('Fase 6: Lisboa real passa de indisponível para valor técnico', async t => {
    const { page, controlo } = await preparar(t)
    const antes=await ler('Lisboa_api_antes.json'), depois=await ler('Lisboa_api.json')
    let dados=antes
    controlo.fwi=async (id,route,historico) => {
        if (id!==depois.id_regiao) return false
        if (historico) {
            const h=await ler('Lisboa_api_historico.json')
            const url=new URL(route.request().url())
            h.resultados=h.resultados.filter(r=>r.data_referencia>=url.searchParams.get('inicio') && r.data_referencia<=url.searchParams.get('fim'))
            await route.fulfill({json:h})
        } else await route.fulfill({json:dados})
        return true
    }
    await page.reload()
    const painel=page.locator('.painel-fwi-diario')
    await page.waitForFunction(()=>document.querySelector('.painel-fwi-diario')?.getAttribute('aria-busy')==='false')
    assert.equal(await painel.getByTestId('valor-fwi-diario').textContent(),'Indisponível')
    dados=depois
    await page.clock.runFor(60_001)
    await page.waitForFunction(()=>document.querySelector('[data-testid="valor-fwi-diario"]')?.textContent==='4,46')
    assert.match(await painel.textContent(),/Não operacional — valor técnico/)
    assert.doesNotMatch(await painel.textContent(),/Operacional estabelecido/)
    assert.match(await painel.textContent(),/30\/09\/2026/)
    await page.screenshot({path:fileURLToPath(new URL('evidencias/Lisboa_dashboard.png',import.meta.url)),fullPage:true})
    await page.goto('http://127.0.0.1:5174/regiao/1')
    await page.waitForFunction(()=>document.querySelector('.historico-fwi-diario tbody')?.children.length===30)
    assert.match(await painel.textContent(),/Reconstruído/)
    assert.match(await painel.textContent(),/ecmwf-ifs/)
    dados={...depois,fwi:0}
    await page.clock.runFor(60_001)
    await page.waitForFunction(()=>document.querySelector('[data-testid="valor-fwi-diario"]')?.textContent==='0')
    dados={...depois,fwi:null,estado:'dados_incompletos'}
    await page.clock.runFor(60_001)
    await page.waitForFunction(()=>document.querySelector('[data-testid="valor-fwi-diario"]')?.textContent==='Indisponível')
    await writeFile(new URL('evidencias/browser.json',import.meta.url),JSON.stringify({passou:true,
        navegador:'Edge',api:'Respostas reais da API isolada reproduzidas no navegador; sem ligação HTTP direta à BD.',
        zero_null:'Variações simuladas explícitas, sem alteração de valores reais persistidos.'},null,2))
})
