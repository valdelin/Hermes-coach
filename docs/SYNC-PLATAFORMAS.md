# Sincronização de plataformas com o Intervals.icu

Guia de como conectar o Intervals.icu às plataformas compatíveis (atividades,
wellness e treinos planejados). Baseado na documentação oficial e nos fóruns
do Intervals.icu (2026-09).

> Onde tudo isso fica no painel: **Settings → Connections** (canto superior
> direito, ícone do perfil).

## Resumo por plataforma

| Plataforma | Atividades (in) | Wellness | Treinos planejados (out) | Observações |
|---|---|---|---|---|
| **Garmin Connect** | ✅ | ✅ (RHR, sono, HRV, peso...) | ✅ | A mais completa; exige scopes de wellness |
| **Wahoo (ELEMNT/SYSTM)** | ✅ | ~ | ✅ | 2 checkboxes independentes (in/out) |
| **Zwift** | ✅ | — | ✅ | Conexão direta; workouts da semana no app |
| **COROS** | ✅ | ✅ | ✅ | |
| **Suunto** | ✅ | ✅ | ✅ | |
| **Polar Flow** | ✅ | ✅ | ❌ (limitação da plataforma) | Treinos: exportar FIT manual |
| **Amazfit** | ✅ | ✅ | ✅ (alguns modelos) | |
| **Strava** | ✅ | — | ❌ | Cuidado com duplicatas; pode "dormir" |
| **Huawei Health** | ~ (limitado) | ✅ | ~ | Depende do modelo/região |
| **Dropbox** | ✅ (arquivos FIT/TCX/GPX) | — | ❌ | Upload manual de arquivos |
| **Oura / WHOOP** | — | ✅ | ❌ | Só wellness (sono/HRV/readiness) |
| **Apple Health (Watch)** | ✅ via app/HealthFit | ✅ | ❌ | Não há conexão nativa; usar ponte 3ª parte |

Legenda: ✅ suportado · ~ parcial/limitado · ❌ não suportado · — não se aplica

---

## 1. Garmin Connect (recomendada — a mais completa)

**O que sincroniza:** atividades, wellness (FC repouso, sono, HRV, peso,
Body Battery, SpO2), e **treinos planejados** (workouts estruturados →
relógio/Edge).

**Como conectar:**
1. Intervals.icu → **Settings → Integrations → Garmin Connect → Connect**
2. Autoriza via **OAuth** na garmin.com (mesmo e-mail do Garmin Connect)
3. Confira que os **scopes** incluem **Wellness** e **Sleep** (Settings →
   Integrations → Garmin Connect → Scopes); se não, **reconecte** com o
   conjunto completo
4. No **Garmin Connect** → Conta → Apps conectados → **intervals.icu** com
   todas as permissões de dados ativas

**Histórico antigo:** use **"Import All Garmin Data"** (Settings → Connections
→ Garmin). Se faltarem treinos específicos após a importação histórica,
exporte os FITs do Garmin Connect e suba manualmente pelo Intervals
(não envie o ZIP gigante direto: use o link de download do e-mail do Garmin).

**Notas:**
- A conexão pode "dormir" após longos períodos sem uso — use **"Download old
  data"** para reativar.
- Trocar a senha do Garmin invalida a conexão (reconecte).
- Nem todo relógio aceita treinos estruturados (ex.: Forerunner 235 não;
  FR255/265/955/965, Fenix 6/7/8, Epix 2, Venu 3, Edge 530+ sim).
- **Wellness depende do hardware do relógio**: HRV noturno exige Elevate Gen
  3+ (FR255/FR955/Fenix 7+); SpO2 exige sensor Pulse Ox (FR245/FR945+).
  Ex.: Forerunner 935 → RHR/sono/Body Battery SIM; HRV/SpO2 NÃO.

---

## 2. Zwift

**O que sincroniza:** atividades concluídas (rides virtuais) + **treinos
planejados** (workouts da semana aparecem no app Zwift, em *Workouts →
Custom → intervals.icu*).

**Como conectar:**
1. Settings → Connections → **Zwift → Connect** (login na conta Zwift
   correta, aceite as permissões)
2. Opcional: escolha quais tipos de atividade baixar / quais workouts enviar

**Notas:**
- Só funciona com a **conexão direta** — um ride do Zwift gravado via
   Garmin/Wahoo não vira atividade "Zwift" no Intervals (vem como atividade
   do respectivo aparelho; pode duplicar se as duas fontes estiverem ativas).
- Ideal para quem treina no Zwift: mantenha Zwift + só uma fonte de backup
   (ou desative download do Zwift se o Garmin já puxa os rides).

---

## 3. Wahoo (ELEMNT / SYSTM)

**O que sincroniza:** atividades + treinos planejados (7 dias seguintes
vão para o Wahoo Cloud → ELEMNT).

**Como conectar:**
1. Settings → Connections → **Wahoo → Connect**
2. Atenção: são **2 checkboxes independentes** — "download activities" e
   "upload planned workouts". Marque os dois (é comum ativar só um e
   estranhar o outro não funcionar).

---

## 4. COROS

**O que sincroniza:** atividades + wellness + treinos planejados.

**Como conectar:** Settings → Connections → **COROS → Connect** (OAuth).
Reconexão pode ser necessária após atualizações grandes do app COROS.

