# Conversa com o treinador de ciclismo

> [!info] Dono deste documento
> Fonte canônica: `docs/ROTEIRO-TREINADOR.md` **no repo**. O arquivo no vault é
> cópia de leitura; quando divergirem, o repo vence. Edite aqui e sincronize com
> `python3 scripts/sync_vault_docs.py --check`, depois
> `python3 scripts/sync_vault_docs.py --sync docs/ROTEIRO-TREINADOR.md`.
> Espelho: `~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/ROTEIRO-TREINADOR.md`.

## Antes de começar

O objetivo desta conversa é entender **como você toma decisões com seus
atletas**. Não estamos procurando respostas "certas", números perfeitos ou uma
prova de ciência. Queremos saber o que você realmente observa no dia a dia para
que o Hermes não invente regras que um treinador de verdade não usaria.

Se você não usa algum dado, dizer **"não uso"** é uma resposta importante.
Também vale responder "depende do atleta", "eu precisaria olhar melhor" ou
"isso eu decidiria caso a caso".

### Como conduzir

- **Essencial**: percorrer na primeira conversa.
- **Se houver tempo**: aprofunda o raciocínio.
- **Follow-up**: pode virar mensagem depois ou uma segunda conversa.

Sempre comece por **"como você trabalha hoje?"**. Só depois pergunte se usa
números, e só no fim pergunte o que gostaria que o Hermes fizesse com isso.

> **Para quem registra a entrevista:** anote as palavras do treinador antes de
> traduzi-las para o sistema. No fim do arquivo há notas técnicas discretas para
> transformar as respostas em decisões de produto.

---

## 1. Conversa essencial

### 1.1 Como você monta as zonas de treino

<!-- zonas / referência de potência e FC -->

**Pergunta:** Quando você define as zonas de um atleta, normalmente usa o FTP
(uma referência de potência do atleta) ou prefere outro valor?

_Por que perguntamos:_ isso mostra como transformar os dados do atleta em zonas
de treino sem impor uma tabela pronta.

**Se houver tempo:** Você vê o Sweet Spot como uma zona própria ou como uma faixa
entre outras zonas? Há alguma zona que você costuma ajustar primeiro?

**Pergunta:** Se o atleta não tiver um FTP confiável, como você orienta o treino?
Você usa frequência cardíaca, sensação de esforço, um teste de campo ou outra
referência?

_Por que perguntamos:_ o Hermes precisa continuar útil mesmo quando falta um
sensor ou um teste recente.

**Pergunta:** Quando monta zonas de frequência cardíaca, você prefere usar a
frequência máxima ou o limiar do atleta?

_Por que perguntamos:_ potência e frequência cardíaca podem contar histórias
diferentes; queremos saber como você usa cada uma.

**Pergunta:** Se o atleta estiver sem medidor de potência ou cinta de frequência
cardíaca, você usaria a sensação de esforço para orientar o treino?

_Por que perguntamos:_ a sensação de esforço, ou RPE (*percepção de esforço*),
pode ser uma alternativa prática, mas não precisa substituir todos os dados.

### 1.2 Como você percebe recuperação e fadiga

<!-- recuperação / decisão diária -->

**Pergunta:** Como você costuma perceber que um atleta está cansado ou não está
absorvendo bem o treino?

_Por que perguntamos:_ queremos começar pela sua prática, antes de falar de
números ou alertas.

**Pergunta:** Quais sinais você olha primeiro? Há algum que você nunca usaria?

**Pergunta:** Quando um dado está ruim, você só quer ser avisado ou às vezes
mudaria o treino daquele dia?

_Por que perguntamos:_ isso ajuda a separar contexto, alerta e mudança de treino
sem automatizar nada por conta própria.

**Pergunta:** Você normalmente tolera um sinal ruim isolado ou prefere esperar
que ele se repita por alguns dias?

**Follow-up:** Isso muda conforme a fase do atleta, por exemplo base,
construção, semana de prova ou volta de férias?

### 1.3 HRV e frequência cardíaca de repouso

<!-- HR-3 / HRV / RHR -->

**Pergunta:** Você usa HRV (*variabilidade da frequência cardíaca*) para avaliar
recuperação? O que costuma observar nela?

