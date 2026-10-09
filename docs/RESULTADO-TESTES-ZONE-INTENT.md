# Resultado dos Testes: Zone Intent no Build

Commit validado: `364bb03 feat(zone-intent): integrate semantic validation into build`

## Resultado Final

```text
python3 -m unittest discover -s tests
Ran 811 tests
OK
```

| Métrica | Resultado |
| --- | --- |
| Baseline antes da integração | 805 testes, 0 falhas |
| Após a integração | 811 testes, 0 falhas |
| Testes adicionados | 6 |
| `git diff --check` | Limpo |

## Cobertura Adicionada

`ZoneIntentBuildGuardrailTest` em `tests/test_plan.py` verifica que:

- `zone2` e `endurance` resolvem para `ENDURANCE`.
- `sweetspot` e `threshold` resolvem para seus perfis declarados.
- A sobreposição de 91-97% FTP continua sendo resolvida pelo `focus`, não por `on_power`.
- `vo2max` não possui perfil e continua o build sem bloquear o fluxo.
- Cada workout construído chama a resolução semântica uma vez.
- Divergência entre `focus` e `params.focus` falha como guardrail interno.
- O plano e os payloads permanecem estruturalmente idênticos com ou sem o guardrail.

## Neutralidade Prescritiva

Para o cenário determinístico usado no teste (`FTP=182`, cinco dias, início em
`2026-09-14`), antes e depois são iguais:

| Campo | Valor |
| --- | --- |
| `focus` | `threshold` |
| `on_power` | `0.98` |
| `on_sec` | `380` |
| `repeats` | `3` |
| `off_sec` | `240` |
| `tss` | `40.0` |

Não foram alterados `plan.json`, `ZONE_BANDS`, `zone_floor`, `zone_ceiling`,
`event_payload`, `cmd_push` ou a prescrição publicada.