---

## 5. Suunto

**O que sincroniza:** atividades + wellness + treinos planejados (ao relógio).

**Como conectar:** Settings → Connections → **Suunto → Connect** (OAuth).
Rides sem potência funcionam; a precisão de alguns campos de wellness varia
por modelo.

---

## 6. Polar Flow

**O que sincroniza:** atividades + wellness (sono, HRV, FC repouso) — mas
**NÃO envia treinos planejados** (limitação do lado da Polar, não do
Intervals).

**Como conectar:** Settings → Connections → **Polar → Connect** (OAuth).

**Treinos no relógio Polar:** exporte o workout como FIT no Intervals e
carregue manualmente no Polar Flow (ou use o cartão de treino se o modelo
suportar).

---

## 7. Strava

**O que sincroniza:** atividades (import). **Não** envia treinos planejados.

**Como conectar:** Settings → Connections → **Strava → Connect** (OAuth).

**Notas (importante):**
- **Duplicatas**: se Strava + outra fonte (Garmin/Zwift) importam o mesmo
  treino, o auto-match pode falhar e aparecer 2 entradas. Recomendação
  oficial: **deixe apenas uma fonte de download** (a original). Use o
  filtro de tipos se quiser só alguns tipos do Strava.
- A conexão pode **"dormir"** sem uso recente: use **"Download old data"**.
- Histórico: o Strava limita download histórico para não-supporter; use o
  **link de exportação** do e-mail do Strava para importar o histórico
  completo.

---

## 8. Amazfit

**O que sincroniza:** atividades + wellness + treinos planejados (alguns
modelos).

**Como conectar:** Settings → Connections → **Amazfit → Connect** (OAuth).

**Notas:** nem todos os modelos recebem workouts estruturados; verifique o
modelo na documentação.

---

## 9. Huawei Health

**O que sincroniza:** atividades (parcial) + wellness. **Limitações que
dependem de modelo/região:** profundidade do histórico, detalhes de voltas,
e envio de treinos planejados são limitados (às vezes indisponíveis).

**Como conectar:** Settings → Connections → **Huawei → Connect**.

---

## 10. Dropbox (uploads manuais)

**O que sincroniza:** arquivos **FIT/TCX/GPX** colocados numa pasta do
Dropbox são importados automaticamente como atividades.

**Como conectar:** Settings → Connections → **Dropbox → Connect** → autorize
e veja qual pasta usar.

**Uso típico:** pedais outdoor de aparelhos sem integração nativa, ou upload
manual de arquivos exportados (Garmin export, Strava export etc.).

---

## 11. Oura / WHOOP (wellness apenas)

**O que sincroniza:** sono, HRV, readiness, temperatura etc. (só wellness —
não importam atividades).

**Como conectar:** Settings → Connections → **Oura** (ou **WHOOP**) → Connect.

**Dica de duplicidade:** se você tiver várias fontes de wellness (ex.: Garmin
+ Oura), configure no Intervals **quais campos vêm de cada fonte** (Settings
→ Connections → fonte → seleção de campos). Quem atualiza por último
sobrescreve — evite manter o mesmo campo em 2 fontes.

---

## 12. Apple Watch / Apple Health

**O que sincroniza:** atividades + wellness, **via ponte** — o Intervals.icu
não tem conexão nativa com a Apple.

**Opções:**
- **HealthFit** (iOS): envia atividades e wellness do Apple Watch para o
  Intervals.icu;
- **RunGap** (iOS): alternativa semelhante;
- App móvel do Intervals.icu / terceiros compatíveis.

---

## Regras de ouro (vale para todas)

1. **Uma fonte de atividades por treino** — evite duplicatas. Prefira a fonte
   direta (Garmin/COROS/Suunto/Polar) e desative o download do Strava se ele
   for redundante.
2. **Wellness**: monte a matriz de fontes no Intervals (quem manda peso, quem
   manda sono, quem manda HRV) e **não deixe 2 fontes no mesmo campo**.
3. Conexões paradas por muito tempo **"dormem"** — use *Download old data*
   para acordá-las.
4. Troca de senha em qualquer plataforma → **reconecte** a integração.
5. Importação de histórico: use os links oficiais de exportação (Garmin /
   Strava), nunca suba ZIPs gigantes arbitrários.
6. **Treinos planejados** só saem para: Garmin, Wahoo, Zwift, COROS, Suunto,
   Amazfit (alguns modelos). Para Polar/outros, exporte FIT manual.

---

## Aplicação ao hermes-coach

O hermes-coach usa a **API do Intervals.icu** (não as integrações acima
diretamente). Ou seja: conectar as plataformas no painel do Intervals é o
**pré-requisito** para o hermes ter dados (eventos, atividades, wellness).
Depois de sincronizadas, o fluxo normal continua igual:

```
Plataformas (Garmin/Zwift/...) ──sync──▶ Intervals.icu ──API──▶ hermes-coach
                                    (Settings→Connections)   (reconcile/push)
```

Estado da conta do atleta (2026-09-19): Garmin Connect conectado com
atividades + estatísticas diárias de saúde + dados históricos; wellness
parcial (RHR/sono chegam; HRV/SpO2 não — hardware FR935; peso manual).
Ver [issue #4](https://github.com/valdelin/Hermes-coach/issues/4).