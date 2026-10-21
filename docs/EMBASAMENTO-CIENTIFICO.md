# 🧬 Embasamento Científico do Algoritmo — Hermes Coach

> [!info] Dono deste documento
> Fonte canônica: `docs/EMBASAMENTO-CIENTIFICO.md` **no repo** (o mesmo arquivo
> do vault é cópia). Quando divergirem, o repo vence. Editar no repo e copiar.
> Espelho: `~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/EMBASAMENTO-CIENTIFICO.md`.

**Data:** 25/09/2026 · atualizado 15/10/2026
**Projeto:** Hermes Coach
**Mapeamento:** Fisiologia do Exercício aplicada ao Algoritmo de Treino

## Como ler este documento

Toda afirmação relevante carrega uma classificação. A distinção é o ponto:
o motor **não** é fisiologia, e apresentar heurística como mecanismo é o modo
mais fácil de este projeto mentir para quem o lê.

| Classificação | Significado |
| --- | --- |
| **EVIDÊNCIA CIENTÍFICA** | Achado de literatura com fonte verificável. Não implica que o motor o reproduza. |
| **HEURÍSTICA DO SISTEMA** | Convenção do Hermes, configurável e contestável. Sem lastro fisiológico necessário. |
| **MODELO COMPUTACIONAL** | Aproximação numérica interna. Não é medição. |

**Sobre superlativos.** Não há "melhor", "ideal" ou "ótimo" sem base
comparativa. Onde a literatura não encontrou superioridade, o texto diz **não há
evidência suficiente** e aponta a heterogeneidade.

---

## Índice