_Por que perguntamos:_ ajuda o Hermes a saber se deve mostrar só o número do dia
ou comparar com os dias anteriores do próprio atleta.

**Pergunta:** Você olha mais o valor do dia ou a tendência de vários dias?

**Pergunta:** Você usa a frequência cardíaca de repouso para perceber cansaço ou
início de doença?

_Por que perguntamos:_ uma mudança isolada pode ser ruído; queremos entender
quando ela passa a merecer atenção na sua prática.

**Pergunta:** Você olha um aumento isolado ou vários dias seguidos? Como trata um
valor que parece erro de sensor?

**Follow-up:** Quando esses sinais fazem você pensar em doença ou necessidade de
reduzir a carga? O que diferencia isso de um dia simplesmente cansado?

**Follow-up:** Em que horário, posição e dispositivo esses dados precisam ser
coletados para você confiar na comparação?

> **Glossário curto:** RHR/FCR significa frequência cardíaca de repouso. Não é a
> queda da frequência cardíaca depois do esforço.

### 1.4 Sono, stress e como o atleta se sente

<!-- HR-4 / sleep duration -->

**Pergunta:** Para você, importa mais quanto tempo o atleta dormiu ou a
qualidade do sono também pesa?

_Por que perguntamos:_ isso ajuda a saber quais dados de sono realmente valem a
pena mostrar e acompanhar.

**Pergunta:** Você usa duração total do sono, tempo na cama, eficiência do sono
ou outra medida? Uma noite ruim já muda sua decisão ou você prefere olhar vários
dias?

**Se houver tempo:** Você pensa em dívida de sono acumulada? Usa algum limite
específico ou compara principalmente com o padrão daquele atleta?

<!-- HR-4 / sleep score -->

**Pergunta:** Relógios às vezes dão uma nota de sono. Você acha esse tipo de nota
útil ou prefere olhar os dados por trás dela?

_Por que perguntamos:_ uma nota de um dispositivo pode ser apenas referência; só
faz sentido usar mais do que isso se você confiar no que ela representa.

**Pergunta:** Você compararia notas de dispositivos diferentes? Precisaria saber
como o fabricante calcula a nota para confiar nela?

<!-- HR-4 / stress -->

**Pergunta:** Quando você fala em stress do atleta, o que considera na prática?

_Por que perguntamos:_ "stress" pode significar trabalho, vida pessoal, sensação
de cansaço, medida do relógio ou outra coisa. Não vamos assumir uma definição.

**Follow-up:** Você costuma comparar esse stress com os dias anteriores? Quando
ele sobe, isso costuma significar o quê para você?

<!-- HR-4 / soreness -->

**Pergunta:** Você costuma perguntar sobre dor muscular ou pernas pesadas antes
de decidir o treino do dia? *(soreness)*

_Por que perguntamos:_ queremos distinguir a dor muscular normal depois do treino
de algo que merece mais cuidado, como dor de lesão.

**Pergunta:** Você olha o corpo todo ou regiões específicas? Pergunta antes ou
depois do treino? Usa alguma escala simples?

<!-- HR-4 / motivation -->

**Pergunta:** A vontade de treinar naquele dia entra na sua avaliação?

_Por que perguntamos:_ uma queda isolada pode não dizer muito; queremos saber se
você usa isso como contexto ou só quando se repete.

**Pergunta:** Você diferencia motivação geral de vontade de fazer o treino de
hoje? O que faria esse sinal importar para você?

<!-- HR-4 / fatigue -->

**Pergunta:** Quando o atleta diz que está cansado, você tenta separar cansaço
físico, muscular e mental, ou uma percepção geral já basta?

_Por que perguntamos:_ evita perguntar duas vezes a mesma coisa com nomes
diferentes, como sono, stress, dor muscular e fadiga.

**Pergunta:** Esse cansaço é algo independente para você ou já aparece por outros
sinais que você acompanha?

<!-- HR-4 / provider readiness -->

**Pergunta:** Relógios e plataformas costumam dar uma nota de prontidão ou
recuperação. Você confia nessas notas?

_Por que perguntamos:_ elas podem servir como contexto, mas não vamos tratá-las
como uma resposta pronta sobre o atleta.

