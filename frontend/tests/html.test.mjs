import test from 'node:test'
import assert from 'node:assert/strict'
import { escaparHTML } from '../src/utils/html.js'

test('popup não interpreta nomes ou mensagens como HTML executável', () => {
    assert.equal(escaparHTML('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;')
    assert.equal(escaparHTML("A&B's"), 'A&amp;B&#39;s')
    assert.equal(escaparHTML('Évora'), 'Évora')
    assert.equal(escaparHTML(null), '')
    assert.equal(escaparHTML(0), '0')
})
