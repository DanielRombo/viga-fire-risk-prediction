const normalizar = valor => (valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()

export function encontrarRegiaoMapa(regioes, nome) {
    const distrito = normalizar(nome)
    if (['azores', 'acores'].includes(distrito)) {
        return regioes.find(r => normalizar(r.nome) === 'ponta delgada' && normalizar(r.distrito) === 'acores')
    }
    if (distrito === 'madeira') {
        return regioes.find(r => normalizar(r.nome) === 'funchal' && normalizar(r.distrito) === 'madeira')
    }
    return regioes.find(r => normalizar(r.nome) === distrito)
}