**Pergunta:** Você usaria essa nota só como referência ou deixaria influenciar
sua decisão? Se ela discordar da sua leitura, o que gostaria de ver?

### 1.5 Quando os sinais se contradizem

<!-- conflitos / revisão humana -->

**Pergunta:** O atleta dormiu mal, mas acordou motivado e diz que está se
sentindo bem. O que pesa mais para você?

**Pergunta:** A frequência de repouso está normal, mas ele relata cansaço forte.
Você mantém o treino ou prefere ajustar?

**Pergunta:** A dor muscular está alta, mas a nota do relógio diz que a
recuperação está boa. Como você resolve isso?

**Pergunta:** O relógio mostra uma boa nota de sono, mas o atleta dormiu pouco.
O que você considera primeiro?

**Follow-up:** A leitura de carga parece pesada, mas o atleta responde bem. Ou o
contrário: a frequência sobe em treino constante num dia muito quente. Em cada
caso, você prefere parar e revisar ou seguir o sinal mais conservador?

_Por que perguntamos:_ queremos saber quando mostrar um conflito e pedir revisão
humana, em vez de fingir que existe uma regra automática certa.

### 1.6 Quando mudar um treino

<!-- automação / prescrição -->

**Pergunta:** Se um sinal estiver ruim, você gostaria que o Hermes apenas avisasse
ou também sugerisse mudar o treino?

**Pergunta:** Você deixaria o sistema mudar sozinho ou sempre prefere confirmar?

**Pergunta:** O que o Hermes nunca deveria fazer sem você aprovar?

_Por que perguntamos:_ o objetivo é respeitar seu jeito de trabalhar, não tirar
do treinador a decisão que exige contexto humano.

### 1.7 Teste de FTP — segurança e agendamento

<!-- FTP-H5 / FTP test safety + placement -->
<!-- As respostas desta seção fecham o contrato de segurança e agendamento do
     teste de FTP (FTP-H5). Nenhuma resposta liga alerta nem muda plano
     automaticamente. -->

_Por que perguntamos:_ quando o atleta não conhece o próprio FTP, o Hermes deve
prescrever um teste de FTP. Teste é esforço alto; precisamos do seu critério
para decidir quando prescrever, como preparar e quando impedir ou adiar — sem
inventar regras por conta própria.

**Pergunta:** Em quais condições um teste de FTP deve ser impedido ou adiado?
Considere, separadamente: prontidão RED, prontidão YELLOW, alerta de possível
doença (illness), fadiga recente e recuperação incompleta.

_Estado de referência:_ o Hermes tem prontidão GREEN/YELLOW/RED e um alerta de
possível doença destacado quando RHR sobe e HRV cai juntos. Não vamos redefinir
esses estados aqui; queremos apenas o seu critério de uso para o dia do teste.

**Follow-up:** Para cada condição, a ação no dia do teste deve ser bloquear
(hard block), adiar, apenas avisar (warning/advice) ou permitir com
confirmação/override do atleta? Não tratamos YELLOW como bloqueio automático sem
você definir.

**Pergunta:** O atleta pode fazer o teste mesmo com um aviso ativo? Se sim, em
quais estados? Se não, quais estados devem ser bloqueio rígido?

**Pergunta (preparação):** Como contrato padrão em volta do teste, o Hermes hoje
monta: D-2 recuperação de 40 min @ 55% FTP; D-1 spin fácil de 30 min @ 50% FTP;
D0 marcador do teste (executado na plataforma externa); D+1 recuperação de 30 min
@ 55% FTP; sem dia extra depois do D+1. Esse arranjo é adequado como contrato
padrão? Se houver ajuste (duração, intensidade, dia extra), qual?

**Pergunta (crítica):** Como as sessões leves D-2/D-1 devem ser prescritas quando
o FTP ainda é UNKNOWN? O propósito do fluxo é descobrir o FTP; "55%/50% do FTP"
não pode depender do valor que o teste vai revelar (circularidade). Opções
conceituais que você pode escolher ou substituir: RPE, frequência cardíaca,
esforço fácil prescrito livre, outro método definido por você.

