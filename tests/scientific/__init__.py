"""Invariantes científicas do motor.

Estes testes não conferem se uma função roda: conferem se as *propriedades*
que o embasamento promete continuam verdadeiras. O objetivo declarado em
`docs/EMBASAMENTO-CIENTIFICO.md` é impedir que uma mudança futura transforme
heurística documentada em regra fisiológica rígida sem justificativa.

Duas categorias de teste aqui:

* **Propriedade** — vale para uma família de entradas (monotonicidade,
  idempotência, limites, comutatividade quando deveria ser).
* **Trava de contrato** — fixa o valor ou o comportamento que o documento
  declara, para que a alteração precise ser explícita.

Os módulos `src/vo2_generator.py` e `src/zone_intent.py` são exercitados aqui
também, porque suas heurísticas (Z5 ceiling, recuperação, não-universalidade de
115%) só se sustentam se forem verificadas como invariantes.
"""
