# Prova Endurance e Hermes Coach — arquitetura, produto e evidência científica — 2026-10-22

> [!info] Dono deste documento
> Fonte canônica: `docs/research/PROVA-ENDURANCE-ANALISE-COMPARATIVO-HERMES-2026-10-22.md` **no repo**
> (o mesmo arquivo do vault é cópia). Quando divergirem, o repo vence.
> Editar no repo e copiar.
> Espelho: `~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/PROVA-ENDURANCE-ANALISE-COMPARATIVO-HERMES-2026-10-22.md`.

## Escopo e método

**Pergunta.** O que é o [Prova Endurance](https://provaendurance.com/en/how-it-works), como ele
funciona por dentro, o que a camada científica dele sustenta e o que disso é comparável ao Hermes
Coach deste checkout?

**Corte e evidência.** Páginas públicas do Prova (`/en/` e `/pt/`, `how-it-works`, `faq`, `tour`,
`setup`, `privacy`, `terms`), metadados do endpoint MCP e do servidor de autorização observados em
2026-10-23 UTC, o tópico oficial do fundador no fórum do Intervals.icu e os registros
bibliográficos/abstracts das seis referências citadas na página. Não fiz login, não executei o app,
não gerei plano, não conectei Intervals/Wahoo/Hammerhead e não testei sync com dispositivo. O código
do Prova é proprietário; a arquitetura abaixo é **declarada** pelo produto ou **inferida** de
metadados observáveis, não lida em fonte.

**Hierarquia de leitura.**

1. **Contrato declarado** — privacy policy, terms, página “how it works”, respostas do FAQ.
2. **Comportamento observável** — endpoint MCP, `/.well-known/oauth-protected-resource`,
   `/.well-known/oauth-authorization-server`, headers HTTP.
3. **Declaração do fundador** — tópico oficial no fórum, incluindo números de tração e o bug de
   refresh token. É autoafirmação, não auditoria independente.
4. **Evidência científica** — metadados e abstracts via Europe PMC; não li os textos completos.
5. **Marketing** — home, tour e frases de posicionamento. Não tratei como prova de capacidade.

“Não documentado” significa “não encontrei declaração na fonte consultada”; não significa que a
capacidade não exista. O Prova é jovem e o site pode mudar depois desta data.

## O que o Prova é

O Prova Endurance é um **serviço de coaching de endurance que vive dentro do app de IA do usuário**.
Ele não tem modelo de IA próprio. O usuário conversa com Claude, ChatGPT, Gemini, Le Chat ou Claude
Code; o cliente de IA faz o raciocínio e escreve o plano; o Prova guarda estado, calcula números,
valida o plano contra regras e mantém a pesquisa que a IA cita [P1][P2][P3][P7].

O produto declara cinco esportes — ciclismo, corrida, natação, remo e força —, com uso concentrado
em ciclismo, esporte do fundador [P3]. O estágio é inicial: o fundador anunciou o produto no fórum
do Intervals.icu em 2026-09-28 dizendo que era o único atleta; em 2026-10-03 relatou 20 atletas
registrados e mais de 11 mil atividades importadas [P9]. São números autoafirmados. O Domain
Arrivals já havia observado a landing page em 2026-09-22 [P10], então “lançamento” aqui é o anúncio
público, não a primeira aparição do site.

O modelo de negócio é **gratuito para atletas**. A justificativa é econômica: a inferência acontece
na conta de IA do próprio usuário, então o Prova não paga conta de modelo e não precisa cobrar por
isso. Os termos dizem que, se o preço mudar, a mudança não se aplica ao que o atleta já usa [P3][P7].

## Arquitetura e modelo de decisão

### Quatro papéis

| Papel | Responsabilidade declarada |
|---|---|
| **Atleta** | Diz o objetivo, a disponibilidade e como o treino está indo; tem a última palavra sobre o plano. |
| **App de IA do atleta** | Conversa, faz o raciocínio, escreve o plano, explica cada sessão e propõe mudanças. |
| **Prova Endurance** | Guarda plano, histórico e thresholds; lê cada atividade; valida planos e mudanças contra regras; mantém a pesquisa citada. **Não roda modelo de IA.** |
| **Plataforma/dispositivo** | Atividades entram do Intervals.icu ou de export do Garmin Connect; sessões saem para o calendário do Intervals.icu ou como `.fit` para relógio/ciclocomputador. |

Fonte: [P1][P2]. A frase “It runs no AI model of its own” aparece na página “how it works” e é
repetida na privacy policy e nos terms [P2][P6][P7].

### O fluxo

1. **Anamnese.** A IA faz a entrevista que um treinador faria: objetivo, outras provas, horas e dias
   disponíveis, lesões, esportes e o que o atleta sabe sobre a própria frequência cardíaca. Depois lê
   o histórico. Sem histórico, começa com cautela [P2].
2. **A IA escreve o plano.** Cada sessão tem um motivo: a pesquisa em que se apoia ou uma nota
   explícita de que é julgamento da IA [P2][P4].
3. **O servidor valida.** O plano é checado contra regras que leem horas semanais, quantidade e
   espaçamento de sessões duras e tempo em cada intensidade. Se uma regra não serve ao atleta, ele
   pode escrever a própria exceção, nas próprias palavras. O plano fica esperando aceite ou recusa
   [P2].
4. **O atleta treina.** Sessões aceitas vão para o calendário do Intervals.icu ou para o dispositivo
   como `.fit`, com o objetivo e os passos [P2][P4].
5. **O Prova lê o que foi feito.** Cada atividade é pareada com a sessão planejada; o atleta pode
   dizer como se sentiu e dar uma nota. O Prova descreve a sessão contra os thresholds do atleta:
   tempo abaixo do primeiro limiar, entre os dois e no/acima do segundo, lido de potência ou pace e
   de FC, lado a lado. Cada semana é comparada com as semanas recentes do atleta e rotulada como
   *building*, *steady*, *backing off* ou *spiking*, com os números por trás da palavra [P2].
6. **A IA adapta.** O atleta conta o que mudou; a IA propõe uma nova versão, checada contra as mesmas
   regras, para aceite ou recusa [P2].

### O “juiz” e a exceção de automação

Na descrição que o fundador publicou — rotulada por ele mesmo como **gerada por LLM** —, há um
“judge” no servidor que checa progressão de carga, carga semanal, espaçamento entre sessões duras,
semanas de recuperação, distribuição das sessões leves e estrutura de taper [P9]. A página pública é
mais genérica: horas semanais, número e espaçamento de sessões duras e tempo em cada intensidade
[P2]. O rótulo importa: a descrição detalhada é uma peça de comunicação, não o contrato do servidor.

A regra de ouro é: **a IA propõe, o atleta aceita ou recusa, e a decisão é registrada**. Há uma
exceção explícita: depois que um plano está aprovado e rodando, a **semana seguinte é preenchida
automaticamente** como prescrição semanal e enviada por e-mail; o atleta pode mudar depois, pedindo
[P2][P3][P9]. Essa exceção é importante: o produto troca aprovação prévia por continuidade e
notificação posterior, mas só para a semana seguinte de um plano já aceito.

### MCP e OAuth — o que é observável

O endpoint é `https://api.provaendurance.com/mcp`, anunciado como **Streamable HTTP, OAuth 2.1 com
dynamic client registration** [P5]. Sem token, o endpoint responde `401` com:

```text
www-authenticate: Bearer resource_metadata="https://api.provaendurance.com/.well-known/oauth-protected-resource"
```

O metadado do recurso declara `resource` igual ao endpoint MCP e o próprio servidor como
authorization server. O metadado do authorization server declara:

- `authorization_endpoint` e `token_endpoint` no mesmo host;
- `registration_endpoint` (dynamic client registration);
- `response_types_supported: ["code"]`;
- `grant_types_supported: ["authorization_code", "refresh_token"]`;
- `code_challenge_methods_supported: ["S256"]` (PKCE);
- `token_endpoint_auth_methods_supported: ["none"]` (cliente público);
- escopos `openid`, `profile`, `email`, `offline_access` [P8].

O servidor responde com `Kestrel` e `strict-transport-security`, o que é consistente com ASP.NET Core
no backend; isso é observação de header, não documentação do produto [P8].

O fundador relata um bug real e a correção: o servidor estava reutilizando o refresh token da sessão
web para a conexão do app de IA. Como o provedor rotaciona refresh tokens (single-use), dois
portadores do mesmo token não conseguem renovar; quem renova primeiro invalida o outro. A correção
foi dar a cada conexão de app de IA um grant próprio via **RFC 8693 token exchange** [P9]. É um
detalhe de implementação, mas é exatamente o tipo de falha que aparece quando OAuth é tratado como
“login” e não como **grant por conexão**.

### O que o Prova não faz

- Não roda modelo de IA próprio; a inferência é do cliente escolhido [P2][P6][P7].
- Não tem tabela de zonas própria; usa os thresholds do atleta ou a tabela de zonas que o atleta
  fornecer à IA [P2].
- Não estima potência nem pace; esses thresholds ficam vazios até o atleta informar ou fazer teste.
  FC máxima pode ser estimada ou vir da maior FC do histórico, e é rotulada como estimativa; a base
  da estimativa é auditada adiante [P2].
- Não exibe um score de prontidão, nem um score de fitness/fadiga [P2].
- Não vende dados nem os compartilha fora dos serviços que o atleta conecta [P6].

## Estado, dados e proveniência

### O que o Prova guarda

| Categoria | Conteúdo declarado |
|---|---|
| Conta | Nome e e-mail do login Google; data e forma de chegada ao site. |
| Perfil do atleta | Nome escolhido, data de nascimento, sexo, fuso horário. |
| Treino | Arquivos originais enviados ou sincronizados; duração, distância, potência, FC, cadência, velocidade, altitude, voltas, training load e curvas de esforço. |
| Saúde/wellness | Peso, sono, RHR, HRV e dor muscular, quando fornecidos ou importados. |
| O que o atleta diz | Respostas da anamnese, notas, declarações, plano e decisões aceitas/recusadas. |
| Credenciais | Tokens de acesso de Intervals.icu, Wahoo e Hammerhead. |

Fonte: [P6]. A política trata treino e saúde como dados sensíveis sob a LGPD (Art. 11) e o GDPR
(Art. 9), com consentimento específico e explícito na criação do atleta [P6].

### Thresholds e zonas

O Prova mostra, em “Your numbers”, FC máxima, FTP e pace de limiar, com valor, data de vigência e
origem [P4]. A regra declarada é:

- **potência e pace nunca são estimados**; ficam vazios até o atleta dar um valor ou fazer um teste;
- **FC máxima** pode ser a maior FC do histórico ou uma estimativa por idade/sexo, rotulada como
  estimativa;
- se um threshold falta, um plano de várias semanas nomeia um teste que o mediria; depois do teste, o
  Prova lê o resultado e **propõe** o valor [P2].

O produto **não tem tabela de zonas própria**. Os dois limiares dividem cada esporte em três domínios:
abaixo do primeiro, entre os dois, no/acima do segundo. Se o atleta der à IA a própria tabela de
zonas, ela pode ser usada [P2]. Na prática, as sessões mostram alvos em percentuais (por exemplo,
76–85%, 55%, 50%) [P4], então “sem tabela de zonas” não significa “sem modelo de intensidade”:
significa que o modelo é do atleta, não do fornecedor.

Há uma inconsistência menor entre páginas: “how it works” fala em **três** domínios; a home e o tour
mostram **quatro** buckets — D1 (abaixo do primeiro limiar), D1-2 (“around your first threshold”),
D2 (entre os limiares) e D3 (no/acima do segundo) [P1][P4]. Não está documentado se D1-2 é um domínio
separado ou uma faixa de incerteza em torno do primeiro limiar. É a mesma classe de problema de
fronteira que o Hermes trata em `zone_intent.classify()` na sobreposição de 91–97% FTP: a diferença é
que o Prova resolve por exibição e o Hermes por recusa a adivinhar.

### “Fitness é o threshold ao longo do tempo”

O Prova rejeita um score único de fitness/fadiga e define: “Your fitness is your thresholds over
time” [P2]. A privacy policy, porém, lista “training load” entre os dados computados [P6], e a
descrição gerada por LLM que o fundador publicou diz que o servidor calcula “training load, fitness
and zones” [P9]. A leitura correta é: **o cálculo existe internamente; a decisão de produto é não
transformá-lo em score exibido**. Isso é diferente de “não calcular carga”.

### Prontidão

RHR e HRV são lidos como **média de vários dias contra o baseline do atleta**. Quando os valores
derivam muito, a IA traz o assunto; **a leitura isolada nunca muda o plano**. Não há readiness score.
O relato subjetivo do atleta vem primeiro [P2].

### Proveniência

O Prova é explícito em três níveis:

1. **Sessão** — cada sessão diz por que está ali: pesquisa citada ou “julgamento do treinador” [P2][P4].
2. **Threshold** — valor, data de vigência e origem [P4].
3. **Ação da IA** — a aba Coach lista propostas, decisões, mudanças de perfil, e-mails e chamadas que
   a IA fez aos dados; o atleta pode revogar o acesso do app de IA [P2][P4][P9].

É a parte mais forte do produto. O “porquê” não é um texto de marketing: é um campo do registro.

## Regras de treino e fisiologia

### O que é público

- Cerca de **duas sessões duras por semana**, com contagem e espaçamento entre elas [P2].
- **Horas semanais** e **tempo em cada domínio de intensidade** como entradas das regras [P2].
- Regras com **fonte científica** ou marcadas como **julgamento** [P2][P9].
- **Exceções do atleta** às regras, escritas nas palavras dele [P2].
- **Semana seguinte preenchida automaticamente** e enviada por e-mail, alterável depois [P2][P3].
- **RHR/HRV em média multi-dia**; leitura isolada não muda o plano [P2].
- **Subjetivo primeiro**; nenhum readiness score [P2].
- **Sessão perdida** não dispara replanejamento total; a semana seguinte é escrita a partir do que
  aconteceu, não do que o plano esperava [P9].
- **Estrutura de taper e semanas de recuperação** entram no “judge” [P9].

### O que não é público

- A definição operacional de “sessão dura”: tempo em D3? intenção da sessão? um limiar de TSS? [P2][P9].
- A fórmula exata de progressão de carga, recovery week e taper [P9].
- A tolerância de pareamento atividade ↔ sessão planejada [P2].
- O que acontece se o atleta nunca fizer o teste que o plano nomeia [P2].
- O conteúdo completo do corpus de 110 papers; a página pública lista 6 referências [P2][P9].

### Comparação com os guardrails do Hermes

O Hermes tem guardrails mais “de motor” e menos “de catálogo”: orçamento semanal de TSS, pisos de
zona, espaçamento de sessões duras, recuperação ativa não absorvível, Limiar/VO2 perdido não
substituído por volume, preservação do treino iniciado, gates de FTP e push idempotente [H1][H2].
O Prova tem um **catálogo de regras com fonte ou julgamento** e um veredito de plano (“Passes every
training rule”) visível ao atleta [P2][P4]. São camadas diferentes: o Hermes tem a mecânica; o Prova
tem a **explicação auditável** da mecânica.

## Integrações e fluxo de dispositivo

| Direção | Prova | Observação |
|---|---|---|
| Entrada | Intervals.icu; export do Garmin Connect; upload de `.fit`, `.gpx` (o fundador cita também `.zip`); Wahoo; Hammerhead | A página oferece **export de arquivo** do Garmin Connect e não lista uma conexão Garmin; o fundador diz que o dele sincroniza com Garmin automaticamente, no contexto do Intervals [P2][P5][P9]. |
| Saída | Calendário do Intervals.icu; `.fit` para relógio/ciclocomputador; e-mail semanal | O `.fit` é entregue pelo produto; a autoria dos passos (IA vs schema do servidor) não está documentada [P2][P5]. |
| Revogação | Desconectar Intervals/Wahoo/Hammerhead na página de Integrations; revogar app de IA na aba Coach | A revogação do app impede renovação; o acesso já concedido dura até expirar [P3][P6]. |

**Ressalva Strava.** O fundador relata que o Strava não permite que terceiros baixem dados que foram
sincronizados do Strava para o Intervals; sessões com origem Strava podem não chegar ao Prova [P9].
É uma restrição de plataforma, não um bug do Prova — e vale para qualquer produto que leia o
Intervals, inclusive o Hermes.

## Privacidade, deploy e modelo de negócio

- **Onde fica:** banco e file store próprios do Prova, em servidores no Brasil, não em cloud de
  terceiro. O cliente de IA escolhido pode estar em outro país; o que ele lê vai para lá porque o
  atleta o conectou [P6].
- **Base legal:** LGPD Art. 11 e GDPR Art. 9; consentimento específico e explícito na criação do
  atleta [P6].
- **Exclusão:** o atleta exclui a conta no app; a exclusão remove perfil, treino, saúde, arquivos,
  planos, decisões, credenciais e registros de conta, e revoga o acesso em todos os serviços
  conectados. O serviço de login mantém nome/e-mail Google para permitir novo login; backups rotam
  em 7 dias [P6].
- **Cookies:** dois essenciais (sessão e CSRF), nenhum de anúncio ou tracking [P6].
- **Controlador:** Tessarolli Bike Shop Indústria e Comércio de Bicicletas Ltda
  (CNPJ 38.438.179/0001-36), Lins, SP [P6][P7].
- **Preço:** gratuito para atletas; se mudar, não se aplica ao uso já existente [P7].
- **Custo de IA:** zero para o Prova; a conta é do usuário, no app de IA dele [P3].

O trade-off é claro: o Prova evita a conta de modelo e o custo de servir LLM, mas **centraliza dados
sensíveis** e os envia ao provedor de IA escolhido. A privacy policy é boa para um projeto pequeno:
diz onde os dados ficam, quem os vê, o que a exclusão remove e o que sobra nos backups. Ainda assim,
não encontrei auditoria de segurança, certificação ou teste de penetração divulgados publicamente; o controlador é
uma loja de bicicletas, não uma empresa de infraestrutura. Isso é risco de continuidade e de
maturidade operacional, não má-fé.

## Evidência científica: auditoria das seis referências

A página “how it works” lista seis referências e liga cada uma a uma decisão do produto [P2]. Todas
as seis têm DOI válido e metadados que batem em título, autores, revista, ano, volume e páginas
contra o Europe PMC [R1–R6]. **Não há referência inventada.** A pergunta seguinte é outra: a citação
sustenta a frase que o produto coloca ao lado dela?

| # | Referência | Frase do Prova | O que o abstract sustenta | O que o abstract não sustenta / ressalva |
|---|---|---|---|---|
| 1 | Passfield et al. 2022, *Validity of the Training-Load Concept* [R1] | “Training load nunca foi validado como medida de dose; pode ser melhor mostrar tempo em cada domínio.” | “TL has never been validated as a measure of training dose”; a maioria das métricas não é consistente com a dose; a duração confunde o cálculo. | A recomendação específica de “mostrar tempo em cada domínio” **não aparece no abstract**; o texto pede novas métricas, não prescreve time-in-zone. É inferência de produto. A frase “multiplica duração por dificuldade” simplifica TSS (que usa IF²), embora a crítica de confusão com duração seja real. |
| 2 | Seiler & Kjerland 2006 [R2] | “Dois limiares dividem em três domínios; um estudo de atletas de elite treina assim.” | VT1 e VT2 delimitam três zonas; 11 esquiadores juniores bem treinados, 32 dias, distribuição ~75/8/17%; padrão polarizado. | A amostra é de **esquiadores juniores**, não de “elite endurance athletes” em geral; o abstract compara com estudos observacionais de elite, mas não prova distribuição ótima para todos. |
| 3 | Seiler 2010 [R3] | “Cerca de duas sessões duras por semana bastam; mais tende a overreaching.” | ~80% baixa intensidade e ~20% alta em atletas que treinam 10–13 sessões/semana; menos bouts intensos; intensificação não mostra ganho de longo prazo em atletas já treinados. | “Duas por semana” é **derivado** de 20% de 10–13 sessões; “mais tende a overreaching” **não está no abstract**. A população é altamente treinada; não é regra para recreacional com 8 h/semana. |
| 4 | Nes et al. 2013 [R4] | “Fórmula de FC máxima por idade e sexo; o erro deve ser considerado.” | Fórmula `211 − 0,64 × idade`; SEE 10,8 bpm; **sem interação com sexo**; o erro deve ser considerado. | A fórmula é **só idade**, não idade-e-sexo. O Prova diz “age-and-sex” em dois lugares [P2]; a fonte citada não tem termo de sexo. O erro de 10,8 bpm é grande para usar FC estimada como alvo fino. |
| 5 | Buchheit 2014 [R5] | “RHR/HRV são médias porque, em atletas de endurance, só acompanharam performance de corrida quando mediram 3–4 dias.” | Medidas de 5 min quase diárias; interpretar com erro de medida, menor mudança importante e contexto de treino; FC não informa tudo. | “3–4 dias” e “running performance” **não aparecem no abstract**; podem estar no texto completo, mas não são verificáveis aqui. A média multi-dia é defensável, mas a citação é mais específica que o abstract. |
| 6 | Saw et al. 2016 [R6] | “Relatos subjetivos refletem o treino com mais sensibilidade e consistência que medidas objetivas; sem readiness score.” | Revisão sistemática de 56 estudos; subjetivo > objetivo em sensibilidade/consistência; pode ser usado sozinho ou em abordagem mista. | “Sem readiness score” é **decisão de produto**, não achado; a revisão é de atletas em geral, não específica de endurance; não prova que o subjetivo basta. |

### O que essa auditoria mostra

1. **A camada de citação é real, não decorativa.** Seis de seis DOIs existem e os metadados batem.
   Isso é melhor que o padrão de produtos que citam papers fabricados.
2. **O problema é de ajuste entre frase e fonte, não de existência.** Duas citações são fortes para a
   frase (Passfield na crítica central, Saw na superioridade do subjetivo), duas são parciais
   (Seiler & Kjerland pela amostra; Nes pela fórmula) e duas são mais específicas que o abstract
   (Seiler 2010 e Buchheit).
3. **O rótulo “fonte ou julgamento” é a mitigação certa, mas precisa ser aplicado à regra, não só à
   sessão.** “Cerca de duas sessões duras” é uma **heurística de produto derivada** de um estudo de
   atletas altamente treinados; não é um achado de que duas seja o número certo para todos. O Prova
   chama isso de “review found about two a week enough”, o que soa mais forte que a fonte.
4. **O corpus de 110 papers não é público.** A página expõe 6; o fundador afirma 110 papers [P9]. Não
   é possível auditar as outras 104, nem saber se o corpus é atualizado, versionado ou revisado.
5. **“Sem zone table” não é “sem modelo”.** O produto usa percentuais de threshold e uma divisão em
   domínios; é um modelo mais enxuto, não a ausência de modelo. A diferença em relação ao Hermes é
   de **compromisso declarado**: o Hermes assume `ZONE_BANDS` como modelo computacional verificado
   [H3][H5]; o Prova evita a tabela canônica e deixa o modelo de zonas por conta do atleta.

## Comparação factual com Hermes Coach

Fontes entre colchetes; a coluna do Hermes refere-se ao checkout de 2026-10-22.

| Eixo | Prova Endurance | Hermes Coach (checkout 2026-10-22) |
|---|---|---|
| **Forma e estágio** | SaaS web + MCP; gratuito; anúncio público no fórum em 2026-09-28; 20 atletas/11k atividades autodeclarados em 2026-10-03 [P9]. | CLI local + `plan.json`; single-athlete; sem servidor/MCP [H1]. |
| **Decisão** | LLM do usuário escreve o plano; servidor valida contra regras; humano aceita/recusa [P2]. | Motor Python determinístico escreve o plano; humano aprova `check --apply`/`push`; LLM fora do caminho produtivo [H1]. |
| **Papel do LLM** | Planejador, explicador e proponente; não muta sozinho, exceto a semana seguinte de plano já aceito [P2][P3]. | Ausente no fluxo produtivo; MCP/Coach+ são roadmap #13/#29 [H4]. |
| **Fonte de verdade** | Estado no servidor: perfil, histórico, thresholds, plano, decisões e corpus [P2][P6]. | `plan.json` + motor + Intervals PMC; FTP history/evidence [H1][H3]. |
| **Thresholds/zonas** | Sem tabela de zonas própria; 2 limiares → 3 domínios (UI mostra 4 buckets); potência/pace nunca estimados; FCmax estimada e rotulada [P2][P4]. | `ZONE_BANDS` com 7 zonas em %FTP; FTP operacional; pisos de zona; Z7 fora da faixa [H5]. |
| **Modelo de carga** | Calcula training load, mas não exibe score único; mostra tempo por domínio; “fitness = thresholds over time”; sem CTL/ATL/TSB exibido [P2][P6]. | CTL/ATL/TSB do Intervals; orçamento de TSS; Banister para projeção; TSB governa foco [H1]. |
| **Prontidão** | RHR/HRV em média multi-dia vs baseline; leitura isolada não muda o plano; sem readiness score; subjetivo primeiro [P2]. | `check` com RHR/HRV/sono/readiness; sinal isolado pode reduzir volume (proposta); classificação GREEN/YELLOW/RED [H1][H6]. |
| **Regras** | ~2 sessões duras/semana, espaçamento, horas, tempo por domínio, recovery/taper; fonte ou julgamento; exceções do atleta [P2][P9]. | TSS budget, pisos de zona, espaçamento, recuperação ativa não absorvível, Limiar/VO2 perdido não compensado, preservação do treino iniciado, gates de FTP [H1][H2]. |
| **Aprovação/mutação** | Proposta → aceite/recusa → publicação; exceção: próxima semana auto-aplicada e e-mail [P2][P3]. | `check` propõe → `--apply` local → `push`; timer diário opcional faz `reconcile + push`; sem ledger geral de propostas/decisões — `plan.json` guarda plano e metadados [H1]. |
| **Integrações** | Intervals, export Garmin, FIT/GPX/ZIP, Wahoo, Hammerhead; `.fit`; calendário; e-mail [P2][P5][P9]. | Intervals API; calendário; depende do Intervals para `.fit`/`.zwo`/`.erg`/`.JSON`/`.MRC`; sem geração local, e-mail ou device direto [H1]. |
| **Multi** | 5 esportes; multi-atleta SaaS [P3]. | Ciclismo indoor + protótipo de corrida; single-athlete; multi-atleta roadmap #8/#24 [H1][H4]. |
| **Auth/privacidade** | Login Google; MCP com OAuth 2.1/DCR/PKCE; servidor próprio no Brasil; LGPD/GDPR; dados vão ao AI client [P6][P8]. | API key no `.env`; local-first **hoje**; servidor próprio no roadmap #23–#26 (portal, banco, API, workers); sem auth/MCP [H1][H4]. |
| **Negócio** | Grátis; inferência na conta do usuário; sem venda de dados [P3][P7]. | Open-source/local; sem modelo de negócio; SaaS planejado [H4]. |
| **Evidência** | 6 refs públicas + corpus de 110 (alegado); fonte/julgamento por sessão [P2][P9]. | 45 refs; §15 com matriz de 14 features; verificação offline/online; não exposto por sessão no produto [H3]. |
| **Testes/evals** | Não há suíte pública divulgada; cobertura das regras não verificável [P2][P9]. | 1.548 testes; sem eval de LLM em dataset [H7]. |

### O que o Prova faz melhor

1. **Proveniência no produto.** Cada sessão e cada regra mostram fonte ou julgamento; a aba Coach
   registra propostas, decisões e chamadas de ferramenta. O Hermes tem a documentação científica,
   mas não expõe esse “porquê” como registro rastreável por decisão (regra, fonte, veredito) no
   produto [P2][P4][H3].
2. **Aprovação como estado de primeira classe.** “Waiting for you”, “Accept/Decline”, “Passes every
   training rule” e o timeline são um contrato de produto, não um log de CLI [P4]. No Hermes, isso
   é **hipótese** enquanto o plano for semanal; ganha força se o treino passar a mudar diariamente
   (ver `MCP-AGENTE-E-ADAPTACAO-DIARIA-2026-10-23.md`).
3. **Onboarding sem instalação.** O atleta cola uma URL no app de IA e autentica com Google; não
   precisa de Python, `.env` ou API key [P5]. Isso amplia o alcance para quem não é engenheiro,
   mas transfere a inferência e parte dos dados ao app de IA escolhido; o Hermes pode preferir um
   agente hospedado (ver o mesmo documento).
4. **Alcance de dispositivo e esporte.** `.fit` para relógio/ciclocomputador, Intervals, Garmin
   export, Wahoo, Hammerhead e cinco esportes [P2][P3][P5]. O Intervals também expõe `.fit`,
   `.zwo`, `.erg`, `.JSON` e `.MRC`; a diferença do Prova é o **alcance direto**, não a
   existência do formato.
5. **Política de privacidade específica.** Localização dos dados, exclusão, backups, subprocessadores
   e base legal estão escritos; para um projeto de uma pessoa, é acima da média [P6].

### O que o Hermes faz melhor

1. **Motor determinístico e testável.** 1.548 testes, pisos de zona, orçamento de TSS, reconciliação,
   preservação de treino iniciado e push idempotente [H1][H7]. O Prova terceiriza a autoria do plano
   ao LLM e depende da cobertura das regras para conter erro.
2. **Privacidade local-first hoje.** API key no `.env`, sem servidor central, sem enviar saúde a um
   LLM [H1]. O Prova centraliza dados sensíveis e os envia ao provedor de IA escolhido [P6]. O
   servidor próprio está no roadmap; quando existir, o modelo de privacidade muda (auth,
   isolamento, retenção, subprocessores).
3. **Contrato fisiológico mais profundo.** 45 referências, §15 com 14 features e a coluna “o que o
   estudo NÃO mostra”, distinção entre evidência, heurística e modelo computacional [H3]. O Prova tem
   6 referências públicas e um corpus fechado de 110 papers não auditáveis [P2][P9].
4. **Maturidade operacional no nicho.** `check`/`apply`/`push`, `--dry-run`, limpeza de órfãos,
   bootstrap no Intervals, `recovery`, `summary`, `model`, `periodization` [H1]. O Prova é um produto
   mais amplo, mas mais jovem e sem suíte pública divulgada.
5. **Independência de cliente de IA.** O Hermes não depende de menus de Claude/ChatGPT/Gemini nem de
   um conector MCP que pode mudar [P5]. O Prova depende disso por desenho.

### O que é apenas diferente

- **Zonas:** o Prova evita uma tabela canônica; o Hermes assume `ZONE_BANDS` como modelo computacional
  verificado e o documenta [H3][H5]. Não é “certo vs errado”: é **compromisso explícito vs
  flexibilidade do atleta**.
- **Carga:** o Prova rejeita um score único e mostra tempo por domínio; o Hermes usa CTL/ATL/TSB como
  referência operacional e orçamento. Ambos são modelos; o Hermes documenta mais o seu, o Prova
  expõe menos o modelo de carga que usa.
- **Prontidão:** o Prova exige média multi-dia e não age por leitura isolada; o Hermes pode reagir a
  um sinal isolado, mas como proposta. A diferença é de **política de ruído**, não de aprovação.
- **Autoria:** o Prova aposta que o LLM, cercado de regras, escreve melhor que um motor fixo; o
  Hermes aposta que o motor fixo, cercado de dados, decide melhor que um LLM. Cada um tem um modo de
  falha distinto.

## Padrões aproveitáveis

### 1. Catálogo de regras com proveniência (P0)

O Prova mostra, por sessão, a fonte ou o julgamento; o Hermes tem a matriz §15, mas ela é
documentação, não um contrato de runtime [P2][H3]. O padrão a copiar é o **registro de decisão**:

```text
DecisionRecord
  id, created_at, actor
  rule_id, rule_kind: evidence | heuristic | model
  source_id: DOI/PMID | JUDGMENT | NONE
  scope: plan | week | session | readiness | ftp
  inputs: { ... }
  outcome: { ... }
  reason: string
  confidence: number | null
```

Isso é a productização da §15: cada linha da matriz vira uma referência de regra; cada decisão
aponta para uma regra; cada regra declara o que a fonte **não** mostra. Sem esse contrato, a aba
“porquê” de um futuro Coach+ seria texto solto.

### 2. Ledger de propostas e aprovação (P0/P1)

O Prova trata proposta, aceite, recusa e timeline como estado [P4]. O Hermes tem `check` → `--apply`
→ `push`, mas não persiste uma proposta com diff, veredito e expiração [H1]. Um `ProposedChange` com
`base_plan_hash`, `diff`, `rule_verdicts`, `status` (`pending|accepted|declined|expired|applied`) e
`expires_at` é pré-requisito para qualquer interface conversacional ou MCP. O `check` atual já tem a
matéria-prima; falta o registro.

### 3. Grant OAuth por conexão (P1, se houver MCP)

O bug do Prova é a melhor aula: refresh token single-use compartilhado entre sessão web e app de IA
quebra a renovação; a correção foi grant próprio por conexão via RFC 8693 [P9]. Se o Hermes expuser
MCP, o contrato mínimo é OAuth 2.1 + DCR + PKCE S256 + cliente público + refresh rotation +
**grant por conexão** + revogação + audit log. O metadado do Prova é um bom modelo de discovery
[P8]. O teste “dois portadores do mesmo refresh token” deve entrar na suíte.

### 4. Política de wellness multi-dia (P1)

O Prova exige média de vários dias e não muda o plano por leitura isolada [P2]. O Hermes pode reduzir
volume com um sinal isolado ruim (proposta) [H1]. Para wearables de consumer, a política do Prova é
mais robusta a ruído e alinhada ao cuidado de “erro de medida / menor mudança importante” [R5]. O
Hermes não precisa copiar o “sem readiness score”, mas pode copiar a **janela mínima** e o **limiar de
mudança** antes de agir; o alerta de doença (RHR subindo 2+ noites + HRV caindo) continua sendo uma
exceção válida.

### 5. Tempo por domínio ao lado do PMC (P2)

O Prova mostra D1/D1-2/D2/D3 e evita um score único; combina isso com uma leitura semanal
qualitativa (*building*, *steady*, *backing off*, *spiking*) e os números por trás [P2][P4]. O Hermes
já tem `intensity_distribution.py` com LOW/MOD/HIGH, mas ele não está no fluxo de publicação atual
[H1]. Expor tempo por domínio no `summary`/relatório, ao lado de CTL/ATL/TSB, responde à crítica de
Passfield sem jogar fora o TSS. A borda de 91–97% FTP já é tratada por `zone_intent.classify()`; a
visualização deve dizer qual é a base (%FTP, threshold do atleta) e como a borda foi resolvida.

### 6. Saída `.fit` e independência de dispositivo (P2)

O Prova entrega `.fit` e calendário [P2][P5]. O Hermes depende do Intervals, que **já expõe**
`.fit`, `.zwo`, `.erg`, `.JSON` e `.MRC`; não gera o arquivo localmente [H1]. O gap real é
**independência de dispositivo/ecossistema**, não ausência de formato: para quem usa Intervals, o
`.fit` está resolvido. Gerar `.fit` estruturado localmente só amplia o alcance para quem não usa
Intervals. É um gap de produto, não de motor; o LLM não deve escrever a sintaxe do arquivo.

### 7. “Bring your own inference” (condicional)

O Prova é grátis porque a conta de IA é do usuário [P3][P7]. Se o Hermes for para SaaS, esse modelo
é uma opção: o motor determinístico fica no centro; o usuário traz o cliente de IA; o Hermes cobra
por hospedagem, sync e dashboard, não por token. O custo é que os dados passam pelo provedor de IA e
o produto fica dependente do suporte MCP do cliente. Não é uma decisão para agora; é uma alternativa
arquitetural documentada.

### 8. Modelo de dados multi-esporte (P2)

O Prova declara cinco esportes [P3]. O Hermes tem ciclismo indoor produtivo e corrida em protótipo
[H1]. Se o catálogo de regras/ledger for multi-esporte, o `sport` precisa estar no contrato desde o
começo (já aparece no roadmap #18), sem presumir potência em corrida/natação. Não é razão para
pressa; é razão para não hard-code “ciclismo” na camada de decisão.

## Anti-patterns e riscos

1. **LLM como autor com regras como única barreira.** O Prova mitiga com validação no servidor e
   aprovação humana, mas a qualidade depende da cobertura das regras. Se falta uma regra, o LLM pode
   escrever um plano plausível e inseguro; o humano pode aceitar sem ler. O Hermes não deve inverter
   seu motor para esse modelo [P2][P9].
2. **Apresentar heurística como achado.** “Cerca de duas sessões duras” é derivado de 80/20 em
   atletas altamente treinados; a página soa como se o estudo tivesse dito “duas”. O mesmo vale para
   “idade e sexo” na FCmax. É o erro que o AGENTS do Hermes proíbe: confundir evidência, heurística e
   modelo [H2][R3][R4].
3. **Auto-aplicar a semana sem aprovação prévia.** A exceção do Prova é deliberada e notificada por
   e-mail, mas ainda é uma semana que chega antes de o atleta vê-la [P2][P3]. Para o Hermes, manter
   aprovação explícita antes de `push` é mais seguro, especialmente para Limiar/VO2.
4. **Centralizar saúde em operador pequeno sem modelo de segurança público.** A política do Prova é
   boa, mas o controlador é uma loja de bicicletas e não encontrei auditoria pública [P6][P7].
   Local-first é um diferencial de confiança do Hermes **hoje**; se o servidor próprio entrar no
   roadmap, não abrir mão dele sem threat model, criptografia, retenção e revogação.
5. **Depender do menu de MCP de terceiros.** Gemini só EUA/inglês/18+; ChatGPT não funciona no free;
   Claude free tem um conector; menus mudam [P3][P5]. O onboarding do Prova é frágil por desenho. O
   Hermes não deve trocar a CLI por uma dependência de UX de terceiro sem fallback.
6. **Tratar tamanho de corpus como validação.** “110 papers” não é evidência de que as regras estão
   certas; é tamanho de biblioteca [P9]. O Hermes deve continuar medindo **ajuste frase↔fonte** e
   cobertura de regras, não contagem de PDFs.
7. **“Sem zone table” como marketing que omite o modelo.** O Prova usa percentuais de threshold e
   domínios; é um modelo. O Hermes deve declarar a base de cada alvo e a fronteira de zona, não
   fingir que não há modelo [P2][P4].
8. **Sem eval de outcome.** Nem Prova nem Hermes têm evidência de que os planos melhoram performance
   em população real; os testes do Hermes são de contrato, não clínicos [H7]. Não vender “validado”
   sem estudo prospectivo.

## Recomendações para o Hermes

### P0 — arquitetura

1. **Não inverter o motor.** Manter o motor determinístico como autor do plano. Se o Hermes ganhar
   MCP/LLM, o LLM deve ser **interface e proponente**: coleta intenção, explica, propõe uma mudança
   tipada; o motor valida, calcula e grava. É o oposto do Prova e é o certo para o ativo do Hermes
   [P2][H1].
2. **Implementar o `DecisionRecord`/`RuleRef` antes de qualquer chat.** É o elo que falta entre a
   §15 e o produto; permite “porquê” por sessão, auditoria, eval e futura aba Coach. Sem isso, o
   Coach+ vira texto sem contrato [H3].

### P1 — produto e segurança

3. **Formalizar `ProposedChange` e o ciclo de aprovação.** Reutilizar `check`/`apply`/`push`; agregar
   diff, veredito de regra, status, expiração e ator. O Prova mostra que “Waiting for you / Accept /
   Decline / Passes every rule” é um contrato de produto, não um print de CLI [P4].
4. **Se expuser MCP, escrever o contrato de OAuth antes do código.** OAuth 2.1 + DCR + PKCE + grant
   por conexão + refresh rotation + revogação + audit. Usar o bug do Prova como caso de teste [P8][P9].
5. **Política de wellness multi-dia.** Janela mínima e limiar de mudança antes de reduzir volume;
   manter o alerta de doença; testar HRV/RHR ruidosos. O `check` atual pode continuar propondo, mas
   com menos reação a um único dia [P2][H1][R5].

### P2 — alcance e evidência

6. **Tempo por domínio no `summary`/relatório.** Usar `intensity_distribution.py` e `ZONE_BANDS`;
   mostrar base e tratamento da borda 91–97% [H1][H5].
7. **`.fit` estruturado.** Só se o alvo incluir atletas fora do Intervals; o Intervals já entrega
   `.fit`/`.zwo`/`.erg`/`.JSON`/`.MRC`, então o `.zwo` atual continua válido para o nicho. O `.fit`
   local seria gerado a partir do plano [P2][H1].
8. **Higiene de evidência voltada ao produto.** Toda regra exibida ao atleta deve carregar
   `evidence|heuristic|model` e, quando evidência, o que a fonte **não** mostra. A §15 já tem a
   coluna; falta o runtime [H3].
9. **Multi-esporte no contrato, não no rush.** `sport` no `DecisionRecord`/`ProposedChange`; não
   presumir potência. O Prova cobre 5 esportes, mas o uso real dele é ciclismo/força [P3][P9].

## Questões abertas sobre o Prova

1. Qual é a definição operacional de “sessão dura”? Tempo em D3, intenção, TSS? [P2][P9]
2. Como o “judge” calcula progressão de carga, recovery week e taper? [P9]
3. A IA escreve os passos do treino ou preenche um schema que o servidor renderiza? O `.fit` é
   entregue pelo produto, mas a autoria dos passos não está documentada [P2][P5].
4. Como é feito o pareamento atividade ↔ sessão planejada? Tolerância de duração/potência? [P2]
5. Qual é o comportamento exato em falta, doença e retorno? O fundador descreve “done, done
   differently, skipped”; não há regra pública [P9].
6. O corpus de 110 papers é versionado, revisado e atualizado? Quem aprova? [P9]
7. D1-2 é um domínio separado ou uma faixa de incerteza? A página diz três domínios; a UI mostra
   quatro buckets [P2][P4].
8. A maior FC do histórico é rotulada como “estimativa” ou como “medida”? A página diz “labels it an
   estimate”, mas um máximo observado não é um teste de HRmax [P2].
9. O que acontece se o atleta nunca fizer o teste que o plano nomeia? [P2]
10. Há auditoria de segurança, teste de penetração ou revisão de código independente? [P6][P7]

## Feedback do operador — 2026-10-23

Revisão dos cinco pontos de “O que o Prova faz melhor”, com o status de cada um para o Hermes.
O detalhamento técnico está em
`docs/research/MCP-AGENTE-E-ADAPTACAO-DIARIA-2026-10-23.md`.

| # | Ponto | Status | O que muda |
|---|---|---|---|
| 1 | Proveniência por sessão/regra e aba Coach | **Aprovado como direção** | Productizar a §15 em `DecisionRecord`/`RuleRef`; ledger append-only antes de qualquer UI. |
| 2 | Aprovação como estado (“Waiting/Accept/Decline”) | **Hipótese** | Só ganha valor se o treino mudar diariamente; separar aprovação de plano (semanal) de ajuste diário e testar um envelope antes de construir. |
| 3 | Onboarding via MCP no app de IA do usuário | **A estudar** | O modelo desejado é a plataforma/agente rodando o LLM, não o usuário trazendo Claude/ChatGPT; MCP é distribuição, não requisito. |
| 4 | Alcance `.fit`/Intervals/Garmin/Wahoo/Hammerhead | **Corrigido** | O Intervals disponibiliza `.fit`, `.zwo`, `.erg`, `.JSON` e `.MRC`; o Hermes depende dele e não gera localmente. |
| 5 | Servidor próprio no Brasil | **Corrigido** | Local-first é o estado de hoje; servidor próprio é roadmap, não promessa permanente. |

O que **não** foi decidido: construir a aba Coach, adotar MCP, implementar adaptação diária ou
migrar para servidor próprio. O próximo artefato, se houver aprovação, é a spec do ledger
(`DecisionRecord`/`RuleRef`) — não a UI.

## Limitações desta análise

- Não fiz login, não executei o app, não gerei plano, não conectei serviços e não testei dispositivo.
- O código é proprietário; a arquitetura é declarada/inferida, não lida.
- As declarações do fundador e os números de tração são autoafirmados; não encontrei auditoria independente.
- A auditoria científica é de **abstract**, não de texto completo. Algumas frases podem ser
  sustentadas no full text (especialmente “3–4 dias” em Buchheit e “tempo por domínio” em Passfield);
  onde digo “não verificável no abstract”, não digo “falso”.
- O corpus de 110 papers não é público; auditei 6 referências.
- O site e o produto podem mudar depois de 2026-10-22/23.
- As páginas EN e PT foram consultadas; não encontrei divergência material além da tradução.

## Fontes

### Prova Endurance

- **[P1]** Home EN/PT — <https://provaendurance.com/en/> e <https://provaendurance.com/>. Posicionamento,
  fluxo plan/train/review/adapt, “free because your AI does the thinking”.
- **[P2]** How it works — <https://provaendurance.com/en/how-it-works/>. Quatro papéis, passo a passo,
  regras, thresholds, três domínios, RHR/HRV, “no readiness score”, “no fitness or fatigue score”,
  seis referências.
- **[P3]** FAQ — <https://provaendurance.com/en/faq/>. Gratuidade, apps testados, esportes, histórico,
  dispositivo, “what if the AI gets it wrong”, revogação, exclusão.
- **[P4]** Tour — <https://provaendurance.com/en/tour/>. Plano com fontes, sessão com `.fit`, atividade
  analisada, Coach tab, thresholds com data/origem, quatro buckets de domínio.
- **[P5]** Setup — <https://provaendurance.com/en/setup/>. MCP endpoint, instruções por cliente,
  Streamable HTTP/OAuth 2.1/DCR, integração.
- **[P6]** Privacy — <https://provaendurance.com/en/privacy/>. Dados, base legal, localização,
  exclusão, backups, cookies, controlador.
- **[P7]** Terms — <https://provaendurance.com/en/terms/>. Definição do serviço, preço, “not medical
  advice”, dados, lei brasileira.
- **[P8]** Metadados observados em 2026-10-23 UTC: `POST https://api.provaendurance.com/mcp` (401 +
  `WWW-Authenticate`), `GET https://api.provaendurance.com/.well-known/oauth-protected-resource`,
  `GET https://api.provaendurance.com/.well-known/oauth-authorization-server`. Headers: `Kestrel`,
  HSTS; OAuth: authorization code, refresh, PKCE S256, DCR, public client, scopes.
- **[P9]** Tópico oficial “Free Adaptive Training Plans: Prova Endurance”, fórum Intervals.icu,
  criado em 2026-09-28 — <https://forum.intervals.icu/t/free-adaptive-training-plans-prova-endurance/132638>.
  Posts 1, 3, 5, 10 e 11: autoria, corpus de 110 papers, judge, exceção da semana automática, bug de
  refresh token/RFC 8693, tração (10→20 atletas), Strava. O post 1 inclui uma descrição que o próprio
  autor rotula como **gerada por LLM**; os detalhes de “judge”, “training load, fitness and zones” e
  a formulação “110 notes” vêm dessa descrição, não de uma especificação técnica.
- **[P10]** Domain Arrivals, “Prova Endurance: an AI coach that shows its work”, 2026-09-22 —
  <https://domainarrivals.com/issues/2026-09-22/domains/provaendurance-com/>. Terceiro, editorial;
  não é avaliação de qualidade.

### Referências científicas citadas pelo Prova (metadados e abstracts via Europe PMC)

- **[R1]** Passfield L, Murias JM, Sacchetti M, Nicolò A. *Validity of the Training-Load Concept.*
  Int J Sports Physiol Perform. 2022;17(4):507–514. DOI `10.1123/ijspp.2021-0536`; PMID 35247874.
- **[R2]** Seiler KS, Kjerland GØ. *Quantifying training intensity distribution in elite endurance
  athletes: is there evidence for an “optimal” distribution?* Scand J Med Sci Sports.
  2006;16(1):49–56. DOI `10.1111/j.1600-0838.2004.00418.x`; PMID 16430681.
- **[R3]** Seiler S. *What is best practice for training intensity and duration distribution in
  endurance athletes?* Int J Sports Physiol Perform. 2010;5(3):276–291. DOI `10.1123/ijspp.5.3.276`;
  PMID 20861519.
- **[R4]** Nes BM, Janszky I, Wisløff U, Støylen A, Karlsen T. *Age-predicted maximal heart rate in
  healthy subjects: the HUNT Fitness Study.* Scand J Med Sci Sports. 2013;23(6):697–704.
  DOI `10.1111/j.1600-0838.2012.01445.x`; PMID 22376273.
- **[R5]** Buchheit M. *Monitoring training status with HR measures: do all roads lead to Rome?*
  Front Physiol. 2014;5:73. DOI `10.3389/fphys.2014.00073`; PMID 24578692.
- **[R6]** Saw AE, Main LC, Gastin PB. *Monitoring the athlete training response: subjective
  self-reported measures trump commonly used objective measures: a systematic review.* Br J Sports
  Med. 2016;50(5):281–291. DOI `10.1136/bjsports-2015-094758`; PMID 26423706.

### Hermes Coach (checkout local)

- **[H1]** `README.md` — motor determinístico, comandos, readiness, automação diária, guardrails,
  limitações.
- **[H2]** `AGENTS.md` — fonte de verdade, separação evidência/heurística/modelo, guardrails de
  domínio.
- **[H3]** `docs/EMBASAMENTO-CIENTIFICO.md` — §15 (matriz de rastreabilidade por feature) e §16
  (referências), incluindo a coluna “O que o estudo NÃO mostra”.
- **[H4]** `docs/ROADMAP.md` — #13 (MCP/apps ChatGPT/Claude), #29 (Coach+), #8/#24 (multi-atleta/SaaS),
  #18/#30 (multi-esporte).
- **[H5]** `src/coach.py` — `ZONE_BANDS`, foco, pisos de zona.
- **[H6]** `src/readiness.py`, `src/readiness_assessment.py` — prontidão, sinais, classificação.
- **[H7]** `tests/` — 1.548 testes no commit `ff3c956` (suíte completa, 2026-10-22).