**Pergunta (V1 — teste externo):** Você aprova que a primeira versão use teste
externo escolhido pelo atleta (ex.: Zwift ou outra plataforma), com: data
escolhida pelo usuário; preparação validada pelo Hermes; resultado informado
manualmente; confirmação explícita antes de virar referência de FTP?
(SIM / NÃO / COM CONDIÇÕES)

**Pergunta:** Se o atleta não utiliza plataforma externa, qual deve ser o
comportamento nesta primeira versão? Considerar: aguardar protocolo Hermes;
teste de campo; outro protocolo; orientação manual.

**Pergunta (V2 — teste do Hermes):** Para a segunda versão (teste próprio do
Hermes), qual protocolo deve ser suportado primeiro: FTP 20 min, Ramp Test ou
outro definido por você?

**Pergunta:** Nesse teste próprio, quais regras devem valer para warm-up, pacing,
termination, cálculo do resultado, recuperação e contraindicações?

**Pergunta:** Existe janela mínima antes/depois de prova na qual um teste de FTP
não deve ser prescrito? Se sim, qual? (Não precisamos de um número agora se você
mesmo não usa um.)

**Pergunta:** A preparação D-2 fácil / D-1 spin é suficiente como proteção contra
treino intenso anterior ao teste? Se não, qual janela/regra usar?

### 1.8 Progressão semanal — decisões de política (gate PROG-1/2)

<!-- PROG-1 / PROG-2 — gates Q1-Q4 da progressão semanal. Sem resposta → PROG-2
     permanece BLOCKED. Não respondidas nesta task. Relacionadas, mas NÃO
     duplicadas, com §2.1 (WEEK_MISSED / BLOCK_PROGRESSION / DELOAD_USE):
     ali o foco é o método geral; aqui é o gate operacional da progressão. -->

_Por que perguntamos:_ o Hermes ainda não decide, semana a semana, se o estímulo
deve progredir, manter, recuperar ou regressar — ele organiza o plano por orçamento
de carga e prontidão diária. Antes de qualquer guardrail de progressão, precisamos
do seu gate: o que bloqueia avanço, o que distingue manter de regressar, como
escolher a dimensão a progredir e como reconhecer a hora de recuperar. Nenhuma
resposta liga alerta nem muda plano automaticamente.

**Pergunta (Q1 — adesão):** Qual nível de cumprimento do plano bloqueia a
progressão semanal? E em qual janela esse nível conta (uma semana? duas semanas?)?

**Pergunta (Q2 — incompletos):** Quantas sessões relevantes incompletas ou parciais
na janela justificam manter o nível atual em vez de progredir? E a partir de quantas
você reduz explicitamente o nível (em vez de só manter)?

**Pergunta (Q3 — dimensão):** Ao longo das semanas, o que você costuma fazer crescer
primeiro: volume total, tempo no intervalo, repetições ou intensidade? Você
prioriza uma dimensão por vez?

**Pergunta (Q4 — recuperação):** Quando você antecipa ou detecta que o atleta precisa
de uma semana de recuperação? Você olha execução, prontidão (sono/RHR/HRV), fase da
periodização, densidade de treinos fortes ou uma combinação?

---

## 2. Se houver tempo: aprofundar a prática de treino

### 2.1 Como você estrutura a semana e o plano

<!-- periodização / TSB / orçamento -->

**Pergunta:** Como você decide quando uma semana deve ser mais leve, de base ou
mais intensa?

**Pergunta:** Você olha a relação entre fitness, fadiga e forma ao tomar essa
decisão? Se sim, como usa isso na prática?

_Por que perguntamos:_ o Hermes hoje usa esses números para organizar a semana;
queremos conferir se o raciocínio parece com o seu, não defender uma regra fixa.

**Pergunta:** Como você percebe que a carga semanal ficou alta demais? Você olha
horas, esforço total, sensação do atleta ou uma combinação?

**Pergunta:** Quando um atleta perde um treino ou faz um treino pesado fora do
planejado, o que você costuma mudar depois?

**Pergunta:** Semanas de descanso fazem parte do seu método? Como você decide a
hora de incluí-las?

**Pergunta:** Como você aumenta volume e intensidade ao longo de um bloco? O que
mudaria para iniciante, intermediário e avançado?

**Follow-up:** Para a mesma prova, o perfil do atleta — por exemplo rouleur,
escalador ou contra-relogista — muda a distribuição dos treinos? Como você faria
essa classificação?