1. [Princípios](#1-princípios) · 2. [FTP](#2-ftp) · [FTP, eFTP e modelos Power-Duration](#21-ftp-eftp-e-modelos-power-duration) · [Inatividade, reteste e preparação](#22-inatividade-reteste-e-preparação-para-teste-de-ftp) · 3. [Critical Power e W'](#3-critical-power-e-w) ·
4. [Zonas](#4-zonas) · 5. [Periodização](#5-periodização) ·
6. [Distribuição de intensidade](#6-distribuição-de-intensidade) ·
7. [Training Load](#7-training-load) · 8. [CTL / ATL / TSB](#8-ctl--atl--tsb) ·
9. [Readiness](#9-readiness) · 10. [Adaptation State](#10-adaptation-state) ·
11. [Progression Engine](#11-progression-engine) · 12. [VO2max](#12-vo2max) ·
13. [Recovery / Deload](#13-recovery--deload) · 14. [Limitações](#14-limitações) ·
15. [Referências](#15-referências)

---

## 1. Princípios

**HEURÍSTICA DO SISTEMA.** O Hermes não aplica ajustes arbitrários: a agenda, a
redução por faltas, a compensação de intensidade e a estrutura de blocos seguem
regras explícitas, todas localizáveis em `src/`. Onde uma regra é convenção
nossa, ela está rotulada como heurística — não como fisiologia.

**EVIDÊNCIA CIENTÍFICA.** A base é o princípio da carga e recuperação e o
modelo fitness-fadiga de Banister (1991). Banister é a **origem do modelo**,
não uma validação das constantes do Hermes: `0,95` no cap diário e o
`-15` de TSB são do sistema.

**Distinção estrutural: periodização ≠ autoregulação.** `GOAL` e a
proximidade da prova definem fase e alvo semanal. `TrainingPlanState` mantém
goal, fase, semanas, cargas, TSB e readiness, mas **TSB não troca fase nem
template semanal**. TSB < −15 ou readiness desfavorável adaptam somente a
primeira sessão de qualidade — com a diferença de que TSB < −15 e o alerta de
possível doença trocam a sessão por uma prescrição leve, enquanto prontidão
YELLOW apenas **reduz volume** preservando `focus` e zona (ver §9.1). Galán-Rioja et al. (2023) contextualizam
periodização, distribuição e volume; a separação em camadas é decisão
arquitetural, não afirmação de que limites de TSB determinem universalmente a
fase fisiológica.

**Nomenclatura: constantes renomeadas, valores preservados.** As constantes
seguem a nomenclatura da tabela (`FOCUS_ZONE2_ENDURANCE`). Os **valores string**
(`"zone2"`, `"threshold"`, `"vo2max"`) não mudam, e é deliberado: são
persistidos em `plan.json` e publicados no Intervals.icu — renomeá-los quebraria
planos salvos e eventos já publicados. `test_valores_string_dos_focos_nao_mudaram`
trava essa compatibilidade.

## 2. FTP

**EVIDÊNCIA CIENTÍFICA.** O teste FTP20 (20 min autocronometrado × 0,95) foi
descrito como **confiável** numa revisão de escopo de 15 estudos. A mesma
revisão registra que os estudos que comparam FTP20 com outros marcadores
fisiológicos relatam **limites de concordância amplos**, e conclui que os
parâmetros não são intercambiáveis. A literatura é limitada e a amostra é
majoritariamente masculina treinada (PMID 34304689).

**EVIDÊNCIA CIENTÍFICA — FTP não equivale a marcadores fisiológicos.**

- FTP correlaciona-se fortemente com a potência associada a lactato 4,0 mmol/L
  (r = 0,88; p < 0,001) e não difere significativamente dela em média — mas o viés
  médio foi 2,9 ± 24,6 W com limites de concordância de **−45 a +51 W**, o que
  **refuta equivalência**. LT, IAT, e LT por Dmax e Dmax modificado diferiram
  significativamente de FTP (todos p < 0,05) (PMID 31269000).
- A potência em MLSS foi **88,5% do FTP** (DP 4,8%) e **93,1% do FTP95%**
  (DP 5,1%), ambas diferentes de FTP95% (p < 0,001). MLSS respondeu ao treino
  (+12 ± 8 W; p = 0,002) enquanto FTP20 e FTP95% não responderam (p = 0,75) —
  95% do FTP é um substituto ruim para MLSS, e os autores registram que a alta
  variabilidade desaconselha trocar 95% por 88% (PMID 31689684).
- A potência no FTP foi maior que no limiar ventilatório (p < 0,001), e FTP e
  RCP tiveram correlação muito alta (r 0,71–0,90 em W; 0,79–0,93 em W/kg) com
  viés médio não significativo — com o alerta explícito de não usar os dois
  conceitos indistintamente (PMID 33728842).

**Consequência no motor.** `AthletePhysiologicalProfile` (`src/athlete_profile.py`)
preserva FTP e sua fonte/confiança (`FtpSource`, `FtpConfidence`) separadamente
de CP, W′, VO2max e marcadores de FC, todos opcionais. **O motor não infere
marcador ausente a partir de FTP.** FTP é referência operacional de potência.

### 2.1 FTP, eFTP e modelos Power-Duration

Esta seção distingue **INTERVALS_OFFICIAL** (fonte oficial do provider),
**SCIENTIFIC_MODEL** (literatura científica) e **INFERENCE** (não confirmada).
O eFTP é um estimate do provider; o FTP canônico Hermes é um valor confirmado
explicitamente pelo usuário.

#### Intervals.icu: o que é documentado

**INTERVALS_OFFICIAL — alta confiança.** David, mantenedor do Intervals.icu,
descreve o eFTP a partir de um esforço máximo: o serviço encontra a curva Morton
3P mais próxima, com parâmetros CP, W′ e pMax, e usa a potência dessa curva em
1 h como FTP estimado. A calibração usou milhares de curvas reais fornecidas por
FastFitness.Tips e os primeiros 20 min de cada curva. O autor caracteriza a
decisão como pragmática para zonas e acompanhamento, não validação fisiológica
universal [37].

**INTERVALS_OFFICIAL — alta confiança.** O eFTP contínuo é calculado atividade a
atividade, apenas com os dados daquela atividade. Um esforço máximo longo pode
gerar novo eFTP; se o estimate for menor que o eFTP corrente, este é mantido; o
serviço também declara decay quando a carga de treino diminui. Coeficientes, taxa
e função desse decay não foram publicados [38]. Isso atualiza o **eFTP do
provider**, não confirma FTP canônico Hermes.

**INTERVALS_OFFICIAL — confiança média.** Texto de interface reproduzido por
usuário afirma modelo Morton 3P, curvas FastFitness.Tips, esforço máximo entre
180 s e 30 min e duração mínima configurável [39]. Como não é especificação do
mantenedor, essa faixa é evidência operacional, não regra atemporal do Hermes.

Não foram encontradas especificações oficiais completas de coeficientes,
transformações, seleção de esforços/curvas, outliers ou decay. **INFERENCE:** as
fontes permitem descrever o workflow, mas não reproduzir a fórmula integral do
eFTP. Também não há evidência de que o eFTP Intervals use o modelo de Riegel.

| Campo/recurso Intervals | Significado conhecido | Semântica temporal conhecida | Uso Hermes |
| --- | --- | --- | --- |
| `activity.icu_pm_ftp` | eFTP da atividade, derivado do power model/best effort [40][41] | activity-specific; imutabilidade/effective dating não documentados | evidência `ACTIVITY_SPECIFIC_PROVIDER_DERIVED_ESTIMATE` |
| `activity.icu_ftp` | “User captured FTP”; usado no cálculo de intensidade [40] | snapshot existe; garantia histórica não encontrada | dado provider, não histórico Hermes |
| `icu_pm_ftp_secs`, `icu_pm_ftp_watts` | campos declarados pelo provider [42] | significado preciso não documentado nas fontes consultadas | não inferir duração/potência |
| `icu_rolling_ftp`, `icu_rolling_ftp_delta` | campos declarados pelo provider [42] | método e tempo não documentados | não usar como referência |
| `SportSettings.ftp`, `SportSettings.indoor_ftp` | configurações FTP por esporte [42] | settings atuais; sem effective dating documentado | configuração provider, não histórica |
| `FTP_UP` / eFTP contínuo | provider pode elevar eFTP e avisar [38] | não documenta confirmação humana | Advice/evidência, nunca update canônico |

#### Modelos científicos: CP, W′ e duração-potência

**SCIENTIFIC_MODEL — alta confiança.** No modelo hiperbólico clássico de dois
parâmetros, a potência média sustentável por duração $t$ é
$P(t) = CP + W'/t$. CP é a assíntota do modelo potência-duração; W′ é a capacidade
finita de trabalho acima de CP no modelo. Eles não são sinônimos automáticos de
FTP, MLSS, IAT ou RCP [23][25].

**SCIENTIFIC_MODEL — alta confiança.** O modelo Morton 3P introduz o componente
associado à potência máxima/pMax para tratar a região de duração curta e altera as
estimativas de CP e capacidade de trabalho frente ao modelo de dois parâmetros
[34]. O estudo sustenta o modelo citado pelo Intervals, não revela sua implementação
interna. Morton 3P, o modelo CP clássico/Monod--Scherrer e Riegel são modelos
distintos; este documento não atribui Riegel ao eFTP.

Seleção de esforços, faixa de durações e parametrização mudam CP e W′ estimados
[29][30]. Assim, CP/W′ são estimates científicos úteis, mas não substituem FTP
canônico automaticamente.

#### FTP20, comparabilidade e confirmação

**SCIENTIFIC_MODEL — alta confiança.** O protocolo prático FTP20 estima
$FTP_{est} = 0{,}95 \times P_{20}$, em que $P_{20}$ é a potência média de 20 min.
A revisão de escopo encontrou confiabilidade em parte da literatura, mas limites
de concordância amplos entre marcadores [10]. Repetibilidade não demonstra
equivalência fisiológica individual. FTP20, FTP60 e IAT podem ter viés médio
pequeno, mas não são intercambiáveis no indivíduo [35]; associação forte com MLSS
também não os torna idênticos [36]. Aquecimento e pacing alteram o resultado do
TT20 [43].

| Método | Entrada | Saída | Natureza | Cria FTP canônico automaticamente? |
| --- | --- | --- | --- | --- |
| FTP confirmado pelo usuário/treinador | valor explícito | `FtpReference` | fato/state Hermes | não; a confirmação é a criação |
| teste formal ou resultado externo | protocolo e resultado | evidência para confirmação | evidência | não |
| FTP20 x 0,95 | TT20 | estimate operacional | heurística/protocolo | não |
| eFTP / `activity.icu_pm_ftp` | esforço + modelo provider | estimate provider | `INTERVALS_OFFICIAL` | não |
| best20 / `ftp_scan` | stream/atividade | estimate Hermes | evidência derivada | não |
| CP/W′ | esforços duração-potência | parâmetros estimados | modelo científico | não |
| `DEFAULT_FTP` | constante | fallback | engenharia Hermes | não |

#### Contrato Hermes

**DECISÃO DE PRODUTO/ENGENHARIA HERMES.** `FTP_CANONICAL` é exclusivamente um
valor confirmado pelo usuário. O fluxo permitido é:

```text
provider estimate, teste ou algoritmo -> FtpEvidence -> Advice/suggestion
-> confirmação explícita do usuário -> FtpReference -> FTP canonical Hermes
```

`FtpEvidence` pode registrar watts, método, source, `observed_at`, atividade,
provider e contexto, mas não é `FtpReference`. Resultado externo, inclusive
Zwift, só pode tornar-se canônico após confirmação; Hermes não pressupõe seu
método interno. Com FTP `UNKNOWN`, sugerir teste ou entrada explícita é policy de
produto, não conclusão automática de paper. Esse contrato impede que estimate,
best effort, CP/W′ ou `DEFAULT_FTP` reescreva a referência canônica.

### 2.2 Inatividade, reteste e preparação para teste de FTP

**EVIDÊNCIA CIENTÍFICA.** Destreino não tem uma taxa única nem um limiar
fisiológico universal: depende de cessação total versus redução parcial,
treinamento anterior e variável medida. Em atletas de endurance, a revisão de
Barbieri et al. classifica destreino de curto prazo como até quatro semanas e de
longo prazo como mais de quatro semanas; a mesma revisão relata redução de
VO₂max após 12 dias de interrupção em corredores e ciclistas [44]. A meta-análise
de Zheng et al. encontrou queda significativa de VO₂max tanto antes quanto após
30 dias de cessação, maior no grupo de longo prazo [45]. Esses achados dizem
respeito a capacidade aeróbica e desempenho; **não demonstram que FTP caia em
uma proporção fixa nem definem uma duração universal de preparação para teste**.

**HEURÍSTICA DO SISTEMA — protocolo futuro de reteste.** Para evitar tratar um
atleta potencialmente destreinado como pronto para esforço máximo, o Hermes
classificará a recência a partir de atividades de ciclismo **observadas**, nunca
de sessões apenas planejadas em `plan.json`:

| Tempo consecutivo sem atividade observada | Estado Hermes | Conduta de teste/FTP |
| --- | --- | --- |
| 0–13 dias | `ACTIVE` | resultado válido de teste pode seguir a policy normal de atualização |
| 14–27 dias | `REDUCED_RECENCY` | mostrar cautela; ainda não é destreino prolongado pela policy |
| ≥28 dias | `DETRAINED` | criar uma semana de reintrodução antes de sugerir ou agendar teste máximo; não atualizar FTP automaticamente nesse intervalo |
| dados de atividades ausentes ou sem recência verificável | `UNKNOWN` | não presumir continuidade de treino; exigir decisão humana |

Os 28 dias operacionalizam o corte de quatro semanas usado nas revisões, mas são
uma convenção de produto, não um diagnóstico. A semana de reintrodução também é
heurística de segurança operacional para retornar ao esforço máximo: não é uma
alegação de que sete dias restaurem FTP, VO₂max ou qualquer limiar fisiológico.
Quando implementado, o catálogo de protocolos deverá oferecer alternativas
independentes de plataforma; o atleta escolhe o protocolo, e o agendamento só
vira publicação no calendário pelo fluxo explícito de `push` já existente.

## 3. Critical Power e W'

**EVIDÊNCIA CIENTÍFICA.** O modelo de dois parâmetros interpreta a relação
potência-duração, com CP como a taxa associada ao estado aeróbico máximo e W′
como a quantidade de trabalho tolerável acima de CP sem recuperação. Protocolos
de 3 min e rampa *all-out* fornecem medidas válidas em um único teste, além
dos testes de taxa constante distribuídos em vários dias (PMID 32899777).

**MODELO COMPUTACIONAL.** `CriticalPowerProfile` (`src/critical_power.py`) guarda
`critical_power`, `w_prime`, `protocol`, `confidence` e `test_dates`.
`estimate_cp()` e `estimate_w_prime()` ajustam $P = CP + W'/t$ por mínimos
quadrados e devolvem `None` com menos de dois esforços válidos — **nunca um valor
inventado**. `work_above_cp()` limita o esforço acima de CP pelo W′ disponível.

**Limite conhecido do estimador.** O ajuste é OLS de $P$ contra $1/t$, sem
ponderação por duração nem filtro de outlier. Durações curtas têm maior
alavancagem no espaço transformado, e a faixa de durações observada influencia
o intercepto. Não há evidência suficiente no Hermes para declarar WLS, regressão
robusta ou outro modelo universalmente superior.

Não há ponderação por duração nem filtro de outlier no ajuste. Um único ponto
ruidoso desloca a leitura de CP. Travas em
`test_critical_power.py::test_um_esforco_muito_curto_ou_muito_longo_muda_cp` e
`::test_ruido_no_esforco_desvia_a_estimativa`. Consequência prática: o CP
estimado é honesto dentro da faixa de durações realmente medida, e extrapolar
para o assíntoto com poucos pontos é chute.

**HEURÍSTICA DO SISTEMA.** O ritmo padrão de reconstituição de W′ (0,1 W/s) é
convenção do Hermes, configurável por atleta, **não constante fisiológica
universal**. Idem para qualquer limiar de W′ do código.

**CP e W′ são complementares ao FTP:** não o substituem e não são equivalentes
a MLSS, LT ou RCP. O uso atual é analítico e informativo: estimativa,
proveniência, metadados, métricas de ajuste e estudo da relação potência-duração.
Não há plano atual para uso prescritivo em esforços acima do limiar, Z6 ou HIIT.

### 3.1 Validade e confiabilidade das estimativas de CP e W′

**[EVIDÊNCIA CIENTÍFICA]** O modelo potência-duração exige que os esforços
observados sustentem a relação que se quer estimar. Protocolos publicados usam
múltiplos esforços e diferentes durações, mas não oferecem um único threshold
universal de quantidade, amplitude de duração, R² ou RMSE que possa classificar
todo atleta e protocolo (PMID 32899777; PMID 20195180; PMID 30387374;
PMID 34708276). Logo, ajuste estatístico e qualidade dos dados não são a mesma
coisa: um R² alto, em especial com dois pontos, não demonstra por si só uma
estimativa fisiologicamente robusta.

**[EVIDÊNCIA CIENTÍFICA]** CP e W′ têm incertezas distintas; W′ tende a ser
mais variável entre protocolos e repetições. FTP e CP podem se associar numa
população, mas não são intercambiáveis no indivíduo (PMID 33551839; PMID
34304689). A reconstituição de W′/W′bal acrescenta hipóteses próprias e não
decorre automaticamente de uma estimativa de CP/W′ válida.

**[ENGENHARIA HERMES]** A Fase 2 registra metadados objetivos dos esforços
aceitos pelo modelo (`n_efforts`, duração mínima, máxima e amplitude) e métricas
de ajuste no espaço $x=1/t$, $y=P$ (`fit_r2`, `fit_rmse` em watts). Isso não
cria `power_duration_coverage`, `fit_condition_warn` ou score composto: ainda
não há critério defensável para transformar esses conceitos em thresholds
automáticos.

**[ENGENHARIA HERMES]** Hard Validation (reta solucionável), Data Quality
(descrição dos dados), Fit Quality (resíduos do modelo) e Confidence
(interpretação informativa) permanecem separados. Nesta fase, todo perfil válido
recebe `LOW` para CP e W′, inclusive três ou mais esforços; dois pontos distintos
também recebem `LOW`, mesmo quando $R^2=1$ e RMSE=0. `MEDIUM` e `HIGH` são
estados representáveis, mas não são derivados sem uma política futura
defensável. Os campos `cp_confidence` e `w_prime_confidence` são separados para
permitir incertezas distintas, sem inferir uma diferença artificial agora.

**[ENGENHARIA HERMES]** FTP continua baseline operacional universal para zonas,
`WorkoutParams`, potência-alvo, prescrição e publicação. CP/W′ continuam
opcionais, analíticos e exclusivamente informativos. Não há
`eligible_for_enhancement`, `eligible_for_prescription`, ativação automática,
fallback `cp = ftp`, consumidor prescritivo, nem alteração de zonas, TSS, VO2,
INTENSITY, work_sec, repeats ou recovery. W′bal e sua reconstituição são
heurísticos/experimentais; não há decisão de usá-los como restrição, gate ou
fonte de prescrição. A Fase 2 está concluída por si só; Fase 3 não tem roadmap
ativo e uso produtivo não é planejado no momento.

## 4. Zonas

**MODELO COMPUTACIONAL (invariante verificável).** As faixas por zona não são
apenas documentação: `ZONE_BANDS` (`src/coach.py`) carrega pisos e tetos de %FTP,
e `ZoneIntegrityTest` (`tests/test_plan.py`) fixa esses valores como regressão —
alterar as faixas **falha a suíte**. O teste compara o dicionário contra um
literal codificado nele próprio; ele não lê este documento nem qualquer markdown.

```python
ZONE_BANDS = {
    FOCUS_ZONE1_RECOVERY:    (0.00, 0.55),   # Z1 Recuperação   <55%
    FOCUS_ZONE2_ENDURANCE:   (0.56, 0.75),   # Z2 Endurance   56–75%
    FOCUS_ZONE3_TEMPO:       (0.76, 0.90),   # Z3 Tempo       76–90%
    ZONE_SWEETSPOT:          (0.84, 0.97),   # Sweet Spot     84–97%
    FOCUS_ZONE4_LIMIAR:      (0.91, 1.05),   # Z4 Limiar      91–105%
    FOCUS_ZONE5_VO2MAX:      (1.06, 1.20),   # Z5 VO₂máx      106–120%
    FOCUS_ZONE6_ANAEROBICA:  (1.21, 1.50),   # Z6 Anaeróbica 121–150%
}
```

Helpers: `zone_floor(focus)`, `zone_ceiling(focus)`, `zone_band(focus)` e
`focus_zone(focus)` — aceitam tanto o foco de prescrição (`'sweetspot'`) quanto
a zona canônica (`'Z4 Limiar'`). Verificação: varredura de 2.000 treinos gerados
(5 TSB × 4 FTP × 5 `weekly_hours`) com **0 violações de zona**.

### Quatro decisões que a tabela impõe ao motor

**1. Todas as zonas têm faixa, mas nem todas têm foco prescrito.** `ZONE_BANDS`
cobre Z1–Z6; em `FOCUS_ZONE` existem só os focos prescritos hoje (Z2, Sweet
Spot, Z4, Z5). Z1, Z3 e Z6 têm faixa declarada **sem** template que as gere —
estão no dicionário para tornar a tabela completa e verificável, não para
sugerir que sejam prescritas. Um teste trava essa separação.

**2. Z7 está fora de `ZONE_BANDS` — deliberadamente.** A tabela o descreve como
**potência máxima**, não como faixa de %FTP: a potência máxima pode ser várias
vezes o FTP. Como `ZONE_BANDS` é um modelo de *faixa de %FTP*, não há o que
colocar entre 1,21 e ∞. A ausência é intencional, tem comentário no código e um
teste que verifica que nada `z7` entra.

**3. Active recovery é uma sessão dentro de Z2, não um foco Z1.** A tabela
define Z1 como `<55%`, mas o *active recovery* do motor é executado a **≈0,60** —
dentro da banda **Z2**. Não é arredondamento: a **zona** descreve o estímulo
fisiológico, enquanto *active recovery* descreve a **intenção da sessão**
(descarregar, circular). Logo Z1 é uma **intenção de sessão** dentro da banda Z2,
sem foco próprio. Consequência: `_is_active_recovery()` classifica por
`focus == zone2` **e** `on_power ≤ 0,65`, e o `reconcile` nunca compensa um active
recovery perdido.

**MODELO COMPUTACIONAL.** `ACTIVE_RECOVERY_DAYS` pode marcar um subconjunto de
`TRAINING_DAYS` como recuperação ativa recorrente. O motor gera Z2 a 60% do FTP,
mantém `focus="zone2"` e não compensa uma ausência. Dias de proteção de prova ou
teste FTP prevalecem sobre essa preferência. A agenda é uma escolha de produto e
disponibilidade, não uma conclusão fisiológica universal.

**4. Um foco de prescrição pode ser servido por mais de uma zona.**

```python
FOCUS_ZONE = {
    "zone2":     FOCUS_ZONE2_ENDURANCE,
    "endurance": FOCUS_ZONE2_ENDURANCE,   # mesma zona, outra template
    "sweetspot": ZONE_SWEETSPOT,          # categoria, não zona numerada
    "threshold": FOCUS_ZONE4_LIMIAR,
    "vo2max":    FOCUS_ZONE5_VO2MAX,
}
```

`zone2` e `endurance` são **ambos Z2** — duas templates distintas na mesma zona.
E `sweetspot` é **categoria de prescrição** (sobrepõe final de Z3 e início de
Z4), não um número de zona.

### Intenção e dose: as famílias se sobrepõem

**EVIDÊNCIA CIENTÍFICA.** As bandas se cruzam: `sweetspot` (84–97%) e
`threshold` (91–105%) compartilham **91–97% FTP**. Nessa faixa a potência **não
distingue** as duas famílias, e é por isso que a diferenciação é por intenção e
dose (`src/zone_intent.py`), não por %FTP. `classify()` levanta
`AmbiguousIntensity` nessa faixa em vez de escolher pelo número.

| Família | Intenção | Dose | Forma | Alavancas de progressão |
| --- | --- | --- | --- | --- |
| Z2 Endurance | Sustentar blocos contínuos e treinos longos; construir base aeróbica e capacidade de *eload* | Contínuo, 30 min–4 h, sem lacunas internas | `CONTINUOUS` | duração, volume total |
| Sweet Spot | Alta densidade de estímulo com fadiga administrável, sobre o final de Z3 e o início de Z4 | Blocos de 8–30 min, com folga para sustentar a repetição | `INTERVAL` | duração, volume total |
| Z4 Limiar | Elevar a potência de limiar e a depreciação de lactato em esforço máximo sustentável | Blocos de 5–20 min, recuperação 2:1 a 4:1 | `INTERVAL` | duração, repetições, recuperação |

**HEURÍSTICA DO SISTEMA.** **Z2 não usa intervalos artificiais.** Fragmentar o
volume em pedaços para trabalhar "mais forte" quebra o que sustenta a base sem
acrescentar estímulo específico. **Sweet Spot é faixa de prescrição**, não zona
fisiológica universal: existe justamente por sobrepor Z3/Z4, e não equivale a
limiar fisiológico. **Não afirme que 95% FTP = MLSS** (ver seção 2).

### Redução hierárquica quando o orçamento aperta

**HEURÍSTICA DO SISTEMA.** A ordem é: (1) corta `repeats`; (2) encurta `on_sec`;
(3) encurta `off_sec`; (4) só então reduz `on_power`, **nunca abaixo do piso da
zona**. Sem caber sem sair da zona, o código **prefere estourar o teto semanal a
rebaixar o estímulo**.

**Justificativa.** Um treino de limiar rebaixado vira um treino de endurance
*travestido* de limiar: o nome mente e a adaptação esperada (acima do LT1) não
acontece. Bug real corrigido em v0.0.30: `2026-10-02` estava com
`focus=sweetspot @ 0,55` — 55% é estímulo de recuperação com o nome de Sweet
Spot intacto. Cortar volume antes de cortar intensidade é mais conservador e é
decisão do sistema, não achado de literatura.

## 5. Periodização

**MODELO COMPUTACIONAL.** `TrainingPhaseEngine` (`src/training_phase.py`)
explicita `BASE`, `BUILD`, `SPECIFIC`, `PEAK`, `RECOVERY` e `TEST`, cada uma com
objetivo, duração configurável, estímulos, limites de carga e critérios de
progressão, deload e saída. **As transições são regras de plano; a ordem não
representa uma sequência fisiológica universal.**

**EVIDÊNCIA CIENTÍFICA.** Não há evidência atual a favor de um modelo de
periodização específico em 8–12 semanas em ciclistas de estrada treinados, e
poucos estudos examinaram o impacto sazonal de forma sistemática (Galán-Rioja
et al., 2023; PMID 36640771). A revisão encontrou blocos de 1–8 semanas na
periodização por blocos, volume de 8,75–11,68 h/semana, e volume de 7,5–10,76
h/semana na periodização tradicional, com TID piramidal ou polarizada.

**MODELO COMPUTACIONAL.** A agenda é **configurável** (`TRAINING_DAYS` no
`.env`; padrão `seg,ter,qua,qui,sex`), não fixa. Um treino perdido é
redistribuído para o **próximo dia de treino da agenda**, obedecendo ao teto de
carga — não a uma regra fixa de dias. `cmd_reconcile` /
`_absorb_missed_into_budget`.

## 6. Distribuição de intensidade

**MODELO COMPUTACIONAL.** `IntensityDistributionEngine`
(`src/intensity_distribution.py`) reporta minutos efetivos de baixa, moderada e
alta intensidade, independentemente do número de sessões. `POLARIZED`,
`PYRAMIDAL`, `THRESHOLD_HEAVY` e `CUSTOM` são **modelos de configuração**, sem
pressupor 80/20 universal.

**EVIDÊNCIA CIENTÍFICA — não há modelo superior.** Meta-análise de 41 estudos,
81 grupos de treino e 797 participantes: tanto a abordagem polarizada
quanto a não polarizada melhoraram VO₂max (g = 0,42; IC 95% 0,31–0,53) e
desempenho em contrarrelógio (g = 0,39; IC 95% 0,25–0,53), **sem diferença
significativa entre modalidades** (p > 0,05). Duração de intervenção maior
associou-se a VO₂max (g = 0,03; IC 95% 0,02–0,05). **Nenhuma associação** foi
encontrada entre volume semanal ou total e mudanças em VO₂max ou desempenho. Os
autores concluem que, atingido o volume necessário, aumentos adicionais não
parecem enhancing performance, e recomendam priorizar distribuição efetiva em
vez de volume total ou modelo específico (Cove et al., 2025; PMID 39788807,
DOI 10.1016/j.jsams.2024.12.005).

**Consequência no motor.** A conclusão vale para ciclistas treinados: 41 estudos,
797 ciclistas, sem diferença entre polarizado e não polarizado.

## 7. Training Load

**METODOLOGIA DE INDÚSTRIA — não é evidência fisiológica.** NP, IF e TSS são
definições operacionais de prescrição e quantificação de carga por potência
(Coggan, TrainingPeaks). São largamente usadas e úteis para comparar sessões do
mesmo atleta, mas **não são equivalentes a MLSS, LT, RCP ou Critical Power**.

**MODELO COMPUTACIONAL.** O motor distingue quatro coisas que não podem ser
somadas nem tratadas como sinônimos:

| Campo | Origem | Uso no Hermes |
| --- | --- | --- |
| `power_training_load` | **Executado**: NP, duração e FTP válidos | TSS operacional: `horas × IF² × 100`, com `IF = NP / FTP`. Sem NP, ou em segmento de 30 s ou menos, é desconhecido; o motor não inventa NP para treino curto ou planejado. |
| `estimated_tss` | **Planejado**: blocos em %FTP, duração e recuperação | Orça carga futura para `build`, `reconcile` e forecast. Não representa TSS medido após execução. |
| `external_load` | Trabalho mecânico, distância, elevação ou outro marcador externo, com unidade declarada | Contexto de volume; não é convertido automaticamente para TSS. |
| `internal_load` | FC, RPE, TRIMP ou score de fonte declarada | Contexto de resposta do atleta; não é convertido automaticamente para carga externa. |

> **Limite operacional:** em HIIT curto, o valor depende fortemente de como a NP
> foi calculada, da janela analisada e das recuperações. Não se deve inferir NP
> de potência média nem atribuir precisão fisiológica a um TSS estimado.

## 8. CTL / ATL / TSB

**MODELO COMPUTACIONAL.** `icu_training_load` é a carga autoritativa que o
Intervals.icu expõe para os fluxos atuais de CTL/ATL/TSB. O Hermes a **preserva**
em vez de recalcular o histórico, porque a pipeline interna do Intervals não é
reproduzível apenas por TSS local. O PMC local usa TSS/`icu_training_load`
como entrada de EWMA 42/7 para projeção — **não é medida fisiológica direta**.

**HEURÍSTICA DO SISTEMA.** O teto de TSS de uma janela rolante de 7 dias é
`cap diário × nº de dias de treino × escala do goal` (`weekly_budget()`), com
`cap diário` derivado da carga média **realizada** (`avg_load`, janela
`BUDGET_WINDOW_DAYS = 60`) e multiplicado por 0,95. `build_plan` e `reconcile`
partilham a mesma base, para nunca derivarem tetos diferentes da mesma carga.

O teto funciona como *guardrail*: **não é alvo a atingir**, é o limite que
impede o plano de prescrever mais do que o atleta demonstrou tolerar. A média é
calculada **apenas sobre sessões efetivamente executadas**
(`paired_activity_id` presente) — carga prescrita e não realizada não é
evidência de tolerância.

**MODELO COMPUTACIONAL (PMC-1).** O contrato de leitura expõe também o
**Form relativo**: `form_pct = TSB / CTL × 100`. CTL/ATL/TSB permanecem
**observados** do provider e não são recalculados — o Hermes faz apenas a
divisão. Devolve `None` (nunca 0) quando `CTL` está ausente, `TSB` está
ausente ou `CTL ≤ 0`, porque a razão não é definida. `form_pct` é uma
**representação derivada para leitura**, medida em % do form absoluto; **não é
regra fisiológica, não é limiar de deload e não tem efeito prescritivo**.
Interpretar o valor (ex.: advisory em `-30%`) é tarefa de policy, não do
cálculo. Snapshot velho (`stale`) ainda produz `form_pct`: freshness informa a
idade da fonte, não bloqueia a derivação.

**HEURÍSTICA OPERACIONAL (POL-1).** O threshold default `form_pct ≤ -30%`
produz somente o advisory configurável `high_negative_form`. É um limiar de
sistema para chamar atenção sobre o valor relativo, **não** uma lei fisiológica,
critério diagnóstico, prova de overtraining ou prescrição de deload. A policy
não altera treino, não chama `REDUCE`/`REPLACE` e pode coexistir com uma
heurística de readiness GREEN; resolver sinais discordantes é escopo de policy
composta/advice futuro.

**MODELO COMPUTACIONAL (HR-1).** CTL ramp rate é a diferença de CTL observada
em dois dias exatos: `CTL(D) − CTL(D−7)`, expressa em **pontos de CTL por 7
dias**. O Hermes não recalcula CTL, não interpola gaps e devolve indisponível
quando um ponto não existe no snapshot. O advisory de ramp é opt-in e recebe
seu limite por configuração do consumidor: não há `5–7 pontos/semana` tratado
como limite fisiológico universal. Um delta absoluto também depende do CTL
basal; HR-1 não o normaliza nem prescreve alteração de treino.

**EVIDÊNCIA CIENTÍFICA - cardiovascular drift.** FC pode aumentar durante
exercício prolongado pelo cardiovascular drift; hidratação, hipertermia e
contexto do esforço são confundidores, portanto o sinal não isola aptidão
aeróbica (Coyle, 1998, PMID 9694416; Coyle & Gonzalez-Alonso, 2001, PMID
11337829). Isso não valida qualquer threshold de Pw:HR como fadiga, recuperação
ou necessidade de deload.

**METODOLOGIA COMPUTACIONAL (HR-2).** Hermes escolhe a familia TrainingPeaks:
`EF = Normalized Power / FC média` em cada metade e
`((EF_primeira - EF_segunda) / EF_primeira) * 100`. O maintainer do
Intervals.icu publicou outra convenção, `potência média / FC média`; portanto os
dois produtos não são numericamente equivalentes quando NP diverge da média.
`power` e `heart_rate` são observados pelo provider; a razão e a eligibility são
derivadas pelo Hermes. Para calcular NP sem resampling, a implementação exige
amostras conjuntas, únicas e contíguas de um segundo, divide pelo midpoint de
`elapsed_seconds` e rejeita gaps/duplicatas/missing. Isto é data-quality policy
computacional conservadora, não detector fisiológico de steady aerobic effort.

**LIMITE EXPLÍCITO (HR-2).** STREAM-1/2 normalizam e armazenam os sinais, mas o
boundary não contém pausa, coasting, temperatura, grade, cadence, warm-up,
cooldown ou classificação de esforço estável. Assim, todo valor calculado expõe
`computable=true` e `methodological_context="unverified"`: ele é matematicamente
válido sob a política Hermes, não automaticamente interpretável como aerobic
decoupling. Não existe threshold, advisory, integração com readiness/form/ramp
ou efeito prescritivo nesta fase.

> **Erro corrigido (v0.0.30):** o teto era `cap diário × 7`. Como a média de
> carga é **por dia de treino** (não por dia-calendário), isso concedia 7
> sessões numa semana com `n` dias de treino, inflando o teto em `7/n` (≈1,4×
> com 5 dias). O teto semanal caiu de ~287 para ~220 TSS.

## 9. Readiness

**MODELO COMPUTACIONAL.** `ReadinessAssessment`
(`src/readiness_assessment.py`) combina HRV contra baseline individual,
tendência de RHR, sono, fadiga subjetiva, carga, desempenho opcional e
consistência. `GREEN`/`YELLOW`/`RED` indicam **adequação ao treino, não
diagnóstico**, e um sinal isolado não cancela automaticamente uma sessão.

**SEPARAÇÃO DE CAMADAS (RDY-1).** `ReadinessView` expõe sem misturar: sinais
**observados** (RHR, HRV/SDNN, sono, readiness composto e stress), PMC
**observada** (CTL/ATL/TSB), `form_pct` **derivado** e o resultado
**heurístico** já existente (`GREEN`/`YELLOW`/`RED`, trace e alertas). O objeto
não produz advice, não decide `REDUCE`/`REPLACE` e não altera treino. Esses são
atos de policy/prescrição dos fluxos existentes e de POL-1; a View não afirma
que um threshold seja uma lei fisiológica.

**SEPARAÇÃO DE CAMADAS (HR-4).** `ObservedWellnessView` vai um passo abaixo de
`ReadinessView`: expõe, por conceito de wellness, o **valor observado** que o
provider entrega e o contexto derivado dele (média da janela, delta, nº de
observações, unidade e escala). Termina em observação e tendência. O Hermes
**observa e deriva tendência de Wellness — não diagnostica recuperação**: não há
score composto, não há corte, não há rótulo de bom/ruim e não há direção
assumida. As unidades e escalas que não são contrato documentado ficam
`unknown` em vez de estimada. Interpretação continua sendo policy, em
`readiness.py`, com os limiares que já existiam. Três conceitos do workstream
(`soreness`, `motivation`, `fatigue`) não têm chave no provider e são
entregues como `unsupported_field`: registrar a lacuna é mais honesto que
fabricar um campo para parecer completo. Detalhes e limitações em
`docs/HR-4-SUBJECTIVE-WELLNESS.md`.

**EVIDÊNCIA CIENTÍFICA — efeito modesto e seletivo.** Numa revisão de escopo com
meta-análise de 8 estudos (198 participantes), treino guiado por HRV teve efeito
de tamanho médio sobre parâmetros fisiológicos submáximos (g = 0,296; IC 95%
0,031–0,562; p = 0,028), mas o efeito sobre **desempenho foi pequeno e não
significativo** (g = 0,079; IC 95% −0,050–0,393; p = 0,597) e sobre
V̇O₂*pico* também (g = 0,171; IC 95% −0,213–0,371; p = 0,130). Houve menos
não-respondedores em desempenho com treino por HRV (Düking et al., 2021;
PMID 34489178).

Noutra meta-análise de ECR, treino guiado por HRV e treino de controle
melhoraram ambos o VO₂max (p < 0,0001), com ES significativamente maior para o
grupo HRV (ES = 0,187; p < 0,0001) e efeito pequeno e positivo no desempenho
(ES = 0,402), **condicionado ao nível e ao sexo do atleta** — subgrupos amador e
feminino reportaram resultados melhores e significativos (Granero-Gallegos et
al., 2020; PMID 33143175).

**Consequência no motor.** A evidência justifica usar HRV como **uma entrada
entre várias** e justifica o tratamento de não-respondedores. Não justifica
prometer ganho de VO₂max, nem tratar um único sinal como veredito — o que é
exatamente o que o código faz.

### 9.1 Do readiness ao plano (issue #58, Passo A)

**O que é medido.** `assess_readiness_assessment()`
(`src/readiness.py`) é o produtor: wellness bruto do Intervals →
`(ReadinessAssessment | None, trace)`. O modelo tem **sete eixos**; a pipeline
atual implementa fonte para **três** (`hrv_score`, `rhr_score`, `sleep_score`),
`recent_load_score`, `subjective_fatigue_score`, `performance_score` e
`consistency_score` ficam `None` até terem produtor próprio. Portanto, **3/7
(≈43%) é capacidade máxima da implementação atual**, não cobertura diária.
Na leitura de cada dia, a cobertura disponível é 0..3 conforme os sinais
válidos presentes; ela é exposta separadamente de modelo e implementação.

O `readiness` composto do Intervals também é observado, mas não ocupa um eixo:
deriva de HRV, sono e RHR e duplicaria essas entradas. Ele permanece no trace
como `composite_low`, com o limiar legado `< 60`.

**Ausência não é neutra.** Eixo sem observação permanece `None`, nunca `0.5` ou
o score saudável `0.8`. Preencher ausente rebaixaria ou elevaria artificialmente
a média. `confidence` é reportado como **cobertura** (fração dos sete eixos
observados), não confiança estatística, e **não há piso de cobertura**: um sinal
ruim de fato observado não deve ser descartado por falta de eixos vizinhos.

**Por que o readiness do Intervals não é um sétimo eixo.** Ele é um composto
derivado de HRV, sono e RHR — as mesmas entradas já convertidas em eixo.
Mapeá-lo contaria o mesmo dado duas vezes. Entra como sinal separado
(`composite_low`), com o limiar legado `< 60`, capaz de sustentar `REDUCE`
isolado.

**Escala dos escores.** `saudável → 0.8`, `sinal ligado → 0.2`. **Heurística do
sistema, sem lastro em literatura.** A justificativa é operacional: o limiar
*poor* do modelo (`< 0.4`) fica no meio do intervalo entre eles, então qualquer
outro par é tão arbitrário — e com esse par um sinal ruim isolado **não** vira
RED. `ReadinessAssessment.level()` e `adjustments()` não foram modificados.

**Política (`readiness_decision`).** Precedência da mais restritiva para a
menos, sem regra que desfaça a anterior:

| Condição | Ação |
|---|---|
| alerta de possível doença (RHR 2+ noites **E** HRV caindo) | `REPLACE` |
| `level() == RED` (≥ 3 eixos `< 0.4` **E** média `< 0.5`) | `REPLACE` |
| `level() == YELLOW` | `REDUCE` |
| `composite_low` isolado | `REDUCE` |
| nenhuma | `NONE` |
| sem observação e sem alerta | `NONE`, motivo "dados indisponíveis" |

**O alerta separado.** `_illness()` legado é reutilizado sem alteração. É uma
conjunção observada, não uma média, então vence inclusive com `level()` GREEN e
cobertura baixa — e o `level()` original é preservado no `ReadinessDecision`
para auditoria. O alerta **não** rebaixa `rhr_score`/`hrv_score`: fazer isso
contaria o mesmo dado duas vezes e criaria um RED que o detector nunca pediu.
Sempre nomeado **alerta de possível doença/recuperação comprometida**; ausência
de RHR ou HRV não permite inferir a conjunção.

**Consequência no motor.** Sinal ruim isolado passou de `REPLACE` para
`REDUCE` — deixa de trocar a sessão e passa a cortar volume, preservando `focus`
e intensidade da zona. É a tradução direta de "um sinal isolado não cancela
automaticamente uma sessão", que a evidência acima sustenta.

**Limites declarados.** `REPLACE` mantém Z2 900 s, recurso conservador **de
convenção**, não resposta validada para possível doença — treino leve não é
garantia de adequação para ninguém. `REDUCE` aplica um degrau da escada de
`_fit_budget` (volume antes de intensidade, `on_power` nunca abaixo do piso de
`ZONE_BANDS`); a **magnitude não está calibrada**, e um degrau é escolha de
projeto. O `build` continua exigindo `push` e aprovação explícita para
publicar.

**A redução não pode virar aumento.** `_fit_budget` decide sobre o TSS já
planejado (`recent`), de modo que reduzir um dia devolveria teto aos seguintes.
Medido: reduzir `14/09` de 37 para 27 TSS fazia `18/09` subir de `4x139` para
`5x139`. Um sinal de recuperação de **um dia** não informa capacidade de
absorver carga em outro dia, e a evidência acima não sustenta essa inferência.
Quando uma intervenção de prontidão age, o livro-razão do orçamento recebe o
TSS **pré-intervenção**, de modo que a pressão de orçamento fica idêntica à de
um plano sem prontidão e **nenhum dia sai com carga maior** que a referência.
O teto é guarda-chuva, não meta; ficar abaixo dele é correto. Progressão
continua possível, mas como decisão separada e rastreável — nunca como efeito
colateral da redução.

O razão é **por fonte**: só entra o TSS pré-intervenção quando a prontidão
**dirigiu** a mudança — decisão adaptativa, válida para o dia, e sem REPLACE
forçado por TSB. Uma decisão `NONE` não adapta nada e por isso não pode alterar
o plano; com TSB abaixo do limite quem age é o TSB, e o razão é o dele.

**Horizonte: o sinal vale para o dia que descreve.** `ReadinessDecision`
carrega `applies_to_day`, o dia do último registro de wellness. A intervenção
só ocorre quando o dia do plano é esse dia. Isso substitui um prazo de
validade arbitrário por uma âncora factual — uma leitura descreve o dia em que
foi medida. Leitura de ontem não adapta a sessão de hoje; leitura antiga não
penaliza nada; dia sem sessão de qualidade não recebe o sinal de outro dia. O
CLI informa o motivo quando a leitura **não** é aplicada, para que um sinal
ruim ignorado seja distinguível de prontidão boa.

### 9.2 A leitura de hoje: quando pode agir

**POLÍTICA DO SISTEMA.** A intervenção só alcança a sessão do dia que a leitura
**descreve** (§9.1, ancoragem por dia). Para que isso valha no uso diário, a
avaliação roda antes de o dia ser publicado: `check`, no script do timer
(`check --apply` → `reconcile` → `push`).

**Limite de evidência, não de conveniência.** Só se toca numa sessão que o
Intervals **não** confirma como realizada. "Concluída" (evento com
`paired_activity_id`, o mesmo critério que o `reconcile` já usava) é
preservada. Acima do horário planejado sem realização confirmada, o estado é
**desconhecido** e o comando **propõe sem aplicar**: o Intervals não
distingue "começou e ainda não sincronizou" de "não começou", e tratar a
ausência como "não iniciada" reescreveria uma sessão em andamento. Preferir
não agir a reescrever o treino que o atleta está fazendo é a escolha
conservadora correta, e a incerteza é declarada na saída em vez de escondida.

Isto **não** é validação fisiológica: é uma política de não agir sobre
informação que o sistema não tem. E o fuso horário não é configurável no
projeto — a "data local do atleta" é a data local da máquina.

### 9.3 Tendências observadas de HRV e RHR (HR-3)

**O que foi implementado.** `HeartRateTrendView` (`src/ui_state.py`) expõe, por
sinal e separadamente: valor observado, baseline individual (média da janela),
delta absoluto, delta percentual e número de observações. Um sinal isolado é
mais informativo que uma média; a média esconde a variabilidade.

**O que é ferramenta computacional, e o que não é.** Baseline e delta são
**aritmética sobre observações do próprio atleta** — nenhuma afirmação
fisiológica. A janela default de 7 dias é a mesma convenção já usada por
`_rising_rhr`/`_low_hrv`, não um protocolo de coleta. **A interpretação** do
delta — se uma queda de HRV é adaptação, estresse ou doença — continua
inteiramente na heurística existente de §9.1, com os mesmos thresholds, e não
foi duplicada nem reinterpretada.

**Por que a média de 7 dias não vira evidência.** A literatura de treino
guiado por HRV (§9) sustenta o uso de HRV como *uma entrada* de decisão. Isso
não autoriza converter HRV em limiar absoluto: o mesmo valor é normal para um
atleta e outro para outro, e depende de horário de coleta, posição corporal e
dispositivo — nenhum dos quais o boundary expõe. Daí o baseline ser
**individual**, e a unidade de `hrv` estar **não documentada** no projeto:
comparar `hrv` com `hrv_sdnn` seria comparar métricas diferentes sem saber qual
é qual.

**Consequência no motor.** HR-3 é leitura pura: local, offline, sem provider,
sem policy e sem prescrição. Dado `stale` continua produzindo valor derivado,
com a frescor visível. Ausência nunca vira zero, e zero observado é tratado
como leitura quebrada de sensor, não como observação.

**Nota terminológica, sem conteúdo fisiológico.** `FCR` significa **frequência
cardíaca de repouso** — é o termo PT-BR de RHR (*Resting Heart Rate*), o mesmo
sinal com outro nome. Não é uma terceira métrica e por isso não tem campo
próprio: expô-lo duplicaria a mesma observação. *Heart-rate recovery* (queda da
FC pós-esforço) é outro conceito, fora deste escopo e não implementado.

Detalhes em `docs/HR-3-HRV-RHR-TRENDS.md`.

## 10. Adaptation State

**HEURÍSTICA DO SISTEMA / MODELO COMPUTACIONAL.** `AdaptationState`
(`src/adaptation.py`) mantém seis domínios normalizados de 0 a 1, atualizados
por vetor de contribuição, decaimento temporal e saturação. **São heurísticas
computacionais para o motor, não medições fisiológicas.** Nenhum valor de
decaimento ou saturação tem lastro em literatura; são escolhidos para dar
comportamento estável e configurável.

`TrainingDecision` (`src/training_decision.py`) compõe os eixos em uma decisão
com `rationale` e `confidence`. A confiança é **heurística**: reflete
concordância entre sinais, não probabilidade estatisticamente calibrada.

**Limite conhecido: `decay()` só limita por baixo.** O fator é
`max(0, 1 − days × daily_rate)`, sem teto superior. Com `days` negativo — data
de treino no futuro, erro de import — ou com `daily_rate` negativo, o fator
passa de 1 e a adaptação **cresce acima do estado anterior**, o que contraria o
nome da função. O clamp inferior existe; o superior não. Registrado em
`test_adaptation.py::test_taxa_negativa_amplifica_por_falta_de_teto_superior`.

## 11. Progression Engine

**MODELO COMPUTACIONAL.** `CompletionScore` e a progressão por família de
estímulo ficam em `src/progression.py`. A regra de prescrição que o motor
segue é: **um degrau deve mexer em uma dimensão por vez**. Subir repetições e
duração no mesmo degrau confunde volume com estrutura e dificulta atribuir
falha a uma causa.

**Essa regra é uma aspiração, não o estado do código.** As escadas de
`src/progression.py` (`SEQUENCES`) mudam **repetições e duração ao mesmo
tempo** em quatro das treze transições entre degraus:

| Família | Transição | O que muda | Trabalho total |
| --- | --- | --- | --- |
| Sweet Spot | 3 × 12 min → 2 × 15 min | repetições e duração | 36 → 30 min (**−16,7%**) |
| Limiar | 3 × 12 min → 2 × 15 min | repetições e duração | 36 → 30 min (**−16,7%**) |
| VO2max | 5 × 3 min → 4 × 4 min | repetições e duração | 15 → 16 min (**+6,7%**) |
| Anaeróbico | 8 × 1 min → 6 × 2 min | repetições e duração | 8 → 12 min (**+50%**) |

As outras nove mudam uma dimensão só.

**Correção (02/10/2026, issue #59).** Este texto antes afirmava que as quatro
transições mudavam "a forma do bloco, **não** o volume total", e citava
"3×12→2×15 preserva 36 min" e "5×3→4×4 preserva 15 min". **A aritmética não
confereva:** nenhuma das quatro preserva o volume total, e elas não vão na mesma
direção — duas reduzem, duas aumentam. O par 3×12→2×15 vai de 36 para 30 min.
A afirmação foi removida e a tabela acima passa a mostrar o delta real, para que
não se leia "troca de forma" como "volume constante".

O que a troca de forma faz é mudar **quantidade de intervalos e comprimento de
cada um** mantendo o esforço total próximo. Que isso seja uma progressão
desejável é uma **decisão de engenharia do Hermes**, não um achado da literatura:
nenhum dos estudos citados na seção 12 compara 3×12 com 2×15. A redução de 16,7%
em Sweet Spot e Limiar em particular é uma escolha de prescrição do sistema, e
está registrada como tal.

`tests/scientific/test_progression.py::test_sequencia_por_familia_muda_uma_dimensao_por_degrau`
trava as quatro exceções nominalmente, e
`test_delta_de_trabalho_total_das_excecoes` trava os valores absolutos de
trabalho por degrau de cada família. Alterar qualquer degrau de `SEQUENCES`
exige atualizar as duas listas — a troca passa a ser uma decisão explícita em
vez de efeito colateral de um ajuste de volume.

**Limite conhecido: a contagem de dimensões não conta o estímulo.** A regra de
"uma dimensão por vez" olha quatro campos — `repeats`, `work_sec`,
`recovery_sec`, `intensity`. Mas `recovery_sec` é **função** de `work_sec`
(180 s a partir de 8 min de bloco, 120 s abaixo disso), de modo que a razão
trabalho:recuperação muda em **todo** degrau de duração, mesmo quando o valor
de `recovery_sec` não muda:

| Família | Razão antes | Razão depois |
| --- | --- | --- |
| Anaeróbico (8×1 → 6×2) | 60:120 = 0,50 | 120:120 = **1,00** |
| Sweet Spot (3×12 → 2×15) | 720:180 = 4,00 | 900:180 = **5,00** |
| VO2max (5×3 → 4×4) | 180:120 = 1,50 | 240:120 = **2,00** |

Ou seja: a invariante é satisfeita no sentido dos campos declarados e violada no
sentido do estímulo. Tratar a razão como uma quinta dimensão reprovaria também as
nove transições "corretas", por isso ela fica **documentada** e não vira
assertion. Como a recuperação modula a resposta da sessão (PMID 31146621), isso
importa: a razão não é um detalhe de planilha. Registrado em
`test_progression.py::test_razao_trabalho_por_recuperacao_muda_em_todo_degrau_de_duracao`,
que falha se `recovery_sec` deixar de acompanhar `work_sec`.

No gerador VO2max a regra **é** respeitada: escadas separadas para duração do
intervalo, repetições, tempo total e intensidade, expostas por
`progression_ledger()` para verificação, e
`test_vo2.py::test_ladder_altera_apenas_uma_dimensao_por_degrau` fecha a
invariante. No caso das famílias de Z2, Sweet Spot e Limiar, as alavancas são
de **dose**: Z2 e Sweet Spot progridem em duração e volume; Limiar em duração,
repetições e recuperação (seção 4).

**HEURÍSTICA DO SISTEMA.** Granularidade de degrau, saltos de volume e os
limiares que disparam avanço, estagnação ou recuo são do sistema. A
`CompletionScore` não é uma medida de quanto o atleta de fato executou.

### 11.1 Progressão multidimensional

O HIIT é tratado pela literatura como um jogo de mais de uma variável por vez, e
ela **não** trata intensidade, duração do esforço, recuperação e número de
repetições como independentes. É o que separa o que se sabe do que o Hermes
escolheu.

#### Evidência científica

**EVIDÊNCIA CIENTÍFICA — HIIT tem múltiplas variáveis manipuláveis.** A revisão
de Buchheit & Laursen lista intensidade e duração do esforço, intensidade e
duração da recuperação, número de repetições e número de séries como variáveis
de prescrição (PMID 23539308). Consequência direta: `work_sec` ↑ sozinho não
demonstra que o estímulo progrediu, e `intensity` ↑ sozinho também não.

**EVIDÊNCIA CIENTÍFICA — intensidade e duração interagem.** Seiler e colaboradores
compararam combinações de intensidade e duração total em ciclistas; o efeito não
se decompõe em "mais intensidade" ou "mais duração" separadamente (PMID 21812820,
*Scandinavian Journal of Medicine & Science in Sports* — **não** MSSE).

**EVIDÊNCIA CIENTÍFICA — a recuperação modula a resposta.** A duração da
recuperação entre intervalos modifica a resposta da sessão e a capacidade de
sustentar trabalho subsequente (PMID 31146621). Por isso `recovery` entra na
auditoria junto com `work_sec`, `repeats` e `intensity`.

**EVIDÊNCIA CIENTÍFICA — tempo acumulado, não intensidade instantânea.** Para
sessões VO2 o alvo é tempo acumulado sob elevada demanda aeróbia, e intervalos
mais longos podem permitir mais tempo perto do V̇O₂max em desenhos específicos
(seção 12; PMID 42237396). Isso **não** autoriza concluir que todo intervalo VO2
deve ficar mais longo.

**EVIDÊNCIA CIENTÍFICA — nenhum formato é universalmente superior.** A network
meta-analysis de Held e colaboradores não encontrou superioridade entre estruturas
(PMID 42482078). A heterogeneidade dos protocolos é razão suficiente para não
transformar uma observação específica em regra do Hermes.

**EVIDÊNCIA CIENTÍFICA — carecem de base.** Nenhum dos estudos acima compara
3 × 12 min com 2 × 15 min, 5 × 3 com 4 × 4 ou 8 × 1 com 6 × 2. As quatro
transições de `SEQUENCES` e os degraus do gerador VO2max **não são**
replicações de resultado publicado.

#### Decisões de engenharia do Hermes

As decisões a seguir **não** decorrem dos estudos acima. São escolhas do sistema,
adotadas porque tornam a progressão interpretável, testável, previsível e
auditável — e porque uma transição que mexe em duas dimensões de uma vez impede
atribuir falha a uma causa.

- **Uma dimensão por degrau**, quando aplicável. É a regra que origina as
  escadas separadas do gerador VO2max (`_ladder`) e a lista de exceções de
  `SEQUENCES`. Onde não é respeitada, a exceção está nomeada e travada.
- **Avoidance de transições contraditórias** entre dimensões — sem subir
  duração enquanto reduz repetições, exceto nas quatro exceções declaradas.
- **`repeats × work_sec` como sanity check**, não como métrica de estímulo. Serve
  para localizar transições suspeitas; não é dose fisiológica.
- **Intensidade fora da escada de `progression.py`**, fixa em 0,90 e sob controle
  de `ZONE_BANDS`. É por isso que a escada não é caminho para subir potência.
- **`INTENSITY` no gerador VO2max**: faixa prescrita tem teto em
  `ZONE_BANDS['vo2max']`, e falta de folga é erro, não degrau válido — hoje
  `generate()` levanta `ValueError`. Não se baixa a faixa padrão para ativar o
  lever: a prescrição determina a abstração, não o contrário.

**Fora do escopo do Hermes:** qual família progride por qual dimensão, e se
2 × 15 min serve melhor como prescrição que 3 × 12 min. Não se compara: a literatura
não traz as duas formas, e nenhum estudo citado escolhe entre elas. Onde a
resposta depende de julgamento técnico, o sistema pede validação com treinador
(`ROTEIRO-TREINADOR`).

## 12. VO2max

**EVIDÊNCIA CIENTÍFICA.** Intervalos de trabalho longos (≥2 min) produziram mais
tempo próximo de V̇O₂max que curtos (≤30 s) ou moderados (>30 s e <2 min), e
intervalos de intensidade variável superaram formatos de ritmo par
(SMD = 0,80; p < 0,01) (PMID 42237396, DOI 10.1186/s13102-026-01766-x). A mesma
revisão registra que a modalidade de recuperação (ativa vs. passiva) **não teve
efeito** sobre o tempo perto de V̇O₂max, e que a relação dose-resposta com
adaptações de longo prazo **ainda exige investigação**.

**EVIDÊNCIA CIENTÍFICA — nenhuma estrutura de protocolo é superior.** Numa
network meta-analysis de 19 publicações (240 atletas, 25,5 ± 5,3 anos),
nenhuma abordagem de HIIT diferiu significativamente dos intervalos longos
pares em tempo acumulado ≥90% V̇O₂max. As estimativas pontuais mais altas foram
para duração decrescente (SMD = 0,87; IC 95% −0,30–2,04) e intensidade variando
(SMD = 0,54; IC 95% −0,42–1,49), e 1:1 pontuou mais baixo (SMD = −0,68), mas
**todas as comparações de referência foram não significativas**, com
heterogeneidade substancial (I² = 69,2%; Q total = 55,12; df = 17; p < 0,0001) e
inconsistência significativa (Q entre designs = 20,78; p = 0,002). Os autores
concluem que a seleção de protocolo deve priorizar viabilidade,
características do atleta e correspondência de carga **em vez do ranking**, que
classificam como exploratório (PMID 42482078, DOI 10.1186/s13102-026-01891-7).

**MODELO COMPUTACIONAL.** `VO2Workout` (`src/vo2_generator.py`) descreve o
bloco por `interval_duration`, `repetitions`, `work_power_range`,
`recovery_duration`, `recovery_power`, `total_work_time`, `progression_step` e
`lever`, em três famílias: `LONG_INTERVALS`, `SHORT_INTERVALS` e
`VARIABLE_INTERVALS`. A baseline de 4 min de `LONG_INTERVALS` segue o achado dos
intervalos ≥2 min. A faixa padrão de 106–120% FTP é a banda Z5 declarada, e
`Z5_CEILING` impede que o degrau de intensidade atravesse para Z6.

**Limite conhecido: o lever de intensidade é inválido com a faixa padrão.** A
faixa padrão `DEFAULT_INTENSITY_RANGE` já tem 1,20 como teto, e `generate()` faz
`min(Z5_CEILING, high + 0,02 × degrau)`. Como `Z5_CEILING` é 1,20, **todo degrau
produziria a mesma faixa** com a configuração padrão: três degraus idênticos
enquanto `next_step()` avançava como se houvesse progressão. O lever só age
quando a faixa prescrita é mais estreita que a banda Z5, e aí o teto sobe +2%
por degrau até 1,20. Subir intensidade por degrau de escada, portanto, não é o
caminho disponível na configuração padrão: a intensidade é controlada pela faixa
prescrita, não pela escada.

**Resolvido em 02/10/2026 (issue #59): a faixa padrão não foi abaixada, o
comportamento mudo deixou de existir.** `generate()` agora levanta `ValueError`
quando `intensity_range[1] >= Z5_CEILING`, com as duas saídas na mensagem (faixa
com folga, ou outro lever); `progression_ledger()` recebe `intensity_range`
porque a escada é construída a partir da faixa. Recusar a prescrição é
preferível a devolver degrau mudo, porque o chamador não distingue um platô real
de um no-op.
Subir acima do teto continuaria errado: geraria Z6 rotulada como VO2max.
Regressão: `test_vo2.py::test_lever_intensity_e_invalido_na_faixa_padrao` e
`test_vo2_generator.py::test_intensidade_sem_folga_falha_explicitamente`.

**Os templates não seguem a regra de dimensão única.** `MIXED_TEMPLATES` muda
a forma do bloco inteiro, mas nem toda transição muda duas dimensões:

| Família | Transição | Dimensões que mudam |
| --- | --- | --- |
| `LONG_INTERVALS` | 4x4 → 5x3 → 3x5 | duas em ambas |
| `SHORT_INTERVALS` | 5x1 → 10x1 | só repetições |
| `SHORT_INTERVALS` | 10x1 → 6x2 | duas |
| `VARIABLE_INTERVALS` | 2x3 → 3x3 → 4x3 | só repetições |

`VARIABLE_INTERVALS` é, no efeito, uma escada de repetições com duração fixa —
despite o nome da família sugerir variabilidade de duração. Nenhum template é
alcançável pelo `ProgressionLever`: eles sãoغرupados à parte e o motor não os
integra às escadas por dimensão.

**HEURÍSTICA DO SISTEMA.** Os templates 4x4, 5x3 e 3x5 são **formatos de
prescrição configuráveis**, não protocolos universais nem recomendações de
eficácia — a network meta-analysis não encontrou superioridade entre estruturas.
115% do FTP **não** é valor universal. O degrau de intensidade (+2% por degrau)
e a direção dessa progressão são convenções: a NMA posicionou duração
decrescente e intensidade variável acima das demais, mas de forma exploratória e
não significativa. E, como registrado acima, o degrau não se manifesta com a
faixa padrão — a truncagem no teto de Z5 o anula. `recovery_power` (0,40) e
`recovery_ratio` (0,5) são convenções — a recuperação ativa vs. passiva não
afetou o tempo perto de V̇O₂max (PMID 42237396). A faixa de trabalho acumulado
(600–2400 s) em `evaluate()` também é heurística: os templates ficam sempre
dentro dela.

## 13. Recovery / Deload

**HEURÍSTICA DO SISTEMA.** Um treino perdido **não** é reparado por uma sessão
binária de "recuperação" nem por uma redução fixa de −5% no próximo Limiar. A
carga não feita é **redistribuída** nos treinos posteriores de mesma natureza que
ainda tenham folga dentro do teto semanal — limitada por `weekly_budget`, não por
fator arbitrário. Implementação: `cmd_reconcile` /
`_absorb_missed_into_budget`.

O custo de perder uma sessão é proporcional ao **estímulo fisiológico**, não ao
TSS bruto (tabela de exemplo, FTP 250 W):

| Treino perdido | TSS | Decisão do Algoritmo | Fundamentação |
|---|---|---|---|
| **Active recovery** (Z2 ≈0,55–0,60) | ~14 | **Não compensa** | O propósito do treino é **não gerar carga**; compensar exigiria carga, contradizendo o objetivo. |
| **Z2 base** (≈0,70) | ~24 | **Absorve** (dentro do teto) | Volume puro; absorvível com mais volume de mesma natureza. |
| **SweetSpot** (≈0,88) | ~37 | **Absorve** (dentro do teto) | Volume puro, mesma natureza. |
| **Limiar** (≈0,98) | ~48 | **Não substitui com volume** | O estímulo é de alta intensidade; não se constrói com mais Z2. Fica como débito para o `build` repriorizar. |
| **VO2máx** (≈1,15) | ~41 | **Não substitui com volume** | A adaptação aeróbica vem da intensidade, não de volume de base. |

**Limites de segurança da absorção.** Só sessões **Z2/SweetSpot** recebem
elevação de volume (nunca VO2/Limiar); cada treino cresce no máximo **20%** de
`on_sec` por reconciliação; só absorve enquanto a soma rolante de 7 dias couber
no teto — sem folga, a carga não feita sobe o TSB e o próprio `build` reduz a
semana seguinte.

> **Erro corrigido (v0.0.30):** a regra anterior inseria uma "recuperação" e
> reduzia −5% no próximo Limiar para **qualquer** falta, sem distinguir a
> natureza do treino perdido — inclusive quando o treino perdido era o próprio
> active recovery, ou VO2máx (compensar estímulo de intensidade com volume de
> base).

Active recovery é tratado como **intenção de sessão dentro de Z2**, não como
foco Z1 e não absorvível quando perdido (seção 4, decisão 3).

## 14. Limitações

**MODELO COMPUTACIONAL.** O que este motor não faz, e não deve ser lido como se
fizesse.

1. **FTP não é fisiologia.** É referência operacional de potência, com limites
   de concordância amplos frente a marcadores de lactato. Não infere MLSS, LT,
   VT, RCP ou CP (seção 2).
2. **Não há modelo de periodização superior.** A evidência é insuficiente para
   eleger um; o Hermes escolhe por coerência interna e configurabilidade, não
   por eficácia demonstrada (seções 5 e 6).
3. **Não há protocolo de VO2max superior.** As comparações entre estruturas são
   não significativas e heterogêneas (seção 12).
4. **TSS é metodologia de indústria.** NP/IF/TSS não são equivalentes a medidas
   fisiológicas, e em HIIT curto o valor depende do método de cálculo da NP
   (seção 7).
5. **Prontidão não prediz desempenho.** O efeito de HRV-guidado é pequeno e não
   significativo para desempenho e V̇O₂*pico* (seção 9).
6. **Módulos isolados não afetam a publicação.** `src/training_phase.py`,
   `src/progression.py`, `src/intensity_distribution.py`,
   `src/athlete_profile.py`, `src/adaptation.py`, `src/training_decision.py`,
   `src/readiness_assessment.py`, `src/critical_power.py`,
   `src/vo2_generator.py` e `src/zone_intent.py` não participam de `build`/`push`,
   não alteram `plan.json`, os valores de `focus`, as bandas nem a publicação no
   Intervals.icu. São contratos testados, ainda não integrados ao fluxo.
7. **Heurísticas não são constantes fisiológicas.** Taxas de decaimento,
   saturação, reconstituição de W′, degraus de progressão, limites de TSB e
   coeficientes de IWMA são do sistema e configuráveis.
8. **Base de evidência restrita.** Vários estudos incluem só ciclistas do sexo
   masculino; a revisão de FTP20 (15 estudos) e a de HRV (8 estudos) são
   explicitamente pequenas. A generalização para outros orçamentos e estilos de
   pedal não está estabelecida.

**Limites de implementação conhecidos.** Estes quatro não são deficiências da
literatura: são comportamentos do código que a documentação anterior descrevia
de forma mais forte do que o código entrega. Estão declarados aqui e em seção
própria, e cada um tem trava de teste.

9. **As escadas de `progression.py` violam a regra de dimensão única em quatro
   transições** (seção 11). A regra é a intenção de prescrição; o código a segue
   em nove de treze transições e a quebra nas quatro restantes, que trocam
   repetições **e** duração no mesmo degrau. **O trabalho total não se mantém:**
   −16,7% em Sweet Spot e Limiar, +6,7% em VO2max e +50% em Anaeróbico. A versão
   anterior deste texto dizia que as quatro "preservavam o volume total"; a
   aritmética não confirmava e foi corrigida em 02/10/2026. Consequência: a
   escada não é um caminho para subir potência — a intensidade é fixa em 0,90.
   A regra em si é **heurística de engenharia**, não regra fisiológica.
10. **A contagem de "uma dimensão por vez" não conta o estímulo.** `recovery_sec`
    é função de `work_sec`, então a razão trabalho:recuperação muda em todo
    degrau de duração mesmo com `recovery_sec` constante (Anaeróbico 0,50 → 1,00;
    Sweet Spot 4,00 → 5,00; VO2max 1,50 → 2,00). A invariante conta quatro campos
    declarados e ignora a razão, por isso passa onde o estímulo mudou.
11. **O lever `INTENSITY` de VO2max não tem efeito com a faixa padrão** (seção
    12). `DEFAULT_INTENSITY_RANGE` é igual à banda Z5 `(1,06; 1,20)`, então o teto
    `Z5_CEILING` trunca todo degrau e a escada devolvia três treinos idênticos
    enquanto `next_step()` avançava como se houvesse progressão. **Resolvido em
    02/10/2026:** `generate()` agora levanta `ValueError` quando não há folga
    abaixo do teto, em vez de devolver degrau mudo. O lever só age com faixa
    prescrita mais estreita — e continua correto assim, porque subir acima do teto
    geraria Z6 rotulada como VO2max. Regressão:
    `test_vo2_generator.py::test_intensidade_sem_folga_falha_explicitamente`.
12. **`AdaptationState.decay()` não tem teto superior** (seção 10). Com `days` ou
    `daily_rate` negativo, a adaptação cresce acima do estado anterior, contra o
    nome da função.
13. **`estimate_cp()` enviesa o intercepto** (seção 3). OLS de $P$ contra $1/t$
    não é o estimador compatível para o intercepto de $P = CP + W'/t$, não
    pondera por duração e não filtra outlier. O CP é honesto dentro da faixa de
    durações medida; extrapolar para o assíntoto com poucos pontos é chute.

### 14.1 Limitações de modelos isolados (#60)

**EVIDÊNCIA CIENTÍFICA.** Destreino, CP/W' e dose de treino intervalado dependem
do atleta, do protocolo, da variável observada, da distribuição das durações e
do contexto. Não há, na evidência usada pelo Hermes, uma taxa universal de
perda de adaptação entre domínios, um estimador universalmente superior de
CP/W', nem um percentual único de FTP adequado a todas as famílias de treino.

Coyle et al. observaram cinéticas distintas de perda após destreino, e a revisão
de Clarke & Skiba descreve os modelos fitness-fatigue como modelos de desempenho
ajustados ao indivíduo, não como estoque fisiológico universal normalizado
(PMID 6511559; PMID 23728131). Estimativas de CP/W' variam com modelo e com a
faixa de durações dos esforços, mesmo quando o ajuste aparenta ser bom (Jenkins
et al., PMID 9923729; Bull et al., PMID 10694142; Vinetti et al., PMID
30694386). Intensidade, duração, recuperação, repetições e séries compõem a
dose do intervalado; uma intensidade isolada não identifica uma família de
treino (Buchheit & Laursen, PMID 23539308). FTP não é intercambiável com
marcadores fisiológicos individuais (Inglis et al., PMID 31689684; Jeffries et
al., PMID 31269000; Mackey et al., PMID 34304689).

**LIMITAÇÕES.** `AdaptationState.decay()` é uma heurística linear:
`max(0, 1 - days * daily_rate)`. Com `days` ou `daily_rate` negativos, o fator
pode exceder 1 e o estado crescer acima da faixa conceitual normalizada. O
fitting CP/W' usa OLS não ponderado de `P` contra `1/t`, sem quality gates de
protocolo/esforço nem remoção automática de outliers. `ProgressionStep` carrega
`intensity=0.90` uniforme como placeholder; isso não é dose fisiológica
universal entre Endurance, Sweet Spot, Threshold, VO2max e Anaerobic.

**DECISÕES DE ENGENHARIA HERMES.** Os três módulos permanecem isolados, sem
consumidores produtivos em `src/plan.py` ou `src/training_plan.py`; hoje não
alteram workout publicado, TSS, intensidade, duração, zonas, calendário ou
payload. A auditoria #60 encerra as decisões, não implementações:

- `decay()`: corrigir futuramente como invariante de engenharia. A futura
  decisão deve separar validação de entrada (`days >= 0`, `daily_rate >= 0`) de
  eventual normalização de estado em `0..1`; não define função fisiológica.
- CP/W' OLS: manter informativo; uso prescritivo não está autorizado. CP/W'
  Fase 2 permanece complementar ao FTP; Fase 3 não tem roadmap ativo e não é
  planejada no momento.
- `intensity=0.90`: manter isolado como placeholder declarado; não substituir o
  valor nem integrar `ProgressionEngine` nesta decisão.

Qualquer integração futura exige decisão explícita, contrato de domínio e testes
de não regressão. `zone_intent` já é guardrail semântico derivado de `focus` no
build; esta auditoria não altera `ZONE_BANDS`, `focus`, `WorkoutParams` nem
`plan.json`.

**QUESTÕES ABERTAS.** Para `decay()`, definir invariantes de entrada e de
normalização sem apresentá-los como teto fisiológico. Para CP/W', definir
protocolo, qualidade dos esforços, cobertura de durações e quality gates antes
de comparar OLS, WLS, regressão robusta ou outro modelo. Para
`ProgressionEngine`, definir intensidade por família e sua reconciliação com
`ZONE_BANDS`, `focus` e o contrato de `WorkoutParams` antes de integração
produtiva.

## 15. Referências

Todas verificadas por PMID no NCBI. Autores, títulos e resultados citados neste
documento foram conferidos contra o abstract.

1. **Banister, E. W. (1991).** *Modeling Muscle Fatigue and Recovery in Training*.
2. **Seiler, S. (2010).** *What is Best Practice for Training Intensity Distribution in Endurance Athletes?* International Journal of Sports Physiology and Performance.
3. **Seiler, S. (2018).** *Periodization Theory: Confronting an Inconvenient Truth*. Swiss Sports Institute.
4. **Coggan, A., & Allen, H. (2010).** *Training and Racing with a Power Meter*. Velopress.
5. **Billat, L. V. (2001).** *Interval Training for Performance: A Scientific and Empirical Update*. Sports Medicine.
6. **Friel, J. (2014).** *The Periodization Bible*. 2nd ed. Velo.
7. **Coggan, A. (2026).** *Normalized Power, Intensity Factor and Training Stress Score.* TrainingPeaks — <https://www.trainingpeaks.com/learn/articles/normalized-power-intensity-factor-training-stress/>
   *METODOLOGIA DE INDÚSTRIA. Definição operacional de NP, IF e TSS; não é evidência fisiológica primária.*
8. **Galán-Rioja, M. Á., Gonzalez-Ravé, J. M., González-Mohíno, F., & Seiler, S. (2023).** *Training Periodization, Intensity Distribution, and Volume in Trained Cyclists: A Systematic Review.* International Journal of Sports Physiology and Performance. PMID 36640771 — <https://doi.org/10.1123/ijspp.2022-0302>
   *EVIDÊNCIA. Sete estudos; nenhuma evidência a favor de um modelo de periodização específico em 8–12 semanas.*
9. **Cove, B., Chalmers, S., et al. (2025).** *The effect of training distribution, duration, and volume on VO₂max and performance in trained cyclists: a systematic review, multilevel meta-analysis, and multivariate meta-regression.* Journal of Science and Medicine in Sport. PMID 39788807 — <https://doi.org/10.1016/j.jsams.2024.12.005>
   *EVIDÊNCIA. 41 estudos, 797 participantes; polarizado e não polarizado sem diferença significativa; sem associação entre volume e adaptação.*
10. **Mackey, N., et al. (2021).** *What is known about the FTP(20) test related to cycling? A scoping review.* Journal of Sports Sciences. PMID 34304689 — <https://pubmed.ncbi.nlm.nih.gov/34304689/>
    *EVIDÊNCIA. Teste confiável, mas limites de concordância amplos impedem troca intercambiável de parâmetros.*
11. **Jeffries, O., Simmons, R., Patterson, S. D., & Waldron, M. (2021).** *Functional Threshold Power Is Not Equivalent to Lactate Parameters in Trained Cyclists.* Journal of Strength and Conditioning Research, 35(10), 2790–2794. PMID 31269000 — <https://pubmed.ncbi.nlm.nih.gov/31269000/>
    *EVIDÊNCIA. r = 0,88 com LT4,0, mas limites de concordância de −45 a +51 W; LT, IAT e Dmax diferiram de FTP.*
12. **Inglis, C., et al. (2020).** *Maximal Lactate Steady State Versus the 20-Minute Functional Threshold Power Test in Well-Trained Individuals: "Watts" the Big Deal?* International Journal of Sports Physiology and Performance. PMID 31689684 — <https://pubmed.ncbi.nlm.nih.gov/31689684/>
    *EVIDÊNCIA. MLSS = 88,5% do FTP (DP 4,8%); MLSS respondeu ao treino (+12 W) e FTP95% não.*
13. **Sitko, S., et al. (2022).** *Relationship between functional threshold power, ventilatory threshold and respiratory compensation point in road cycling.* Journal of Sports Medicine and Physical Fitness. PMID 33728842 — <https://pubmed.ncbi.nlm.nih.gov/33728842/>
    *EVIDÊNCIA. FTP acima de VT; FTP e RCP fortemente relacionados, com ressalva contra uso indistinto.*
14. **Chorley, A., Lamb, K. L., et al. (2020).** *The Application of Critical Power, the Work Capacity above Critical Power (W′), and its Reconstitution: A Narrative Review of Current Evidence and Implications for Cycling Training Prescription.* Sports, 8(9), 123. PMID 32899777 — <https://doi.org/10.3390/sports8090123>
    *EVIDÊNCIA. CP como taxa do estado aeróbico máximo; W′ como trabalho tolerável acima de CP.*
15. **Düking, P., Zinner, C., Trabelsi, K., Reed, J. L., et al. (2021).** *Monitoring and adapting endurance training on the basis of heart rate variability monitored by wearable technologies: A systematic review with meta-analysis.* Journal of Science and Medicine in Sport. PMID 34489178 — <https://doi.org/10.1016/j.jsams.2021.04.012>
    *EVIDÊNCIA. Efeito médio em parâmetros submáximos; efeito pequeno e não significativo em desempenho e V̇O₂*pico*.*
16. **Granero-Gallegos, A., González-Quílez, A., et al. (2020).** *HRV-Based Training for Improving VO₂max in Endurance Athletes. A Systematic Review with Meta-Analysis.* International Journal of Environmental Research and Public Health, 17(21), 7999. PMID 33143175 — <https://doi.org/10.3390/ijerph17217999>
    *EVIDÊNCIA. Efeito pequeno e positivo no desempenho, condicionado a nível e sexo do atleta.*
17. **Schoenmakers, P., et al. (2026).** *Time spent at or near V̇O₂max during high-intensity interval training — a systematic review and meta-analysis.* BMC Sports Science, Medicine and Rehabilitation, 2026. PMID 42237396 — <https://doi.org/10.1186/s13102-026-01766-x>
    *EVIDÊNCIA. Intervalos ≥2 min > curtos/moderados; intensidade variável > ritmo par (SMD 0,80); recuperação ativa vs. passiva sem efeito.*
18. **Held, S., et al. (2026).** *Comparison of high-intensity interval training protocol designs on accumulated time ≥90% V̇O₂max: a network meta-analysis.* BMC Sports Science, Medicine and Rehabilitation, 2026. PMID 42482078 — <https://doi.org/10.1186/s13102-026-01891-7>
    *EVIDÊNCIA. Nenhuma estrutura superior; todas as comparações não significativas, I² = 69,2%; rankings exploratórios.*

19. **Buchheit, M., & Laursen, P. B. (2013).** *High-intensity interval training, solutions to the programming puzzle: Part I: cardiopulmonary emphasis.* Sports Medicine, 43(5), 313–338. PMID 23539308 — <https://doi.org/10.1007/s40279-013-0029-x>
    *EVIDÊNCIA. Múltiplas variáveis manipuláveis na prescrição de HIIT: intensidade e duração do esforço, intensidade e duração da recuperação, número de repetições e número de séries. Sustenta que nenhuma delas progride de forma isolada.*
20. **Seiler, S., Jøranson, K., Olesen, B. V., et al. (2013).** *Adaptations to aerobic interval training: interactive effects of exercise intensity and total work duration.* Scandinavian Journal of Medicine & Science in Sports, 23(2), e53–e63. PMID 21812820 — <https://doi.org/10.1111/j.1600-0838.2011.01351.x>
    *EVIDÊNCIA. Efeitos interativos de intensidade e duração total em ciclistas. Sustenta "intensidade × duração interagem"; não sustenta a leitura de que uma das duas, isolada, seja superior. Nota de origem: a revista é Scandinav J Med Sci Sports, não MSSE.*
21. **Schoenmakers, P. P. J. M., Hettinga, F. J., & Reed, K. E. (2019).** *The Moderating Role of Recovery Durations in High-Intensity Interval-Training Protocols.* International Journal of Sports Physiology and Performance, 14(7), 994–1002. PMID 31146621 — <https://doi.org/10.1123/ijspp.2018-0876>
    *EVIDÊNCIA. A duração da recuperação modera a resposta da sessão e a capacidade de sustentar trabalho subsequente. Sustenta avaliar `recovery` junto de `work_sec`, `repeats` e `intensity` — base do limite sobre a razão trabalho:recuperação (§11).*
22. **Rosenblat, M. A., Lin, E., da Costa, B. R., et al. (2021).** *Programming Interval Training to Optimize Time-Trial Performance: A Systematic Review and Meta-Analysis.* Sports Medicine, 51(8), 1857–1880. PMID 33826121 — <https://doi.org/10.1007/s40279-021-01457-2>
   *EVIDÊNCIA. Programação de intervalos para desempenho em contrarrelógio. Cited como contexto de Relationship entre duração do intervalo, dose e desempenho — não como regra determinística do algoritmo.*

23. **Jones, A. M., Vanhatalo, A., Burnley, M., Morton, R. H., & Poole, D. C. (2010).** *Critical power: implications for determination of V̇O₂max and exercise tolerance.* Medicine & Science in Sports & Exercise, 42(10), 1876–1890. PMID 20195180 — <https://doi.org/10.1249/MSS.0b013e3181d9cf7f>
   *EVIDÊNCIA. Revisão dos fundamentos do modelo CP/W′: CP como assíntoto e W′ como componente finito associado à tolerância acima de CP.*
24. **Morgan, P. T., Black, M. I., Bailey, S. J., Jones, A. M., & Vanhatalo, A. (2019).** *Road cycle TT performance: Relationship to the power-duration model and association with FTP.* Journal of Sports Sciences, 37(8), 902–910. PMID 30387374 — <https://doi.org/10.1080/02640414.2018.1535772>
   *EVIDÊNCIA. CP/W′ obtidos de esforços de TT predizem desempenho; os limites de concordância entre CP e FTP foram amplos demais para tratá-los como intercambiáveis.*
25. **Karsten, B., Petrigna, L., Klose, A., Bianco, A., Townsend, N., & Triska, C. (2021).** *Relationship Between the Critical Power Test and a 20-min Functional Threshold Power Test in Cycling.* Frontiers in Physiology, 11, 613151. PMID 33551839 — <https://doi.org/10.3389/fphys.2020.613151>
   *EVIDÊNCIA. Correlação forte não torna CP e FTP intercambiáveis no indivíduo; os limites de concordância foram amplos.*
26. **Leo, P., Spragg, J., Podlogar, T., Lawley, J. S., & Mujika, I. (2022).** *Power profiling and the power-duration relationship in cycling: a narrative review.* European Journal of Applied Physiology, 122(2), 301–316. PMID 34708276 — <https://doi.org/10.1007/s00421-021-04833-y>
   *EVIDÊNCIA. Revisão sobre perfil potência-duração; recomenda testes de campo estruturados e alerta contra inferência a partir de esforço único.*
27. **Coyle, E. F., Martin, W. H., Sinacore, D. R., et al. (1984).** *Time course of loss of adaptations after stopping prolonged intense endurance training.* Journal of Applied Physiology, 57(6), 1857–1864. PMID 6511559 — <https://doi.org/10.1152/jappl.1984.57.6.1857>
    *EVIDÊNCIA. Marcadores de destreino tiveram cinéticas distintas após cessar treino de endurance; não sustenta taxa única para todos os domínios.*
28. **Clarke, D. C., & Skiba, P. F. (2013).** *Rationale and resources for teaching the mathematical modeling of athletic training and performance.* Advances in Physiology Education, 37(2), 134–152. PMID 23728131 — <https://doi.org/10.1152/advan.00078.2011>
    *EVIDÊNCIA. Modelos fitness-fatigue e CP abstraem a fisiologia; não definem estoque fisiológico universal normalizado.*
29. **Jenkins, D. G., Kretek, K., & Bishop, D. (1998).** *The duration of predicting trials influences time to fatigue at critical power.* Journal of Science and Medicine in Sport, 1(4), 213–218. PMID 9923729 — <https://doi.org/10.1016/S1440-2440(09)60004-9>
    *EVIDÊNCIA. A seleção das durações de esforço altera a estimativa de CP.*
30. **Bull, A. J., Housh, T. J., Johnson, G. O., & Perry, S. R. (2000).** *Effect of mathematical modeling on the estimation of critical power.* Medicine & Science in Sports & Exercise, 32(2), 526–530. PMID 10694142 — <https://doi.org/10.1097/00005768-200002000-00040>
    *EVIDÊNCIA. Estimativas variam entre parametrizações/modelos de CP.*
31. **Vinetti, G., Taboni, A., Bruseghini, P., et al. (2019).** *Experimental validation of the 3-parameter critical power model in cycling.* European Journal of Applied Physiology, 119(4), 941–949. PMID 30694386 — <https://doi.org/10.1007/s00421-019-04083-z>

32. **Coyle, E. F. (1998).** *Cardiovascular drift during prolonged exercise and the effects of dehydration.* International Journal of Sports Medicine, 19(Suppl 2), S121-S124. PMID 9694416 — <https://doi.org/10.1055/s-2007-971975>

33. **Coyle, E. F., & Gonzalez-Alonso, J. (2001).** *Cardiovascular drift during prolonged exercise: new perspectives.* Exercise and Sport Sciences Reviews, 29(2), 88-92. PMID 11337829 — <https://doi.org/10.1097/00003677-200104000-00009>
     *EVIDÊNCIA. A inclusão do componente curto e a escolha do modelo afetam parâmetros do ajuste.*

34. **Morton, R. H. (1996).** *A 3-parameter critical power model.* Ergonomics, 39(4), 611–619. PMID 8854981 — <https://doi.org/10.1080/00140139608964484>
    *EVIDÊNCIA. Modelo CP de três parâmetros; introduz o componente associado a potência máxima para tratar a região de duração curta.*
35. **Borszcz, F. K., Tramontin, A. F., Bossi, A. H., Carminatti, L. J., & Costa, V. P. (2018).** *Functional Threshold Power in Cyclists: Validity of the Concept and Physiological Responses.* International Journal of Sports Medicine, 39(10), 737–742. PMID 29801189 — <https://doi.org/10.1055/s-0044-101546>
    *EVIDÊNCIA. FTP20, FTP60 e IAT não devem ser tratados como intercambiáveis no indivíduo apenas pelo pequeno viés médio.*
36. **Borszcz, F. K., Tramontin, A. F., & Costa, V. P. (2019).** *Is the Functional Threshold Power Interchangeable With the Maximal Lactate Steady State in Trained Cyclists?* International Journal of Sports Physiology and Performance, 14(8), 1029–1035. PMID 30676826 — <https://doi.org/10.1123/ijspp.2018-0572>
    *EVIDÊNCIA. Relação forte com MLSS em ciclistas treinados não estabelece identidade fisiológica universal.*
37. **Intervals.icu / David. (2021).** *FTP and CP Interchangeability: Some notes.* Fórum oficial — <https://forum.intervals.icu/t/ftp-and-cp-interchangeability-some-notes/2665/2>
    *INTERVALS_OFFICIAL. Descreve a seleção de curva Morton 3P próxima ao esforço máximo e potência da curva em 1 h como eFTP.*
38. **Intervals.icu / David. (2020).** *Power model now complete.* Fórum oficial — <https://forum.intervals.icu/t/power-model-now-complete/1680/4>
    *INTERVALS_OFFICIAL. eFTP contínuo por atividade, retenção quando a estimativa é menor e decay com redução de carga; fórmula de decay não publicada.*
39. **Intervals.icu Forum / Thijs van Luijk. (2024).** *Eftp calculation formula based on effort.* <https://forum.intervals.icu/t/eftp-calculation-formula-based-on-effort/70480/2>
    *INTERVALS_OFFICIAL, confiança média. Reprodução de texto da UI sobre FastFitness.Tips, Morton 3P, janela 180 s–30 min e duração mínima configurável; não é resposta do mantenedor.*
40. **Intervals.icu / David. (2020).** *Download all activities in CSV format.* Fórum oficial — <https://forum.intervals.icu/t/download-all-activities-in-csv-format/599/1>
    *INTERVALS_OFFICIAL. Glossário de `icu_ftp`, `icu_pm_ftp`, CP/W′/pMax do power model da atividade e campos calculados.*
41. **Intervals.icu / David. (2023).** *Custom field Java help.* Fórum oficial — <https://forum.intervals.icu/t/custom-field-java-help/40283/3>
    *INTERVALS_OFFICIAL. `activity.icu_pm_ftp` é o eFTP da atividade.*
42. **Intervals.icu / David. (2023).** *Server side data model for scripts.* Fórum oficial — <https://forum.intervals.icu/t/server-side-data-model-for-scripts/25781/16>
    *INTERVALS_OFFICIAL. Declara os campos de atividade e `SportSettings.ftp_est_min_secs`; não define a semântica precisa de todos os campos rolling/pm.*
43. **Tramontin, A., Borszcz, F., & Costa, V. (2022).** *Functional Threshold Power Estimated from a 20-minute Time-trial Test is Warm-up-dependent.* International Journal of Sports Medicine. PMID 34749416 — <https://doi.org/10.1055/a-1524-2312>
    *EVIDÊNCIA. Aquecimento e pacing afetam o TT20 e o FTP derivado.*
44. **Barbieri, A., Fuk, A., Gallo, G., et al. (2024).** *Cardiorespiratory and metabolic consequences of detraining in endurance athletes.* Frontiers in Physiology, 14, 1334766. PMID 38344385 — <https://doi.org/10.3389/fphys.2023.1334766>
    *EVIDÊNCIA. Revisão em atletas de endurance: classifica até quatro semanas como curto prazo e mais de quatro como longo prazo; relata respostas heterogêneas e queda de VO₂max após 12 dias de interrupção em estudo prévio de corredores/ciclistas.*
45. **Zheng, J., Pan, T., Jiang, Y., & Shen, Y. (2022).** *Effects of Short- and Long-Term Detraining on Maximal Oxygen Uptake in Athletes: A Systematic Review and Meta-Analysis.* BioMed Research International, 2022, 2130993. PMID 36017396 — <https://doi.org/10.1155/2022/2130993>
    *EVIDÊNCIA. Vinte e um estudos; cessação curta e longa reduziram VO₂max, com efeito maior no período longo. Não oferece conversão direta para FTP.*

**Lacuna conhecida (05/10/2026).** Desde a v0.0.31 este documento foi descrito —
também no `AGENTS.md` — como contendo uma "Tabela Científica Z1–Z7" com colunas
de %FCmáx, %FC de limiar e RPE por zona (VT1, MLSS, VT2), sistema energético,
recuperação típica e matriz de geração `.ZWO`, e como sendo essa tabela
canônica no vault porque um teste compararia os dois lados. **Nada disso
corresponde ao estado real:** a tabela não existe nem aqui nem no espelho do
vault; `ZoneIntegrityTest` (`tests/test_plan.py`) compara `src/coach.py:ZONE_BANDS`
com um literal dentro do próprio teste e não lê nenhum markdown. O que existe é o
bloco `ZONE_BANDS` da seção 4, com faixas de %FTP. Escrever a tabela é trabalho de
pesquisa com escopo próprio, com PMID por zona: não deve ser inferida nem
fabricada para satisfazer uma referência antiga.