**Follow-up:** Para duas ou três provas na temporada, você montaria um plano em
sequência com preparação específica para cada uma? O que o Hermes precisaria
saber sobre a prova além da data e do tipo?

**Pergunta:** Você prefere que o sistema crie treinos a partir de princípios ou
parta de uma biblioteca de treinos já validados? Em que situação cada caminho
faz sentido?

**Follow-up:** Se o atleta pudesse escolher uma prova numa lista com distância,
perfil e exigência, isso ajudaria mais do que pedir apenas data e tipo de prova?

**Follow-up:** Um relatório semanal ou mensal com carga, evolução e tempo em
zonas seria útil para você ou para o atleta? O que você leria e o que cortaria?

### 2.2 Volta após pausa, férias ou lesão

<!-- recovery / ramp rate -->

**Pergunta:** Depois de férias, doença, lesão ou uma pausa longa, como você faz o
atleta voltar a treinar?

**Pergunta:** Você costuma olhar se a carga aumentou rápido demais de uma semana
para outra? Se sim, o que faz esse aumento parecer preocupante?

_Por que perguntamos:_ o Hermes consegue mostrar a velocidade de aumento de
carga; precisamos saber se isso ajuda sua decisão e em quais situações.

**Pergunta:** Você compara esse aumento com o nível atual do atleta? Que fatores
fariam você ignorar uma semana aparentemente alta, como viagem, calor ou teste?

**Follow-up:** Na volta, uma semana de recuperação programada a cada algumas
semanas faz sentido? Como você equilibraria isso com a vontade do atleta de
recuperar a forma rápido?

### 2.3 Frequência cardíaca subindo em treino constante

<!-- HR-2 / Pw:HR -->

**Pergunta:** Em treinos longos e constantes, você costuma observar se a
frequência cardíaca vai subindo mesmo quando a potência continua parecida?

_Por que perguntamos:_ esse comportamento é o que o Hermes chama de
desacoplamento entre potência e frequência cardíaca. Primeiro queremos saber se
ele faz parte da sua leitura de treino.

**Pergunta:** Em quais treinos isso vale para você? Você olharia o treino inteiro
ou só uma parte estável dele?

**Pergunta:** Como trataria aquecimento, volta à calma, pausas, calor, treino
indoor e mudanças de ritmo?

**Pergunta:** Você prefere escolher o trecho manualmente ou deixaria o Hermes
procurar um trecho estável? O que caracterizaria um bom trecho?

**Follow-up:** Você usa algum limite para esse comportamento? Esse número vem da
sua experiência, de formação/literatura ou de uma mistura dos dois?

### 2.4 Detalhes das zonas, se precisar fechar a tabela

<!-- zonas / follow-up científico -->

**Pergunta:** Para cada zona, faz sentido registrar a sensação de esforço, a
duração típica e o objetivo do treino? O que seria útil e o que seria ruído?

**Pergunta:** As zonas mudam com modalidade, indoor/outdoor, idade, histórico ou
nível do atleta? Quais diferenças realmente importam na sua prática?

**Pergunta:** Quando você atualiza as zonas: novo teste, mudança percebida, alteração manual ou rotina fixa? Quem tem a palavra final: você, atleta ou a plataforma?

---

## 3. Produto: como isso entraria no seu trabalho

### 3.1 Trabalho com vários atletas

**Pergunta:** Quantos atletas você atende hoje? Eles treinam mais indoor ou na
rua? Que perfil de atleta você atende mais?

**Pergunta:** Se o Hermes acompanhasse seus atletas, qual seria a primeira coisa
que você abriria todo dia: calendário, lista de alertas, resumo ou outra tela?

**Pergunta:** Que tipo de alerta seria realmente útil? O que só atrapalharia?

**Pergunta:** Você quer aprovar cada treino antes de publicar ou confiaria em um
fluxo automático com opção de desfazer?

**Pergunta:** Quais dados você precisa ajustar por atleta: dias disponíveis,
tempo, FTP, objetivo, intensidade da semana ou outros?

**Pergunta:** Como você acompanha e conversa com os atletas hoje? O que uma
ferramenta teria de fazer para merecer substituir parte desse processo?

**Se houver tempo:** Que tipo de relatório o atleta realmente leria? Como você
saberia, depois de um mês, que a ferramenta está ajudando?

### 3.2 Preço e piloto

**Pergunta:** O que precisaria existir para você testar o Hermes com um atleta
real? Há algo que você não aceitaria de jeito nenhum?

**Pergunta:** Você cobraria por atleta, por mês ou de outra forma? Que valor faria
sentido se a ferramenta economizasse tempo e ajudasse a acompanhar o plano?

**Pergunta:** Quer ver uma demonstração com os dados de um atleta? Se sim, o que
precisamos preservar como controle seu antes de qualquer publicação?

### 3.3 Uso por atleta sem treinador

**Pergunta:** Para um atleta que treina sem acompanhamento, o que o Hermes nunca
deveria fazer sozinho?

**Pergunta:** Que proteção você colocaria para esse atleta: pedir novo teste,
avisar sobre muitas semanas pesadas, limitar mudanças ou outra trava?

**Pergunta:** Se ele viajar, não tiver agenda ou ficar alguns dias sem treinar,
como você gostaria que o sistema reagisse?

**Pergunta:** Qual seria o primeiro tipo de plano seguro para um iniciante que
treina sozinho?

---

## 4. Encerramento

**Pergunta:** Qual seria a maior vantagem e o maior risco de recomendar o Hermes
para outro treinador?

**Pergunta:** O que faltaria para você usar hoje? Quais três melhorias você
pediria primeiro?

**Pergunta:** Se você explicasse essa ferramenta a um colega, como descreveria o
valor dela?

---

## 5. Notas para implementação após a entrevista

Esta seção não é para conduzir a conversa. Ela preserva rastreabilidade para
transformar resposta do treinador em decisão de produto, evidência ou heurística
operacional, sem apresentar linguagem de software ao treinador.

### 5.1 Como registrar cada resposta

```text
Pergunta:
Resposta do treinador:
Classificação: evidência científica | experiência do treinador |
               heurística operacional | decisão de produto
Vem mais de experiência, literatura/formação ou mistura?
Precisa pesquisa bibliográfica: SIM | NÃO | INCERTO
Fonte/referência:
Decisão provisória:
Próximo passo:
```

Pergunte primeiro como ele decide; só depois se usa algum número. Todo número
novo fica como prática individual até haver fonte verificável. Não tratar opinião
do treinador como verdade fisiológica universal.

### 5.2 Mapa técnico discreto

| assunto da conversa | rastreabilidade |
|---|---|
| zonas de potência | `ZONE_BANDS`; tabela científica Z1–Z7 ainda é pendência |
| sensação de esforço | RPE; não assumir equivalência exata com potência ou frequência cardíaca |
| forma e carga | PMC: fitness, fadiga e forma; números servem de contexto, não de diagnóstico |
| volta gradual | crescimento de carga semanal; hoje existe leitura observacional, sem limite universal novo |
| frequência cardíaca em esforço constante | Pw:HR / desacoplamento; contexto metodológico precisa ser confirmado |
| recuperação diária | HRV/RHR, sono e demais sinais; cada sinal pode ser exibição, contexto, alerta ou decisão futura |
| sono, stress, dor, vontade e fadiga | HR-4; decidir primeiro se o treinador usa, depois pesquisar a fonte de dados |
| teste de FTP (segurança e agendamento) | FTP-H5; safety/placement aguarda respostas do treinador (perguntas no §1.7); suporta a decisão de produto e o fluxo FTP UNKNOWN |
| progressão semanal (gate PROG-1/2) | contrato em `docs/SPEC-progression.md`; perguntas Q1-Q4 no §1.8; PROG-2 bloqueado até as respostas |

### 5.3 Estado atual que não deve ser apresentado como decisão do treinador

- O Hermes já usa dados de carga para organizar a semana, respeita orçamento de
  carga, reage a treino perdido e registra treino extra. Isso é o ponto de
  partida a ser validado, não uma prescrição científica final.
- O plano pode ser adaptado por objetivo, data de prova, disponibilidade e
  retorno após pausa. Nível do atleta, perfil de esforço, múltiplas provas e
  catálogo de eventos continuam perguntas de produto, não fatos decididos.
- HRV significa variabilidade da frequência cardíaca; RHR/FCR significa
  frequência cardíaca de repouso. *Heart-rate recovery* é outro conceito e não
  faz parte desta conversa de HR-3.
- Para HR-4, `soreness`, `motivation` e `fatigue` não têm fonte confirmada.
  `stress`, nota de sono e nota de prontidão são dados observados, mas sua escala
  e direção ainda precisam de decisão do treinador e pesquisa posterior.
- Nenhuma resposta liga alerta, muda treino, cria limite ou automatiza decisão
  nesta entrevista.

### 5.4 Perguntas prováveis e resposta curta para a demo

| pergunta | resposta curta |
|---|---|
| Como o Hermes acompanha carga e forma? | Usa o histórico de treino como contexto para organizar o plano; o treinador valida se essa leitura faz sentido. |
| E se o atleta perder um treino ou fizer carga extra? | O sistema registra isso e pode propor uma adaptação; a regra exata continua sujeita à sua validação. |
| Como lida com descanso, doença ou lesão? | Há sinais e leitura de contexto, mas nenhuma decisão de saúde deve ser inventada ou automatizada sem critério validado. |
| Usa potência ou frequência cardíaca? | Normalmente potência; quando ela falta, a conversa define se frequência cardíaca e percepção de esforço ajudam. |
| O sistema substitui o treinador? | Não. A intenção é tirar trabalho repetitivo e deixar decisões com contexto humano visíveis e auditáveis. |
| Pode publicar sozinho? | Só no limite de autonomia que o treinador aceitar; aprovação e possibilidade de desfazer são perguntas centrais. |

### 5.5 Material de referência, não roteiro de fala

- **Resumo inicial, se for útil apresentar.** O Hermes consulta o histórico no
  Intervals.icu, organiza treinos indoor, acompanha carga semanal, registra
  treino perdido ou extra e pode publicar no calendário. Apresentar isso como
  ponto de partida para crítica, não como lógica já aprovada pelo treinador.
- **Lógica atual a validar, não defender.** A semana hoje usa faixas de TSB para
  variar foco; limita a carga semanal; em falta de treino propõe recuperação e
  ajuste da próxima sessão intensa; e tem rampa de retorno após pausa. Perguntas
  das seções 2.1 e 2.2 cobrem cada uma dessas escolhas sem despejar os números
  internos na conversa.
- **Benchmark de produto.** Xert, Pillar, TriDot e RunDot tendem a organizar o
  plano por objetivo e evento, não apenas por catálogo fixo. O benchmark de
  preços e o objetivo de pilotos com treinadores conhecidos continuam no pitch;
  validar primeiro se objetivo, evento, múltiplas provas e revisão humana são
  úteis para este treinador antes de ampliar o produto.
- **Piloto.** Estratégia atual: convidar treinadores conhecidos como beta testers,
  usar esta conversa e, se houver interesse, demonstrar com dados autorizados de
  um atleta. Nenhum treino deve ser publicado sem o controle aceito pelo treinador.
- **Cenários a avaliar depois:** retorno pós-pausa, nível do atleta, perfil de
  esforço, múltiplos objetivos, catálogo de eventos, relatórios, indoor/outdoor,
  preço, modo solo e controles de aprovação.
- **Tabela científica Z1–Z7.** Exige entrevista, definição dos campos úteis,
  levantamento bibliográfico verificável, classificação de fontes e reconciliação
  com a prática. Nunca preencher uma tabela vazia para parecer concluída, nem
  deduzir números a partir da implementação atual.

---

## 6. Sugestão de execução

**Primeiro encontro — 30 a 40 min:** seções 1.1 a 1.8. Prioridade: zonas, como
percebe recuperação/fadiga, HRV/RHR, sono, quando mudaria um treino e os gates de
progressão semanal (Q1-Q4, §1.8).

**Segundo encontro — 30 a 45 min:** seção 2 e produto da seção 3. Use follow-up
por mensagem para números, referências e detalhes que exigem consulta.

**Depois da conversa:** registrar respostas no vault de decisões; transformar
apenas respostas explícitas em backlog. Se o treinador disser que não usa um
sinal, isso é uma decisão válida e evita criar complexidade desnecessária.
