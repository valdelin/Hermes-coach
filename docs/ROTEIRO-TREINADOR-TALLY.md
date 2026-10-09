# Como você trabalha com seus atletas?

> **Arquivo derivado.** Este arquivo é derivado de `docs/ROTEIRO-TREINADOR.md`.
> A fonte canônica das perguntas e decisões da entrevista é o roteiro principal.
> Este arquivo existe apenas para facilitar a montagem/importação no Tally.

<!-- TALLY PAGE: 01
SOURCE: ROTEIRO-TREINADOR §Antes de começar
priority: boas-vindas
sem campos
-->

## 1. Boas-vindas

Queremos entender como você toma decisões no dia a dia para que o Hermes
reflita a prática de um treinador de verdade.

Não existem respostas certas ou erradas.

Se você não usa algum dado ou métrica, dizer **"não uso"** é uma resposta
importante. Também vale responder "depende do atleta", "eu precisaria olhar
melhor" ou "isso eu decidiria caso a caso".

O objetivo não é testar conhecimento técnico — queremos entender o seu
processo.

A maior parte das perguntas é rápida. Perguntas mais detalhadas só aparecem
quando fizerem sentido para a sua forma de trabalhar: se um assunto não se
aplicar, ele some sozinho.

<!-- TALLY LOGIC
ORDEM: como você trabalha -> o que você observa -> usa algum número?
       -> o que faria se estivesse alterado -> o que o Hermes deveria fazer
NOTA: nenhum campo abaixo é pré-marcado.
-->

---

## 2. Sobre você e seu trabalho

<!-- TALLY PAGE: 02
SOURCE: ROTEIRO-TREINADOR §3.1 + identificação mínima
priority: essencial (identificação) / se houver tempo (perfil)
-->

Antes de qualquer coisa, uma apresentação rápida. Nada além do necessário.

Qual seu nome?

<!-- TALLY ID: COACH_NAME
type: short_text
required: true
-->

Há quanto tempo você trabalha como treinador?

<!-- TALLY ID: COACH_TIME
type: multiple_choice
required: true
options: Menos de 2 anos | 2–5 anos | 6–10 anos | Mais de 10 anos
-->

Quantos atletas você atende hoje?

<!-- TALLY ID: COACH_ATHLETES
type: multiple_choice
required: false
options: Menos de 5 | 5 a 10 | 11 a 20 | Mais de 20 | Até agora só acompanhei meus próprios treinos
-->

Eles treinam mais indoor ou na rua?

<!-- TALLY ID: COACH_MODALITY
type: multiple_choice
required: false
options: Mais indoor | Mais na rua | Os dois por igual | Depende do atleta
-->

Que perfil de atleta você atende mais?

<!-- TALLY ID: COACH_PROFILE
type: long_text
required: false
-->

---

## 3. Zonas de treino usadas atualmente pelo Hermes

<!-- TALLY PAGE: 03
SOURCE: ADENDO REVISADO (PROMPT 35) + src/coach.py:ZONE_BANDS
tags canônicas: zonas / referência de potência e FC
priority: essencial — avaliar a implementação real antes da prática do treinador
-->

Hoje o Hermes usa as zonas abaixo para orientar treinos baseados em potência.

Os percentuais são relativos ao FTP do atleta.

Queremos saber se essas faixas fazem sentido para você, se mudaria algum limite
e se organizaria alguma dessas intensidades de outra forma.

Essas zonas mostram apenas como o Hermes funciona hoje.
Não estamos apresentando esses valores como uma definição científica definitiva.

<!-- SOURCE:
src/coach.py:ZONE_BANDS

Usar exatamente os limites atualmente implementados.
Não alterar percentuais nesta tarefa.
Não criar Z7.
Não transformar Sweet Spot em outra zona.
Este formulário serve para o treinador avaliar a implementação existente.
-->

<!-- NOTA TÉCNICA
Valores conferidos contra src/coach.py:ZONE_BANDS e contra o literal de
tests/test_plan.py::test_zona_bands_espelham_a_tabela_do_documento.
Z7 está fora de ZONE_BANDS (é potência máxima, não faixa de %FTP) e Sweet Spot
sobrepõe Z3/Z4 de propósito.
Guardrail: não chamar esta tabela de "Tabela Científica Z1–Z7" e não deduzir
uma estrutura Z1–Z7 a partir dela.
-->

| Zona | Faixa usada pelo Hermes |
|---|---:|
| **Z1** | **até 55% do FTP** |
| **Z2** | **56–75% do FTP** |
| **Z3** | **76–90% do FTP** |
| **Sweet Spot** | **84–97% do FTP** |
| **Z4** | **91–105% do FTP** |
| **Z5** | **106–120% do FTP** |
| **Z6** | **121–150% do FTP** |

Observação: o Hermes atualmente usa Z1 a Z6 e uma faixa específica de Sweet
Spot.

Sweet Spot se sobrepõe parcialmente à Z3 e à Z4.

Hoje não existe uma Z7 separada no Hermes. Uma das coisas que queremos avaliar
com você é justamente se essa estrutura deveria continuar assim.

Olhando para os percentuais acima, essas faixas se parecem com as zonas que
você costuma usar?

<!-- TALLY ID: ZONES_CURRENT_MODEL
type: multiple_choice
required: false
options: Sim, são bem parecidas | Em parte | Não | Eu uso outro modelo de zonas
-->

Pense principalmente nos limites em %FTP e no objetivo que você normalmente
associa a cada faixa.

Quais faixas você revisaria?

<!-- TALLY ID: ZONES_PER_ZONE_REVIEW
type: checkboxes
required: false
show_if: ZONES_CURRENT_MODEL ≠ "Sim, são bem parecidas"
options: Z1 — até 55% FTP | Z2 — 56–75% FTP | Z3 — 76–90% FTP | Sweet Spot — 84–97% FTP | Z4 — 91–105% FTP | Z5 — 106–120% FTP | Z6 — 121–150% FTP | A estrutura inteira
-->

Hoje o Hermes considera Z1 como até 55% do FTP. Como você trataria essa zona?

<!-- TALLY ID: ZONE1_REVIEW
type: long_text
required: false
show_if: ZONES_PER_ZONE_REVIEW contém "Z1 — até 55% FTP"
-->

Você pode sugerir outro percentual, explicar o objetivo dessa zona ou dizer se
usa uma divisão diferente.

Hoje o Hermes usa Z2 entre 56% e 75% do FTP. Você manteria essa faixa?

<!-- TALLY ID: ZONE2_REVIEW
type: long_text
required: false
show_if: ZONES_PER_ZONE_REVIEW contém "Z2 — 56–75% FTP"
-->

Hoje o Hermes usa Z3 entre 76% e 90% do FTP. Como você definiria essa
intensidade?

<!-- TALLY ID: ZONE3_REVIEW
type: long_text
required: false
show_if: ZONES_PER_ZONE_REVIEW contém "Z3 — 76–90% FTP"
-->

Hoje o Hermes considera Sweet Spot entre 84% e 97% do FTP. Essa faixa faz
sentido para você?

<!-- TALLY ID: SWEET_SPOT_REVIEW
type: multiple_choice
required: false
show_if: ZONES_PER_ZONE_REVIEW contém "Sweet Spot — 84–97% FTP"
other: short_text
options: Sim | Mudaria os limites | Não trataria Sweet Spot como faixa própria | Não costumo usar Sweet Spot | Outro
-->

Quais limites você usaria?

<!-- TALLY ID: SWEET_SPOT_LIMITS
type: short_text
required: false
show_if: SWEET_SPOT_REVIEW = "Mudaria os limites"
-->

Hoje o Hermes usa Z4 entre 91% e 105% do FTP. Você manteria essa faixa?

<!-- TALLY ID: ZONE4_REVIEW
type: long_text
required: false
show_if: ZONES_PER_ZONE_REVIEW contém "Z4 — 91–105% FTP"
-->

Hoje o Hermes usa Z5 entre 106% e 120% do FTP. Como você trataria essa faixa?

<!-- TALLY ID: ZONE5_REVIEW
type: long_text
required: false
show_if: ZONES_PER_ZONE_REVIEW contém "Z5 — 106–120% FTP"
-->

Hoje o Hermes usa Z6 entre 121% e 150% do FTP. Essa faixa representa bem os
esforços que você colocaria nessa zona?

<!-- TALLY ID: ZONE6_REVIEW
type: long_text
required: false
show_if: ZONES_PER_ZONE_REVIEW contém "Z6 — 121–150% FTP"
-->

Hoje o Hermes termina a estrutura de zonas na Z6, que vai de 121% a 150% do
FTP. Você sente falta de uma Z7 ou de outra faixa específica acima disso?

<!-- TALLY ID: ZONE7_NEED
type: multiple_choice
required: false
options: Sim | Não | Depende do tipo de treino | Eu organizo esses esforços de outra forma
-->

Como você organizaria os esforços acima da Z6?

<!-- TALLY ID: ZONE7_HOW
type: long_text
required: false
show_if: ZONE7_NEED ≠ "Não"
-->

Pode sugerir uma Z7, outro limite em %FTP ou simplesmente explicar como você
trabalha esses esforços mais intensos.

Além dos números, você mudaria o objetivo de alguma dessas zonas?

<!-- TALLY ID: ZONE_PURPOSES
type: yes_no
required: false
NOTA: os nomes de objetivo do ajuda não equivalem automaticamente a Z1–Z6.
-->

O que você mudaria?

<!-- TALLY ID: ZONE_PURPOSES_HOW
type: long_text
required: false
show_if: ZONE_PURPOSES = Sim
-->

Por exemplo: recuperação, endurance, tempo, limiar, VO₂, anaeróbio ou outra
forma que você prefere para organizar os treinos.

Além do percentual do FTP, o que você costuma observar para confirmar se o
atleta está realmente na intensidade certa?

<!-- TALLY ID: ZONE_SIGNALS
type: checkboxes
required: false
other: short_text
options: Frequência cardíaca | Sensação de esforço | Respiração / capacidade de falar | Cadência | Comportamento da potência durante o intervalo | Experiência e feedback do atleta | Uso principalmente a potência | Outro
-->

---

<!-- TALLY PAGE: 04
SOURCE: ROTEIRO-TREINADOR §1.1 (essencial) + §2.4 (se houver tempo)
tags canônicas: zonas / referência de potência e FC; zonas / follow-up científico
priority: essencial
-->

## 4. Como você define as zonas

Quando você define as zonas de um atleta, qual referência costuma usar
primeiro?

<!-- TALLY ID: ZONE_REF
type: multiple_choice
required: true
other: short_text
options: FTP | Potência crítica / CP | Frequência cardíaca | Sensação de esforço | Combino mais de uma | Depende do atleta | Outro
-->

Se o atleta não tiver um FTP confiável, como você orienta o treino? Você usa
frequência cardíaca, sensação de esforço, um teste de campo ou outra
referência?

<!-- TALLY ID: ZONE_NOFTP
type: checkboxes
required: false
show_if: ZONE_REF ≠ "FTP"
other: short_text
options: Frequência cardíaca | Sensação de esforço | Teste de campo | Outro
-->

Quando monta zonas de frequência cardíaca, você prefere usar a frequência
máxima ou o limiar do atleta?

<!-- TALLY ID: ZONE_FC_METHOD
type: multiple_choice
required: false
show_if: ZONE_REF em {"Frequência cardíaca", "Combino mais de uma", "Depende do atleta"}
         OU ZONE_NOFTP contém "Frequência cardíaca"
options: Frequência máxima | Limiar do atleta | Os dois | Depende do atleta | Não monto zonas de frequência cardíaca
-->

Quando potência ou frequência cardíaca não estão disponíveis, você usa a
sensação de esforço para orientar o atleta?

<!-- TALLY ID: ZONE_RPE
type: multiple_choice
required: false
options: Sim, frequentemente | Às vezes | Raramente | Não
-->

Você considera Sweet Spot uma faixa própria na hora de montar os treinos?

<!-- TALLY ID: ZONE_SWEETSAPOT
type: multiple_choice
required: false
options: Sim | Não | Depende | Não uso Sweet Spot dessa forma
-->

Em quais situações o Sweet Spot se aplica?

<!-- TALLY ID: ZONE_SWEETSAPOT_WHY
type: long_text
required: false
show_if: ZONE_SWEETSAPOT = "Depende"
-->

Há alguma zona que você costuma ajustar primeiro?

<!-- TALLY ID: ZONE_FIRST_ADJUST
type: long_text
required: false
-->

Para cada zona, faz sentido registrar a sensação de esforço, a duração típica
e o objetivo do treino? O que seria útil e o que seria ruído?

<!-- TALLY ID: ZONE_PER_ZONE
type: checkboxes
required: false
other: short_text
options: Sensação de esforço | Duração típica | Objetivo do treino | Nada disso | Outro
-->

As zonas mudam com modalidade, indoor/outdoor, idade, histórico ou nível do
atleta? Quais diferenças realmente importam na sua prática?

<!-- TALLY ID: ZONE_CONTEXT
type: checkboxes
required: false
other: short_text
options: Modalidade | Indoor versus outdoor | Idade | Histórico | Nível do atleta | Não mudam | Outro
-->

Quando você atualiza as zonas?

<!-- TALLY ID: ZONE_UPDATE_WHEN
type: checkboxes
required: false
other: short_text
options: Novo teste | Mudança percebida | Alteração manual | Rotina fixa | Outro
-->

Quem tem a palavra final quando as zonas mudam?

<!-- TALLY ID: ZONE_FINAL_SAY
type: multiple_choice
required: false
options: Eu | O atleta | A plataforma | Depende do que mudou
-->

---

## 5. Como você percebe recuperação e fadiga

<!-- TALLY PAGE: 05
SOURCE: ROTEIRO-TREINADOR §1.2
tags canônicas: recuperação / decisão diária
-->

Como você costuma perceber que um atleta está cansado ou não está absorvendo
bem o treino? Uma ou duas frases bastam.

<!-- TALLY ID: RECOVERY_OPEN
type: long_text
required: true
-->

Quando você quer saber se o atleta está recuperado para o treino do dia, o que
costuma observar?

<!-- TALLY ID: RECOVERY_SIGNALS
type: checkboxes
required: true
preselect: nenhum
note: controla o resto do formulário — só aparecem os detalhes dos sinais marcados
options: Como ele diz que está se sentindo | Frequência cardíaca de repouso | HRV / variabilidade da frequência cardíaca | Sono | Carga recente de treino | Dor muscular / pernas pesadas | Stress | Motivação | Desempenho nos treinos recentes | Outro
-->

Há algum desses sinais que você nunca usaria?

<!-- TALLY ID: RECOVERY_NEVER
type: checkboxes
required: false
other: short_text
options: Como ele diz que está se sentindo | Frequência cardíaca de repouso | HRV / variabilidade da frequência cardíaca | Sono | Carga recente de treino | Dor muscular / pernas pesadas | Stress | Motivação | Desempenho nos treinos recentes | Nenhum, uso todos | Outro
-->

Você normalmente tolera um sinal ruim isolado ou prefere esperar que ele se
repita por alguns dias?

<!-- TALLY ID: RECOVERY_TOLERANCE
type: multiple_choice
required: false
options: Um dia isolado raramente me preocupa | Geralmente espero alguns dias | Depende do sinal | Depende da fase do atleta
-->

Isso muda conforme a fase do atleta?

<!-- TALLY ID: RECOVERY_PHASE
type: checkboxes
required: false
other: short_text
options: Base | Construção | Semana de prova | Volta de férias | Não muda conforme a fase | Outro
-->

---

## 6. HRV e frequência cardíaca de repouso

<!-- TALLY PAGE: 06
SOURCE: ROTEIRO-TREINADOR §1.3
tags canônicas: HR-3 / HRV / RHR
priority: essencial
-->

### HRV

Você usa HRV (variabilidade da frequência cardíaca) para avaliar recuperação?

<!-- TALLY ID: HRV_USE
type: multiple_choice
required: true
show_if: RECOVERY_SIGNALS contém "HRV / variabilidade da frequência cardíaca"
options: Sim | Às vezes | Não
-->

O que pesa mais para você?

<!-- TALLY ID: HRV_TREND
type: multiple_choice
required: false
show_if: HRV_USE em {Sim, Às vezes}
other: short_text
options: Valor de hoje | Tendência de vários dias | Comparação com o padrão daquele atleta | Uma combinação desses fatores | Outro
-->

Uma mudança em um único dia costuma ser suficiente para preocupar você?

<!-- TALLY ID: HRV_SINGLE_DAY
type: multiple_choice
required: false
show_if: HRV_USE em {Sim, Às vezes}
options: Sim | Às vezes | Não | Depende do sinal
-->

### Frequência cardíaca de repouso

Você usa a frequência cardíaca de repouso (FCR/RHR) para perceber cansaço ou
possível início de doença?

<!-- TALLY ID: RHR_USE
type: multiple_choice
required: true
show_if: RECOVERY_SIGNALS contém "Frequência cardíaca de repouso"
options: Sim | Às vezes | Não
-->

Você olha um aumento isolado ou vários dias seguidos?

<!-- TALLY ID: RHR_PATTERN
type: multiple_choice
required: false
show_if: RHR_USE em {Sim, Às vezes}
options: Um aumento isolado | Vários dias seguidos | Os dois | Depende
-->

Como você trata um valor que parece erro de sensor?

<!-- TALLY ID: RHR_SENSOR
type: long_text
required: false
show_if: RHR_USE em {Sim, Às vezes}
-->

Quando esses sinais fazem você pensar em doença ou necessidade de reduzir a
carga? O que diferencia isso de um dia simplesmente cansado?

<!-- TALLY ID: RHR_ILLNESS
type: long_text
required: false
show_if: RHR_USE em {Sim, Às vezes}
-->

Em que horário, posição e dispositivo esses dados precisam ser coletados para
você confiar na comparação?

<!-- TALLY ID: RHR_PROTOCOL
type: long_text
required: false
show_if: RHR_USE em {Sim, Às vezes}
-->

> **Glossário:** RHR/FCR significa frequência cardíaca de repouso. Não é a
> queda da frequência cardíaca depois do esforço.

---

## 7. Sono

<!-- TALLY PAGE: 07
SOURCE: ROTEIRO-TREINADOR §1.4
tags canônicas: HR-4 / sleep duration; HR-4 / sleep score
priority: essencial
-->

Quais medidas de sono você usa ou considera mais úteis?

<!-- TALLY ID: SLEEP_USE
type: checkboxes
required: false
show_if: RECOVERY_SIGNALS contém "Sono"
preselect: nenhum
other: short_text
options: Quantidade de horas dormidas | Tempo na cama | Eficiência do sono | Qualidade percebida do sono | Nota fornecida pelo relógio/app | Tendência de vários dias | Não costumo usar dados de sono | Outro
-->

Uma noite ruim já muda sua decisão ou você prefere olhar vários dias?

<!-- TALLY ID: SLEEP_ONE_NIGHT
type: multiple_choice
required: false
show_if: SLEEP_USE não contém "Não costumo usar dados de sono"
options: Uma noite ruim já muda | Prefiro olhar vários dias | Depende do atleta
-->

Você pensa em dívida de sono acumulada? Usa algum limite específico ou compara
principalmente com o padrão daquele atleta?

<!-- TALLY ID: SLEEP_DEBT
type: long_text
required: false
show_if: SLEEP_USE não contém "Não costumo usar dados de sono"
-->

Quando existe uma nota de sono, você prefere olhar:

<!-- TALLY ID: SLEEP_SCORE_PREFERENCE
type: multiple_choice
required: false
show_if: SLEEP_USE contém "Nota fornecida pelo relógio/app"
options: A nota pronta | Os dados por trás dela | Os dois | Depende do dispositivo
-->

Quanto você confia nessas notas prontas dos relógios e aplicativos?

<!-- TALLY ID: SLEEP_SCORE_TRUST
type: multiple_choice
required: false
show_if: SLEEP_USE contém "Nota fornecida pelo relógio/app"
options: Bastante | Uso apenas como referência | Pouco | Não confio | Depende do dispositivo
-->

Você compararia notas de dispositivos diferentes? Precisaria saber como o
fabricante calcula a nota para confiar nela?

<!-- TALLY ID: SLEEP_SCORE_COMPARE
type: multiple_choice
required: false
show_if: SLEEP_SCORE_TRUST está respondida
options: Compararia sem ressalvas | Só se soubesse como ela é calculada | Não compararia
-->

---

## 8. Stress, dor muscular, motivação e fadiga

<!-- TALLY PAGE: 08
SOURCE: ROTEIRO-TREINADOR §1.4 (escala de stress: §5.3, pendência que cita
        decisão do treinador; irmã da escala de dor já existente)
tags canônicas: HR-4 / stress; HR-4 / soreness; HR-4 / motivation;
                HR-4 / fatigue; HR-4 / provider readiness
priority: essencial
nota interna: "notas de prontidão" aqui são a nota do provedor (campo
  readiness do /wellness, HR-4/RDY-1); a visão de prontidão do Hermes é
  outro cálculo derivado do PMC (source: RDY-1, src/ui_state.py). Não dizer
  ao treinador que uma é a outra. RDY-1 é read-only e não toca em ação.
-->

### Stress

Quando você considera "stress" na avaliação do atleta, em que tipo de stress
pensa?

<!-- TALLY ID: STRESS_USE
type: checkboxes
required: false
show_if: RECOVERY_SIGNALS contém "Stress"
preselect: nenhum
other: short_text
options: Trabalho/vida pessoal | Stress percebido pelo próprio atleta | Nota do relógio ou aplicativo | Cansaço geral | Não costumo usar stress | Outro
-->

Você costuma comparar esse stress com os dias anteriores? Quando ele sobe,
isso costuma significar o quê para você?

<!-- TALLY ID: STRESS_TREND
type: long_text
required: false
show_if: STRESS_USE está respondida e não contém "Não costumo usar stress"
-->

Você costuma usar alguma escala ou nota para medir o stress do atleta?

<!-- TALLY ID: STRESS_SCALE
type: yes_no
required: false
show_if: STRESS_TREND está respondida
-->

Qual?

<!-- TALLY ID: STRESS_SCALE_NAME
type: short_text
required: false
show_if: STRESS_SCALE = Sim
-->

### Dor muscular ou pernas pesadas

A dor muscular ou as pernas pesadas costuma influenciar sua decisão sobre o
treino do dia?

<!-- TALLY ID: SORENESS_USE
type: multiple_choice
required: false
show_if: RECOVERY_SIGNALS contém "Dor muscular / pernas pesadas"
options: Frequentemente | Às vezes | Raramente | Não
-->

Você faz diferença entre dor muscular normal pós-treino e uma dor que pode
indicar lesão?

<!-- TALLY ID: SORENESS_DOMS
type: multiple_choice
required: false
show_if: SORENESS_USE em {Frequentemente, Às vezes}
options: Sim | Às vezes | Não | Depende
-->

Como você faz essa distinção na prática?

<!-- TALLY ID: SORENESS_DOMS_HOW
type: long_text
required: false
show_if: SORENESS_DOMS em {Sim, Às vezes, Depende}
-->

Você olha o corpo todo ou regiões específicas?

<!-- TALLY ID: SORENESS_REGION
type: checkboxes
required: false
show_if: SORENESS_USE em {Frequentemente, Às vezes}
other: short_text
options: Corpo todo | Regiões específicas | Não separo | Outro
-->

Você pergunta sobre dor antes ou depois do treino?

<!-- TALLY ID: SORENESS_WHEN
type: multiple_choice
required: false
show_if: SORENESS_USE em {Frequentemente, Às vezes}
options: Antes do treino | Depois do treino | Os dois | Não faço essa separação
-->

Você costuma usar alguma escala ou nota para avaliar a dor?

<!-- TALLY ID: SORENESS_SCALE
type: yes_no
required: false
show_if: SORENESS_USE em {Frequentemente, Às vezes}
-->

Qual?

<!-- TALLY ID: SORENESS_SCALE_NAME
type: short_text
required: false
show_if: SORENESS_SCALE = Sim
-->

### Motivação

A vontade de treinar naquele dia entra na sua avaliação?

<!-- TALLY ID: MOTIVATION_USE
type: multiple_choice
required: false
show_if: RECOVERY_SIGNALS contém "Motivação"
options: Sim | Às vezes | Não
-->

Uma queda de motivação em um único dia importa ou você prefere observar
vários dias?

<!-- TALLY ID: MOTIVATION_SINGLE
type: multiple_choice
required: false
show_if: MOTIVATION_USE em {Sim, Às vezes}
options: Um dia já importa | Prefiro observar vários dias | Depende do atleta
-->

Você diferencia motivação geral de vontade de fazer o treino de hoje? O que
faria esse sinal importar para você?

<!-- TALLY ID: MOTIVATION_KIND
type: long_text
required: false
show_if: MOTIVATION_USE em {Sim, Às vezes}
-->

### Fadiga

Quando o atleta diz que está cansado, você costuma diferenciar tipos de
cansaço?

<!-- TALLY ID: FATIGUE_USE
type: checkboxes
required: false
show_if: RECOVERY_SIGNALS contém "Como ele diz que está se sentindo"
preselect: nenhum
other: short_text
options: Cansaço muscular | Cansaço físico geral | Cansaço mental | Sonolência/falta de sono | Não costumo separar | Outro
-->

Esse cansaço é algo independente para você ou já aparece por outros sinais
que você acompanha?

<!-- TALLY ID: FATIGUE_INDEP
type: long_text
required: false
show_if: FATIGUE_USE está respondida e não contém "Não costumo separar"
-->

### Notas de prontidão dos aparelhos

Relógios e plataformas costumam dar uma nota de prontidão ou recuperação.
Você confia nessas notas?

<!-- TALLY ID: READINESS_USE
type: multiple_choice
required: false
show_if: sempre
options: Bastante | Só como referência | Pouco | Não confio | Depende do dispositivo
-->

Na prática, como essa nota entra na sua decisão?

<!-- TALLY ID: READINESS_ROLE
type: multiple_choice
required: false
show_if: READINESS_USE está respondida
options: Só como informação extra | Pode reforçar o que eu já estava pensando | Pode me fazer rever o treino | Pode levar a uma mudança em algumas situações | Não usaria para decidir | Depende
-->

Se essa nota discordar da sua leitura, o que você gostaria de ver?

<!-- TALLY ID: READINESS_DISCORD
type: long_text
required: false
show_if: READINESS_ROLE está respondida
-->

---

## 9. Carga e resposta ao treino

<!-- TALLY PAGE: 09
SOURCE: ROTEIRO-TREINADOR §2.1 e §2.2
tags canônicas: periodização / TSB / orçamento; recovery / ramp rate
priority: se houver tempo
-->

Como você decide quando uma semana deve ser mais leve, de base ou mais
intensa?

<!-- TALLY ID: WEEK_STRUCTURE
type: long_text
required: false
-->

Você olha a relação entre fitness, fadiga e forma ao tomar essa decisão?

<!-- TALLY ID: FORM_USE
type: multiple_choice
required: false
options: Sim | Às vezes | Não | Não uso esses números
-->

Se sim, como você usa essa relação na prática?

<!-- TALLY ID: FORM_HOW
type: long_text
required: false
show_if: FORM_USE em {Sim, Às vezes}
-->

Como você percebe que a carga semanal ficou alta demais?

<!-- TALLY ID: WEEK_LOAD_HIGH
type: checkboxes
required: false
other: short_text
options: Horas de treino | Esforço total | Sensação do atleta | Uma combinação | Não olho de forma separada | Outro
-->

Quando um atleta perde um treino ou faz um treino pesado fora do planejado,
o que você costuma mudar depois?

<!-- TALLY ID: WEEK_MISSED
type: long_text
required: false
-->

Semanas de descanso fazem parte do seu método?

<!-- TALLY ID: DELOAD_USE
type: multiple_choice
required: false
options: Sim, faço de forma periódica | Sim, quando percebo que é preciso | Não | Depende do atleta
-->

Como você decide a hora de incluir essas semanas de descanso?

<!-- TALLY ID: DELOAD_HOW
type: long_text
required: false
show_if: DELOAD_USE começa com "Sim"
-->

Como você aumenta volume e intensidade ao longo de um bloco? O que mudaria
para iniciante, intermediário e avançado?

<!-- TALLY ID: BLOCK_PROGRESSION
type: long_text
required: false
-->

Para a mesma prova, o perfil do atleta — por exemplo rouleur, escalador ou
contra-relogista — muda a distribuição dos treinos? Como você faria essa
classificação?

<!-- TALLY ID: ATHLETE_PROFILE_IMPACT
type: long_text
required: false
-->

Depois de férias, doença, lesão ou uma pausa longa, como você faz o atleta
voltar a treinar?

<!-- TALLY ID: RETURN_PAUSE
type: long_text
required: false
-->

Você costuma observar se a carga de treino aumentou rápido demais de uma
semana para outra?

<!-- TALLY ID: RAMP_USE
type: multiple_choice
required: false
options: Sim | Às vezes | Não
-->

O que faz você considerar um aumento rápido de carga preocupante?

<!-- TALLY ID: RAMP_CONCERN
type: long_text
required: false
show_if: RAMP_USE em {Sim, Às vezes}
-->

O que você considera um aumento rápido de carga muda conforme o nível ou o
histórico do atleta?

<!-- TALLY ID: RAMP_INDIVIDUAL
type: multiple_choice
required: false
show_if: RAMP_USE em {Sim, Às vezes}
options: Sim | Não | Depende
-->

O que muda na sua avaliação?

<!-- TALLY ID: RAMP_INDIVIDUAL_HOW
type: long_text
required: false
show_if: RAMP_INDIVIDUAL em {Sim, Depende}
-->

Que fatores fariam você ignorar uma semana aparentemente alta?

<!-- TALLY ID: RAMP_IGNORE
type: checkboxes
required: false
show_if: RAMP_USE em {Sim, Às vezes}
other: short_text
options: Viagem | Clima quente | Teste de referência | Nível atual do atleta | Não ignoraria | Outro
-->

Na volta, uma semana de recuperação programada a cada algumas semanas faz
sentido? Como você equilibraria isso com a vontade do atleta de recuperar a
forma rápido?

<!-- TALLY ID: RETURN_RECOVERY_WEEK
type: long_text
required: false
-->

---

## 10. Frequência cardíaca subindo em treino constante

<!-- TALLY PAGE: 10
SOURCE: ROTEIRO-TREINADOR §2.3
tags canônicas: HR-2 / Pw:HR
priority: se houver tempo
-->

Em treinos longos e constantes, você observa se a frequência cardíaca vai
subindo mesmo quando a potência continua parecida?

<!-- TALLY ID: PWHR_OBSERVE
type: multiple_choice
required: true
options: Sim | Às vezes | Não | Não presto atenção nisso
-->

<!-- TALLY NOTE
texto a exibir quando a resposta for Sim ou Às vezes:
"O Hermes consegue medir esse comportamento. Queremos entender quando ele
realmente é útil para você."
-->

Em quais treinos isso vale para você? Você olharia o treino inteiro ou só uma
parte estável dele?

<!-- TALLY ID: PWHR_SCOPE
type: long_text
required: false
show_if: PWHR_OBSERVE em {Sim, Às vezes}
-->

Como você trataria aquecimento, volta à calma, pausas, calor, treino indoor e
mudanças de ritmo?

<!-- TALLY ID: PWHR_CAVEATS
type: checkboxes
required: false
show_if: PWHR_OBSERVE em {Sim, Às vezes}
other: short_text
options: Aquecimento | Volta à calma | Pausas | Calor | Treino indoor | Mudanças de ritmo | Outro
-->

Você prefere escolher o trecho manualmente ou deixaria o Hermes procurar um
trecho estável?

<!-- TALLY ID: PWHR_PICK
type: multiple_choice
required: false
show_if: PWHR_OBSERVE em {Sim, Às vezes}
options: Eu escolho o trecho | O Hermes pode procurar | Depende
-->

O que caracterizaria um bom trecho?

<!-- TALLY ID: PWHR_GOOD_SEGMENT
type: long_text
required: false
show_if: PWHR_OBSERVE em {Sim, Às vezes}
-->

Você usa algum limite para esse comportamento?

<!-- TALLY ID: PWHR_LIMIT
type: yes_no
required: false
show_if: PWHR_OBSERVE em {Sim, Às vezes}
-->

Qual limite você costuma usar?

<!-- TALLY ID: PWHR_LIMIT_VALUE
type: short_text
required: false
show_if: PWHR_LIMIT = Sim
-->

De onde vem esse valor?

<!-- TALLY ID: PWHR_LIMIT_SOURCE
type: multiple_choice
required: false
show_if: PWHR_LIMIT = Sim
options: Experiência prática | Formação/cursos | Literatura científica | Ferramenta/plataforma | Combinação | Não lembro | Outro
other: short_text
-->

---

## 11. Quando os sinais se contradizem

<!-- TALLY PAGE: 11
SOURCE: ROTEIRO-TREINADOR §1.5
tags canônicas: conflitos / revisão humana
priority: essencial
-->

O atleta dormiu mal, mas acordou motivado e diz que está se sentindo bem. O
que você faria?

<!-- TALLY ID: CONFLICT_1
type: multiple_choice
required: false
other: short_text
options: Manteria o treino | Manteria, mas observaria | Reduziria | Mudaria o tipo de treino | Depende | Outro
-->

Do que dependeria?

<!-- TALLY ID: CONFLICT_1_DEP
type: long_text
required: false
show_if: CONFLICT_1 = "Depende"
-->

A frequência de repouso ou os dados do relógio parecem normais, mas o atleta
relata cansaço forte. O que pesa mais para você?

<!-- TALLY ID: CONFLICT_2
type: multiple_choice
required: false
other: short_text
options: O relato do atleta | Os dados | Uma combinação | Depende da situação | Outro
-->

A dor muscular está alta, mas a nota do relógio diz que a recuperação está
boa. Como você resolveria isso?

<!-- TALLY ID: CONFLICT_3
type: multiple_choice
required: false
other: short_text
options: Daria mais peso à dor | Daria mais peso à nota | Consideraria os dois | Mudaria o treino | Depende | Outro
-->

O relógio mostra uma boa nota de sono, mas o atleta dormiu pouco. O que você
considera primeiro?

<!-- TALLY ID: CONFLICT_4
type: multiple_choice
required: false
other: short_text
options: A nota do relógio | O relato do atleta | Os dois | Depende da situação | Outro
-->

Às vezes a leitura de carga parece pesada, mas o atleta responde bem; outras
vezes a frequência sobe em treino constante num dia muito quente. Em cada
caso, você prefere parar e revisar ou seguir o sinal mais conservador?

<!-- TALLY ID: CONFLICT_RECHECK
type: long_text
required: false
-->

---

## 12. Autonomia: o que o Hermes pode fazer

<!-- TALLY PAGE: 12
SOURCE: ROTEIRO-TREINADOR §1.2 + §1.6 + §1.7 (FTP-H5: safety/placement) + PROMPT 35 §35–37
tags canônicas: automação / prescrição / teste de FTP
priority: essencial — sempre por último (FTP-H5 quando FTP é UNKNOWN)
-->

Quando o Hermes percebe um sinal preocupante, o que você gostaria que ele
fizesse primeiro?

<!-- TALLY ID: AUTOMATION_LEVEL
type: multiple_choice
required: true
options: Não fazer nada | Apenas mostrar o dado | Mostrar um aviso | Sugerir uma mudança
-->

Hoje o Hermes já publica a sessão do dia no calendário automaticamente, sem
pedir aprovação antes. Com isso em mente, você deixaria o Hermes mudar um
treino automaticamente por causa desses sinais?

<!-- SOURCE: estado implementado, não decisão atual — scripts/daily_reconcile.sh
     publica o dia com push --start sem etapa de aprovação. Se esse comportamento
     mudar, atualizar esta linha (ver checklist pós-importação). -->

<!-- TALLY ID: AUTOMATION_CHANGE
type: multiple_choice
required: true
options: Não, sempre quero confirmar | Sim, mas apenas em situações bem definidas | Sim | Ainda não sei
-->

Quais mudanças fariam sentido?

<!-- TALLY ID: CHANGE_TYPES
type: checkboxes
required: false
show_if: AUTOMATION_LEVEL = "Sugerir uma mudança"
         OU AUTOMATION_CHANGE em {"Sim, mas apenas em situações bem definidas", "Sim"}
other: short_text
options: Reduzir intensidade | Reduzir duração | Trocar por recuperação | Adiar o treino | Cancelar o treino | Sugerir descanso | Outro
-->

O que o Hermes nunca deveria fazer sem você aprovar?

<!-- TALLY ID: AUTOMATION_NEVER
type: long_text
required: false
-->

#### 12.1 Teste de FTP — segurança e agendamento

Quando o atleta não conhece o próprio FTP, o Hermes deve prescrever um teste de
FTP. Antes disso, precisamos do seu critério (SEÇÃO A) e da sua aprovação do
fluxo da versão 1 (SEÇÃO B). Não há resposta pré-marcada; nada disso liga alerta
nem muda plano automaticamente.

#### SEÇÃO A — Critério de segurança

Em quais condições um teste de FTP deve ser impedido ou adiado? Considere,
separadamente: prontidão RED, prontidão YELLOW, alerta de possível doença
(illness), fadiga recente e recuperação incompleta. Para cada condição, indique
a ação no dia do teste: bloquear (hard block) | adiar | apenas avisar (warning) |
permitir com confirmação do atleta.

<!-- TALLY ID: FTPTEST_BLOCK
type: long_text
required: true
-->

O atleta pode fazer o teste mesmo com um aviso ativo? Se sim, em quais estados?
Se não, quais estados devem ser bloqueio rígido?

<!-- TALLY ID: FTPTEST_OVERRIDE
type: long_text
required: true
-->

Existe janela mínima antes/depois de prova na qual um teste de FTP não deve ser
prescrito? Se sim, qual? (Não precisamos de um número agora se você mesmo não usa
um.)

<!-- TALLY ID: FTPTEST_RACE_WINDOW
type: long_text
required: false
-->

A preparação D-2 fácil / D-1 spin é suficiente como proteção contra treino
intenso anterior ao teste? Se não, qual janela/regra usar?

<!-- TALLY ID: FTPTEST_HARD_WINDOW
type: long_text
required: false
-->

#### SEÇÃO B — Preparação e fluxo da versão 1

Como contrato padrão de preparação, o arranjo atual é: D-2 recuperação de 40 min
@ 55% FTP; D-1 spin fácil de 30 min @ 50% FTP; D0 marcador do teste (executado na
plataforma externa); D+1 recuperação de 30 min @ 55% FTP; sem dia extra depois do
D+1. Esse arranjo é adequado como contrato padrão?

<!-- TALLY ID: FTPTEST_PREP
type: multiple_choice
required: true
options: Sim | Não | Com ajustes
other: short_text
-->

Quando o FTP ainda é UNKNOWN, como as sessões leves D-2/D-1 devem ser
prescritas? O propósito do fluxo é descobrir o FTP; "55%/50% do FTP" não pode
depender do valor que o teste vai revelar. Opções conceituais que você pode
escolher ou substituir: RPE | frequência cardíaca | esforço fácil prescrito
livre | outro método definido por você.

<!-- TALLY ID: FTPTEST_PREP_UNKNOWN
type: long_text
required: true
-->

Você aprova que a versão 1 use teste externo escolhido pelo atleta (ex.: Zwift
ou outra plataforma), com: data escolhida pelo usuário; preparação validada pelo
Hermes; resultado informado manualmente; confirmação explícita antes de virar
referência de FTP?

<!-- TALLY ID: FTPTEST_EXTERNAL_V1
type: multiple_choice
required: true
options: Sim | Não | Com condições
other: short_text
-->

Se o atleta não utiliza plataforma externa, qual deve ser o comportamento nesta
primeira versão?

<!-- TALLY ID: FTPTEST_NO_PLATFORM
type: multiple_choice
required: false
other: short_text
options: Aguardar protocolo Hermes | Teste de campo | Outro protocolo | Orientação manual do treinador
-->

#### SEÇÃO C — Segunda versão, teste próprio do Hermes

Para a segunda versão, qual protocolo o Hermes deve suportar primeiro?

<!-- TALLY ID: FTPTEST_HERMES_PROTOCOL
type: multiple_choice
required: false
other: short_text
options: FTP 20 min | Ramp Test | Outro definido pelo treinador
-->

Nesse teste próprio, quais regras devem valer para warm-up, pacing, termination,
cálculo do resultado, recuperação e contraindicações?

<!-- TALLY ID: FTPTEST_HERMES_RULES
type: long_text
required: false
-->

#### 12.2 Progressão semanal — decisões de política (gate PROG-1/2)

O Hermes ainda não decide, semana a semana, se o estímulo deve progredir, manter,
recuperar ou regressar — o plano é organizado por orçamento de carga e prontidão
diária. Antes de qualquer guardrail de progressão, precisamos do seu gate (SEÇÃO D).
**Enquanto estas respostas não existirem, PROG-2 permanece bloqueado.** Não há
resposta pré-marcada; nada disso liga alerta nem muda plano automaticamente. Relacionado
(no formulário) com `WEEK_MISSED`, `BLOCK_PROGRESSION` e `DELOAD_USE`, que tratam do
método geral; aqui o foco é o gate operacional da progressão.

#### SEÇÃO D — Gates da progressão semanal

Qual nível de cumprimento do plano bloqueia a progressão semanal? E em qual janela
esse nível conta (uma semana? duas semanas?)?

<!-- TALLY ID: PROG_Q1
type: long_text
required: false
-->

Quantas sessões relevantes incompletas ou parciais na janela justificam manter o
nível atual em vez de progredir? E a partir de quantas você reduz explicitamente o
nível (em vez de só manter)?

<!-- TALLY ID: PROG_Q2
type: long_text
required: false
-->

Ao longo das semanas, o que você costuma fazer crescer primeiro: volume total,
tempo no intervalo, repetições ou intensidade? Você prioriza uma dimensão por vez?

<!-- TALLY ID: PROG_Q3
type: long_text
required: false
-->

Quando você antecipa ou detecta que o atleta precisa de uma semana de recuperação?
O que você olha para isso?

<!-- TALLY ID: PROG_Q4
type: checkboxes
required: false
other: short_text
options: Execução | Prontidão (sono/RHR/HRV) | Fase da periodização | Densidade de treinos fortes | Uma combinação
-->

---

## 13. Produto: como isso entraria no seu trabalho

<!-- TALLY PAGE: 13
SOURCE: ROTEIRO-TREINADOR §3.1–3.3 + §2.1 (perguntas de produto)
priority: se houver tempo
-->

Se o Hermes acompanhasse seus atletas, qual seria a primeira coisa que você
abriria todo dia?

<!-- TALLY ID: PROD_FIRST_SCREEN
type: checkboxes
required: false
other: short_text
options: Calendário | Lista de alertas | Resumo do dia | Outro
-->

Que tipo de alerta seria realmente útil? O que só atrapalharia?

<!-- TALLY ID: PROD_ALERTS
type: long_text
required: false
-->

Você quer aprovar cada treino antes de publicar ou confiaria em um fluxo
automático com opção de desfazer?

<!-- TALLY ID: PROD_APPROVAL
type: multiple_choice
required: false
options: Quero aprovar cada treino | Aprovo em lote | Confiaria em automático com desfazer | Depende
-->

Se um treino precisar entrar no calendário e você ainda não tiver avaliado, o
que prefere que aconteça?

<!-- SOURCE: PORTAL-UI-DESIGN P1 (decisão de produto ainda aberta) + ROTEIRO §1.6
     (aprovação/controle do treinador) -->
<!-- TALLY ID: PROD_APPROVAL_PENDING
type: multiple_choice
required: false
show_if: PROD_APPROVAL está respondida
options: Publicar mesmo assim e me avisar | Não publicar até eu avaliar | Expirar e voltar a aparecer depois | Depende do tipo de mudança | Outro
other: short_text
-->

Quais dados você precisa ajustar por atleta?

<!-- TALLY ID: PROD_ADJUST
type: checkboxes
required: false
other: short_text
options: Dias disponíveis | Tempo | FTP | Objetivo | Intensidade da semana | Outro
-->

Como você acompanha e conversa com os atletas hoje? O que uma ferramenta
teria de fazer para merecer substituir parte desse processo?

<!-- TALLY ID: PROD_TODAY
type: long_text
required: false
-->

O que seria útil em um resumo semanal ou mensal?

<!-- TALLY ID: PROD_REPORT_CONTENT
type: checkboxes
required: false
other: short_text
options: Carga de treino | Evolução ao longo do tempo | Tempo em cada zona | Treinos concluídos | Treinos perdidos | Sinais de recuperação | Alertas importantes | Planejado versus realizado | Outro | Não usaria esse tipo de relatório
-->

Esse resumo seria útil mais para você ou para o atleta? O que você realmente
leria e o que seria só ruído? E como você saberia, depois de um mês, que a
ferramenta está ajudando?

<!-- TALLY ID: PROD_REPORT
type: long_text
required: false
show_if: PROD_REPORT_CONTENT está respondida
-->

Você prefere que o sistema crie treinos a partir de princípios ou parta de uma
biblioteca de treinos já validados? Em que situação cada caminho faz sentido?

<!-- TALLY ID: PLAN_SOURCE
type: multiple_choice
required: false
other: short_text
options: Criar a partir de princípios | Biblioteca de treinos já validados | Os dois | Depende da situação | Outro
-->

Para duas ou três provas na temporada, você montaria um plano em sequência
com preparação específica para cada uma? O que o Hermes precisaria saber
sobre a prova além da data e do tipo?

<!-- TALLY ID: MULTI_RACE
type: long_text
required: false
-->

Se o atleta pudesse escolher uma prova numa lista com distância, perfil e
exigência, isso ajudaria mais do que pedir apenas data e tipo de prova?

<!-- TALLY ID: PROD_RACE_CATALOG
type: multiple_choice
required: false
options: Sim, ajudaria mais | Não, data e tipo bastam | Depende
-->

O que precisaria existir para você testar o Hermes com um atleta real? Há
algo que você não aceitaria de jeito nenhum?

<!-- TALLY ID: PROD_PILOT
type: long_text
required: false
-->

Você cobraria por atleta, por mês ou de outra forma?

<!-- TALLY ID: PROD_PRICE
type: multiple_choice
required: false
other: short_text
options: Por atleta | Por mês | Por pacote de serviços | Ainda não sei | Outro
-->

Que valor faria sentido se a ferramenta economizasse tempo e ajudasse a
acompanhar o plano?

<!-- TALLY ID: PROD_PRICE_VALUE
type: long_text
required: false
-->

Quer ver uma demonstração com os dados de um atleta?

<!-- TALLY ID: PROD_DEMO
type: multiple_choice
required: false
options: Quero ver | Gostaria, mas com ressalvas | Não agora
-->

Se sim, o que precisamos preservar como controle seu antes de qualquer
publicação?

<!-- TALLY ID: PROD_DEMO_CONTROL
type: long_text
required: false
show_if: PROD_DEMO ≠ "Não agora"
-->

Para um atleta que treina sem acompanhamento, o que o Hermes nunca deveria
fazer sozinho?

<!-- TALLY ID: SOLO_NEVER
type: long_text
required: false
-->

Que proteção você colocaria para esse atleta?

<!-- TALLY ID: SOLO_GUARD
type: checkboxes
required: false
other: short_text
options: Pedir novo teste | Avisar sobre muitas semanas pesadas | Limitar mudanças | Outro
-->

Se ele viajar, não tiver agenda ou ficar alguns dias sem treinar, como você
gostaria que o sistema reagisse?

<!-- TALLY ID: SOLO_ABSENCE
type: long_text
required: false
-->

Qual seria o primeiro tipo de plano seguro para um iniciante que treina
sozinho?

<!-- TALLY ID: SOLO_BEGINNER
type: long_text
required: false
-->

---

## 14. Comentários finais

<!-- TALLY PAGE: 14
SOURCE: ROTEIRO-TREINADOR §4 (encerramento) + PROMPT 35 §38–40
priority: essencial (EVIDENCE_SOURCE) / opcional (demais)
-->

Quando você usa números ou limites para tomar essas decisões, eles vêm
principalmente de onde?

<!-- TALLY ID: EVIDENCE_SOURCE
type: multiple_choice
required: true
other: short_text
options: Minha experiência prática | Formação/cursos | Literatura científica | Ferramentas/plataformas que uso | Uma combinação | Não costumo usar limites fixos | Outro
-->

Existe alguma coisa importante sobre como você treina seus atletas que não
perguntamos?

<!-- TALLY ID: FINAL_MISSING
type: long_text
required: false
-->

Se o Hermes pudesse ajudar em uma decisão do seu dia a dia como treinador,
qual seria a mais útil?

<!-- TALLY ID: FINAL_HERMES
type: long_text
required: false
-->

Qual seria a maior vantagem e o maior risco de recomendar o Hermes para outro
treinador?

<!-- TALLY ID: FINAL_ADVANTAGE
type: long_text
required: false
-->

O que faltaria para você usar hoje? Quais três melhorias você pediria
primeiro?

<!-- TALLY ID: FINAL_IMPROVE
type: long_text
required: false
-->

Se você explicasse essa ferramenta a um colega, como descreveria o valor
dela?

<!-- TALLY ID: FINAL_PITCH
type: long_text
required: false
-->

---

# Guia de configuração no Tally

Esta seção é **para nós**, não para o treinador. Ela não entra no formulário
publicado. A fonte canônica das perguntas continua sendo
`docs/ROTEIRO-TREINADOR.md`; este guia só traduz o roteiro para campos,
regras e rastreabilidade.

## Páginas

| # | Página | Origem no roteiro | Prioridade |
|---|---|---|---|
| 1 | Boas-vindas | §Antes de começar | boas-vindas, sem campos |
| 2 | Sobre você e seu trabalho | §3.1 + identificação mínima | essencial (nome/tempo) |
| 3 | Zonas de treino usadas atualmente pelo Hermes | adendo revisado + `src/coach.py:ZONE_BANDS` | essencial (avaliação da implementação real) |
| 4 | Como você define as zonas | §1.1 + §2.4 | essencial / se houver tempo |
| 5 | Como você percebe recuperação e fadiga | §1.2 | essencial |
| 6 | HRV e frequência cardíaca de repouso | §1.3 (HR-3) | essencial |
| 7 | Sono | §1.4 (HR-4) | essencial |
| 8 | Stress, dor muscular, motivação e fadiga | §1.4 (HR-4) | essencial |
| 9 | Carga e resposta ao treino | §2.1 e §2.2 | se houver tempo |
| 10 | Frequência cardíaca subindo em treino constante | §2.3 (HR-2) | se houver tempo |
| 11 | Quando os sinais se contradizem | §1.5 | essencial |
| 12 | Autonomia: o que o Hermes pode fazer | §1.6 + §1.2 | essencial, sempre por último |
| 13 | Produto: como isso entraria no seu trabalho | §3.1–3.3 + §2.1 | se houver tempo |
| 14 | Comentários finais | §4 + §38–40 | essencial (origem das decisões) |

A estrutura sugerida no pedido agrupava "quando mudaria um treino" e "quanto
automatizar" em duas páginas; o roteiro canônico concentra tudo em §1.6, então
aqui virou **uma** página (12). A página 10 existe porque §2.3 é um bloco
próprio no roteiro, não por decisão nova. A página 3 foi separada da 4 de
propósito: primeiro o treinador avalia a faixa real em uso, depois relata a
própria prática — são perguntas diferentes e não devem ser fundidas.

## Tabela de configuração

| ID | Página | Tipo | Obrigatória | Condição |
|---|---|---|---|---|
| COACH_NAME | 2. Sobre você | short_text | sim | — |
| COACH_TIME | 2. Sobre você | multiple_choice | sim | — |
| COACH_ATHLETES | 2. Sobre você | multiple_choice | não | — |
| COACH_MODALITY | 2. Sobre você | multiple_choice | não | — |
| COACH_PROFILE | 2. Sobre você | long_text | não | — |
| ZONES_CURRENT_MODEL | 3. Zonas (modelo atual) | multiple_choice | não | — |
| ZONES_PER_ZONE_REVIEW | 3. Zonas (modelo atual) | checkboxes | não | ZONES_CURRENT_MODEL ≠ "Sim, são bem parecidas" |
| ZONE1_REVIEW | 3. Zonas (modelo atual) | long_text | não | ZONES_PER_ZONE_REVIEW contém "Z1 — até 55% FTP" |
| ZONE2_REVIEW | 3. Zonas (modelo atual) | long_text | não | ZONES_PER_ZONE_REVIEW contém "Z2 — 56–75% FTP" |
| ZONE3_REVIEW | 3. Zonas (modelo atual) | long_text | não | ZONES_PER_ZONE_REVIEW contém "Z3 — 76–90% FTP" |
| SWEET_SPOT_REVIEW | 3. Zonas (modelo atual) | multiple_choice | não | ZONES_PER_ZONE_REVIEW contém "Sweet Spot — 84–97% FTP" |
| SWEET_SPOT_LIMITS | 3. Zonas (modelo atual) | short_text | não | SWEET_SPOT_REVIEW = "Mudaria os limites" |
| ZONE4_REVIEW | 3. Zonas (modelo atual) | long_text | não | ZONES_PER_ZONE_REVIEW contém "Z4 — 91–105% FTP" |
| ZONE5_REVIEW | 3. Zonas (modelo atual) | long_text | não | ZONES_PER_ZONE_REVIEW contém "Z5 — 106–120% FTP" |
| ZONE6_REVIEW | 3. Zonas (modelo atual) | long_text | não | ZONES_PER_ZONE_REVIEW contém "Z6 — 121–150% FTP" |
| ZONE7_NEED | 3. Zonas (modelo atual) | multiple_choice | não | — |
| ZONE7_HOW | 3. Zonas (modelo atual) | long_text | não | ZONE7_NEED ≠ "Não" |
| ZONE_PURPOSES | 3. Zonas (modelo atual) | yes_no | não | — |
| ZONE_PURPOSES_HOW | 3. Zonas (modelo atual) | long_text | não | ZONE_PURPOSES = Sim |
| ZONE_SIGNALS | 3. Zonas (modelo atual) | checkboxes | não | — |
| ZONE_REF | 4. Zonas (prática) | multiple_choice | sim | — |
| ZONE_NOFTP | 4. Zonas (prática) | checkboxes | não | ZONE_REF ≠ "FTP" |
| ZONE_FC_METHOD | 4. Zonas (prática) | multiple_choice | não | ZONE_REF em {FC, Combino, Depende} OU ZONE_NOFTP contém FC |
| ZONE_RPE | 4. Zonas (prática) | multiple_choice | não | — |
| ZONE_SWEETSAPOT | 4. Zonas (prática) | multiple_choice | não | — |
| ZONE_SWEETSAPOT_WHY | 4. Zonas (prática) | long_text | não | ZONE_SWEETSAPOT = "Depende" |
| ZONE_FIRST_ADJUST | 4. Zonas (prática) | long_text | não | — |
| ZONE_PER_ZONE | 4. Zonas (prática) | checkboxes | não | — |
| ZONE_CONTEXT | 4. Zonas (prática) | checkboxes | não | — |
| ZONE_UPDATE_WHEN | 4. Zonas (prática) | checkboxes | não | — |
| ZONE_FINAL_SAY | 4. Zonas (prática) | multiple_choice | não | — |
| RECOVERY_OPEN | 5. Recuperação | long_text | sim | — |
| RECOVERY_SIGNALS | 5. Recuperação | checkboxes | sim | — |
| RECOVERY_NEVER | 5. Recuperação | checkboxes | não | — |
| RECOVERY_TOLERANCE | 5. Recuperação | multiple_choice | não | — |
| RECOVERY_PHASE | 5. Recuperação | checkboxes | não | — |
| HRV_USE | 6. HRV/FCR | multiple_choice | sim | RECOVERY_SIGNALS contém HRV |
| HRV_TREND | 6. HRV/FCR | multiple_choice | não | HRV_USE em {Sim, Às vezes} |
| HRV_SINGLE_DAY | 6. HRV/FCR | multiple_choice | não | HRV_USE em {Sim, Às vezes} |
| RHR_USE | 6. HRV/FCR | multiple_choice | sim | RECOVERY_SIGNALS contém FCR |
| RHR_PATTERN | 6. HRV/FCR | multiple_choice | não | RHR_USE em {Sim, Às vezes} |
| RHR_SENSOR | 6. HRV/FCR | long_text | não | RHR_USE em {Sim, Às vezes} |
| RHR_ILLNESS | 6. HRV/FCR | long_text | não | RHR_USE em {Sim, Às vezes} |
| RHR_PROTOCOL | 6. HRV/FCR | long_text | não | RHR_USE em {Sim, Às vezes} |
| SLEEP_USE | 7. Sono | checkboxes | não | RECOVERY_SIGNALS contém Sono |
| SLEEP_ONE_NIGHT | 7. Sono | multiple_choice | não | SLEEP_USE sem "Não costumo usar" |
| SLEEP_DEBT | 7. Sono | long_text | não | SLEEP_USE sem "Não costumo usar" |
| SLEEP_SCORE_PREFERENCE | 7. Sono | multiple_choice | não | SLEEP_USE contém "Nota fornecida pelo relógio/app" |
| SLEEP_SCORE_TRUST | 7. Sono | multiple_choice | não | SLEEP_USE contém "Nota fornecida pelo relógio/app" |
| SLEEP_SCORE_COMPARE | 7. Sono | multiple_choice | não | SLEEP_SCORE_TRUST respondida |
| STRESS_USE | 8. Bem-estar | checkboxes | não | RECOVERY_SIGNALS contém Stress |
| STRESS_TREND | 8. Bem-estar | long_text | não | STRESS_USE respondida e sem "Não costumo usar" |
| STRESS_SCALE | 8. Bem-estar | yes_no | não | STRESS_TREND respondida |
| STRESS_SCALE_NAME | 8. Bem-estar | short_text | não | STRESS_SCALE = Sim |
| SORENESS_USE | 8. Bem-estar | multiple_choice | não | RECOVERY_SIGNALS contém Dor muscular |
| SORENESS_DOMS | 8. Bem-estar | multiple_choice | não | SORENESS_USE em {Frequentemente, Às vezes} |
| SORENESS_DOMS_HOW | 8. Bem-estar | long_text | não | SORENESS_DOMS em {Sim, Às vezes, Depende} |
| SORENESS_REGION | 8. Bem-estar | checkboxes | não | SORENESS_USE em {Frequentemente, Às vezes} |
| SORENESS_WHEN | 8. Bem-estar | multiple_choice | não | SORENESS_USE em {Frequentemente, Às vezes} |
| SORENESS_SCALE | 8. Bem-estar | yes_no | não | SORENESS_USE em {Frequentemente, Às vezes} |
| SORENESS_SCALE_NAME | 8. Bem-estar | short_text | não | SORENESS_SCALE = Sim |
| MOTIVATION_USE | 8. Bem-estar | multiple_choice | não | RECOVERY_SIGNALS contém Motivação |
| MOTIVATION_SINGLE | 8. Bem-estar | multiple_choice | não | MOTIVATION_USE em {Sim, Às vezes} |
| MOTIVATION_KIND | 8. Bem-estar | long_text | não | MOTIVATION_USE em {Sim, Às vezes} |
| FATIGUE_USE | 8. Bem-estar | checkboxes | não | RECOVERY_SIGNALS contém "Como ele diz que está se sentindo" |
| FATIGUE_INDEP | 8. Bem-estar | long_text | não | FATIGUE_USE respondida e sem "Não costumo separar" |
| READINESS_USE | 8. Bem-estar | multiple_choice | não | sempre |
| READINESS_ROLE | 8. Bem-estar | multiple_choice | não | READINESS_USE respondida |
| READINESS_DISCORD | 8. Bem-estar | long_text | não | READINESS_ROLE respondida |
| WEEK_STRUCTURE | 9. Carga | long_text | não | — |
| FORM_USE | 9. Carga | multiple_choice | não | — |
| FORM_HOW | 9. Carga | long_text | não | FORM_USE em {Sim, Às vezes} |
| WEEK_LOAD_HIGH | 9. Carga | checkboxes | não | — |
| WEEK_MISSED | 9. Carga | long_text | não | — |
| DELOAD_USE | 9. Carga | multiple_choice | não | — |
| DELOAD_HOW | 9. Carga | long_text | não | DELOAD_USE começa com "Sim" |
| BLOCK_PROGRESSION | 9. Carga | long_text | não | — |
| ATHLETE_PROFILE_IMPACT | 9. Carga | long_text | não | — |
| RETURN_PAUSE | 9. Carga | long_text | não | — |
| RAMP_USE | 9. Carga | multiple_choice | não | — |
| RAMP_CONCERN | 9. Carga | long_text | não | RAMP_USE em {Sim, Às vezes} |
| RAMP_INDIVIDUAL | 9. Carga | multiple_choice | não | RAMP_USE em {Sim, Às vezes} |
| RAMP_INDIVIDUAL_HOW | 9. Carga | long_text | não | RAMP_INDIVIDUAL em {Sim, Depende} |
| RAMP_IGNORE | 9. Carga | checkboxes | não | RAMP_USE em {Sim, Às vezes} |
| RETURN_RECOVERY_WEEK | 9. Carga | long_text | não | — |
| PWHR_OBSERVE | 10. Pw:HR | multiple_choice | sim | — |
| PWHR_SCOPE | 10. Pw:HR | long_text | não | PWHR_OBSERVE em {Sim, Às vezes} |
| PWHR_CAVEATS | 10. Pw:HR | checkboxes | não | PWHR_OBSERVE em {Sim, Às vezes} |
| PWHR_PICK | 10. Pw:HR | multiple_choice | não | PWHR_OBSERVE em {Sim, Às vezes} |
| PWHR_GOOD_SEGMENT | 10. Pw:HR | long_text | não | PWHR_OBSERVE em {Sim, Às vezes} |
| PWHR_LIMIT | 10. Pw:HR | yes_no | não | PWHR_OBSERVE em {Sim, Às vezes} |
| PWHR_LIMIT_VALUE | 10. Pw:HR | short_text | não | PWHR_LIMIT = Sim |
| PWHR_LIMIT_SOURCE | 10. Pw:HR | multiple_choice | não | PWHR_LIMIT = Sim |
| CONFLICT_1 | 11. Conflitos | multiple_choice | não | — |
| CONFLICT_1_DEP | 11. Conflitos | long_text | não | CONFLICT_1 = "Depende" |
| CONFLICT_2 | 11. Conflitos | multiple_choice | não | — |
| CONFLICT_3 | 11. Conflitos | multiple_choice | não | — |
| CONFLICT_4 | 11. Conflitos | multiple_choice | não | — |
| CONFLICT_RECHECK | 11. Conflitos | long_text | não | — |
| AUTOMATION_LEVEL | 12. Autonomia | multiple_choice | sim | — |
| AUTOMATION_CHANGE | 12. Autonomia | multiple_choice | sim | — |
| CHANGE_TYPES | 12. Autonomia | checkboxes | não | AUTOMATION_LEVEL = "Sugerir" OU AUTOMATION_CHANGE ∈ {Sim…} |
| AUTOMATION_NEVER | 12. Autonomia | long_text | não | — |
| PROD_FIRST_SCREEN | 13. Produto | checkboxes | não | — |
| PROD_ALERTS | 13. Produto | long_text | não | — |
| PROD_APPROVAL | 13. Produto | multiple_choice | não | — |
| PROD_APPROVAL_PENDING | 13. Produto | multiple_choice | não | PROD_APPROVAL respondida |
| PROD_ADJUST | 13. Produto | checkboxes | não | — |
| PROD_TODAY | 13. Produto | long_text | não | — |
| PROD_REPORT_CONTENT | 13. Produto | checkboxes | não | — |
| PROD_REPORT | 13. Produto | long_text | não | PROD_REPORT_CONTENT respondida |
| PLAN_SOURCE | 13. Produto | multiple_choice | não | — |
| MULTI_RACE | 13. Produto | long_text | não | — |
| PROD_RACE_CATALOG | 13. Produto | multiple_choice | não | — |
| PROD_PILOT | 13. Produto | long_text | não | — |
| PROD_PRICE | 13. Produto | multiple_choice | não | — |
| PROD_PRICE_VALUE | 13. Produto | long_text | não | — |
| PROD_DEMO | 13. Produto | multiple_choice | não | — |
| PROD_DEMO_CONTROL | 13. Produto | long_text | não | PROD_DEMO ≠ "Não agora" |
| SOLO_NEVER | 13. Produto | long_text | não | — |
| SOLO_GUARD | 13. Produto | checkboxes | não | — |
| SOLO_ABSENCE | 13. Produto | long_text | não | — |
| SOLO_BEGINNER | 13. Produto | long_text | não | — |
| EVIDENCE_SOURCE | 14. Finais | multiple_choice | sim | — |
| FINAL_MISSING | 14. Finais | long_text | não | — |
| FINAL_HERMES | 14. Finais | long_text | não | — |
| FINAL_ADVANTAGE | 14. Finais | long_text | não | — |
| FINAL_IMPROVE | 14. Finais | long_text | não | — |
| FINAL_PITCH | 14. Finais | long_text | não | — |

**Política de obrigatoriedade:** só é obrigatório o que estrutura o
formulário — identificação (2 campos), âncora aberta da prática
(`RECOVERY_OPEN`), controladores de ramificação (`ZONE_REF`,
`RECOVERY_SIGNALS`, `HRV_USE`, `RHR_USE`, `PWHR_OBSERVE`), os dois nós de
autonomia (`AUTOMATION_LEVEL`, `AUTOMATION_CHANGE`) e a origem das decisões
(`EVIDENCE_SOURCE`). São **11 de 129** campos obrigatórios; todo o resto é
opcional. Exceção consciente: `ZONES_CURRENT_MODEL` também controla
ramificação (página 3), mas é opcional de propósito — se o treinador não quiser
avaliar o modelo atual, o bloco de faixas some e o formulário segue inteiro.
Condições que dependem de um campo opcional sem resposta tratam a
resposta vazia como "não marcado" → bloco oculto.

## Lógica condicional

<!-- TALLY LOGIC
IF RECOVERY_SIGNALS não contém "HRV / variabilidade da frequência cardíaca"
THEN skip HRV_BLOCK
-->

<!-- TALLY LOGIC
IF HRV_USE = "Não"
THEN skip HRV_DETAILS (HRV_TREND, HRV_SINGLE_DAY)
-->

<!-- TALLY LOGIC
IF RECOVERY_SIGNALS não contém "Frequência cardíaca de repouso"
THEN skip RHR_BLOCK
-->

<!-- TALLY LOGIC
IF RHR_USE = "Não"
THEN skip RHR_DETAILS (RHR_PATTERN, RHR_SENSOR, RHR_ILLNESS, RHR_PROTOCOL)
-->

<!-- TALLY LOGIC
IF RECOVERY_SIGNALS não contém "Sono"
THEN skip SLEEP_BLOCK
-->

<!-- TALLY LOGIC
IF SLEEP_USE contém "Não costumo usar dados de sono"
THEN skip SLEEP_DETAILS (SLEEP_ONE_NIGHT, SLEEP_DEBT)
-->

<!-- TALLY LOGIC
IF SLEEP_USE não contém "Nota fornecida pelo relógio/app"
THEN skip SLEEP_SCORE_BLOCK (SLEEP_SCORE_PREFERENCE, SLEEP_SCORE_TRUST,
                              SLEEP_SCORE_COMPARE)
-->

<!-- TALLY LOGIC
IF RECOVERY_SIGNALS não contém "Stress"
THEN skip STRESS_BLOCK
-->

<!-- TALLY LOGIC
IF STRESS_USE contém "Não costumo usar stress"
THEN skip STRESS_TREND, STRESS_SCALE, STRESS_SCALE_NAME
IF STRESS_TREND não está respondida
THEN skip STRESS_SCALE, STRESS_SCALE_NAME
IF STRESS_SCALE ≠ Sim THEN skip STRESS_SCALE_NAME
-->

<!-- TALLY LOGIC
IF RECOVERY_SIGNALS não contém "Dor muscular / pernas pesadas"
THEN skip SORENESS_BLOCK
-->

<!-- TALLY LOGIC
IF SORENESS_USE = "Não"
THEN skip SORENESS_DETAILS (SORENESS_DOMS, SORENESS_DOMS_HOW, SORENESS_REGION,
                            SORENESS_WHEN, SORENESS_SCALE, SORENESS_SCALE_NAME)
-->

<!-- TALLY LOGIC
IF RECOVERY_SIGNALS não contém "Motivação"
THEN skip MOTIVATION_BLOCK
-->

<!-- TALLY LOGIC
IF MOTIVATION_USE = "Não"
THEN skip MOTIVATION_DETAILS (MOTIVATION_SINGLE, MOTIVATION_KIND)
-->

<!-- TALLY LOGIC
IF RECOVERY_SIGNALS não contém "Como ele diz que está se sentindo"
THEN skip FATIGUE_BLOCK
-->

<!-- TALLY LOGIC
IF FATIGUE_USE contém "Não costumo separar"
THEN skip FATIGUE_INDEP
-->

<!-- TALLY LOGIC
IF ZONES_CURRENT_MODEL = "Sim, são bem parecidas"
THEN skip ZONES_PER_ZONE_REVIEW e todos os reviews por faixa
IF ZONES_PER_ZONE_REVIEW não contém "Z1 — até 55% FTP"
THEN skip ZONE1_REVIEW
IF ZONES_PER_ZONE_REVIEW não contém "Z2 — 56–75% FTP"
THEN skip ZONE2_REVIEW
IF ZONES_PER_ZONE_REVIEW não contém "Z3 — 76–90% FTP"
THEN skip ZONE3_REVIEW
IF ZONES_PER_ZONE_REVIEW não contém "Sweet Spot — 84–97% FTP"
THEN skip SWEET_SPOT_REVIEW
IF SWEET_SPOT_REVIEW ≠ "Mudaria os limites"
THEN skip SWEET_SPOT_LIMITS
IF ZONES_PER_ZONE_REVIEW não contém "Z4 — 91–105% FTP"
THEN skip ZONE4_REVIEW
IF ZONES_PER_ZONE_REVIEW não contém "Z5 — 106–120% FTP"
THEN skip ZONE5_REVIEW
IF ZONES_PER_ZONE_REVIEW não contém "Z6 — 121–150% FTP"
THEN skip ZONE6_REVIEW
IF ZONE7_NEED = "Não"
THEN skip ZONE7_HOW
IF ZONE_PURPOSES ≠ Sim
THEN skip ZONE_PURPOSES_HOW
-->

<!-- TALLY LOGIC
IF ZONE_REF = "FTP"
THEN skip ZONE_NOFTP
IF ZONE_REF ∉ {"Frequência cardíaca", "Combino mais de uma", "Depende do atleta"}
   E ZONE_NOFTP não contém "Frequência cardíaca"
THEN skip ZONE_FC_METHOD
IF ZONE_SWEETSAPOT ≠ "Depende"
THEN skip ZONE_SWEETSAPOT_WHY
-->

<!-- TALLY LOGIC
IF FORM_USE ∉ {Sim, Às vezes} THEN skip FORM_HOW
IF DELOAD_USE não começa com "Sim" THEN skip DELOAD_HOW
IF RAMP_USE ∉ {Sim, Às vezes}
THEN skip RAMP_DETAILS (RAMP_CONCERN, RAMP_INDIVIDUAL, RAMP_INDIVIDUAL_HOW,
                        RAMP_IGNORE)
IF RAMP_INDIVIDUAL = "Não" THEN skip RAMP_INDIVIDUAL_HOW
-->

<!-- TALLY LOGIC
IF PWHR_OBSERVE ∉ {Sim, Às vezes}
THEN skip PWHR_DETAILS (PWHR_SCOPE, PWHR_CAVEATS, PWHR_PICK,
                         PWHR_GOOD_SEGMENT, PWHR_LIMIT,
                         PWHR_LIMIT_VALUE, PWHR_LIMIT_SOURCE)
IF PWHR_LIMIT ≠ Sim THEN skip PWHR_LIMIT_VALUE, PWHR_LIMIT_SOURCE
+ exibir o texto: "O Hermes consegue medir esse comportamento. Queremos
  entender quando ele realmente é útil para você."
-->

<!-- TALLY LOGIC
IF CONFLICT_1 ≠ "Depende" THEN skip CONFLICT_1_DEP
-->

<!-- TALLY LOGIC
IF AUTOMATION_LEVEL ≠ "Sugerir uma mudança"
   E AUTOMATION_CHANGE ∉ {"Sim, mas apenas em situações bem definidas", "Sim"}
THEN skip CHANGE_TYPES
-->

<!-- TALLY LOGIC
IF PROD_DEMO = "Não agora" THEN skip PROD_DEMO_CONTROL
IF PROD_APPROVAL não está respondida THEN skip PROD_APPROVAL_PENDING
IF PROD_REPORT_CONTENT não está respondida THEN skip PROD_REPORT
IF SORENESS_SCALE ≠ Sim THEN skip SORENESS_SCALE_NAME
IF READINESS_USE não está respondida THEN skip READINESS_ROLE
IF READINESS_ROLE não está respondida THEN skip READINESS_DISCORD
-->

<!-- TALLY LOGIC
IF todas as perguntas de uma página estiverem ocultas
THEN ocultar a página inteira
(ex.: página 6 sem HRV e sem FCR em RECOVERY_SIGNALS; página 10 se
 PWHR_OBSERVE não for respondida e os dependentes ficarem ocultos)
-->

## Validações e limites

- O Markdown deste arquivo é válido e importável como documento normal
  (headings, parágrafos, listas). Os comentários `<!-- TALLY ... -->` **não**
  são importados: eles documentam a configuração a fazer depois, dentro do
  Tally.
- Tipos usados: `short_text`, `long_text`, `multiple_choice`, `checkboxes`,
  `yes_no`. Nenhum `number` ou `scale` foi criado — o roteiro não pede escala
  numérica fixa (ver §29: escala só entra depois que o treinador confirma que
  usa; os casos explícitos são `SORENESS_SCALE` e `STRESS_SCALE`, e ambos só
  perguntam se existe escala — nenhum número ou direção foi sugerido).
- `Outro` em `multiple_choice`/`checkboxes` sempre abre um campo de texto
  curto (`other: short_text`).
- A tabela da página 3 ("Zonas de treino usadas atualmente pelo Hermes") é
  leitura de `src/coach.py:ZONE_BANDS`: Z1–Z6 + Sweet Spot, **sem Z7** (Z7 é
  potência máxima, não faixa de %FTP). Os valores foram conferidos contra o
  código e contra o literal de
  `test_zona_bands_espelham_a_tabela_do_documento`. Se as faixas mudarem no
  código, atualizar a tabela aqui — ela não é decisão de produto nem tabela
  científica, e Sweet Spot sobrepõe de propósito Z3/Z4.
- Nenhuma resposta deste formulário cria limite, alerta ou mudança automática.
  Ele só captura respostas; a decisão técnica fica depois (ver
  `ROTEIRO-TREINADOR.md` §5).
- Nenhum valor de escala, direção de métrica ou faixa de corte foi
  pré-definido aqui. `stress`, nota de sono e nota de prontidão continuam com
  direção e faixa indefinidas até a pendência de HR-4 ser resolvida
  (`STRESS_SCALE`/`SORENESS_SCALE` só registram se o treinador usa uma escala).
  `PWHR_LIMIT_VALUE` é texto livre do treinador: nenhum cutoff sugerido —
  HR-2 registra explicitamente que não há limite de 5%.
- As medidas oferecidas em `SLEEP_USE` ("Tempo na cama", "Eficiência do sono")
  são prática do treinador, não campos atuais do provedor: `src/provider_fields.py`
  só mapeia `sleep_secs` e `sleep_score`. Não dizer ao treinador que o Hermes
  coleta essas medidas.
- `PROD_APPROVAL_PENDING` cobre a decisão P1 de `PORTAL-UI-DESIGN.md`
  (aprovação atrasada) e é a única pergunta cuja origem não está no roteiro
  canônico. Se o P1 for decidido em outro lugar, reavaliar a pergunta.
- `READINESS_USE` aparece mesmo sem depender de `RECOVERY_SIGNALS`: o treinador
  pode usar nota de prontidão do relógio sem ter marcado nenhum sinal
  subjetivo na página 5.

## Cobertura vs. roteiro canônico

Checklist interno de §47 — cada conceito tem ao menos um ID:

- [x] zona (`ZONES_CURRENT_MODEL`, `ZONES_PER_ZONE_REVIEW`,
      `ZONE1_REVIEW`–`ZONE6_REVIEW`, `SWEET_SPOT_REVIEW`, `SWEET_SPOT_LIMITS`,
      `ZONE7_NEED`, `ZONE7_HOW`, `ZONE_PURPOSES`, `ZONE_PURPOSES_HOW`,
      `ZONE_SIGNALS`, `ZONE_REF`, `ZONE_FC_METHOD`, `ZONE_PER_ZONE`,
      `ZONE_CONTEXT`, `ZONE_UPDATE_WHEN`, `ZONE_FINAL_SAY`)
- [x] potência (`ZONE_REF`, `ZONE_NOFTP`, `PROD_ADJUST`)
- [x] frequência cardíaca (`ZONE_FC_METHOD`, `ZONE_NOFTP`)
- [x] RPE (`ZONE_RPE`)
- [x] recuperação (`RECOVERY_OPEN`, `RECOVERY_SIGNALS`, `RECOVERY_TOLERANCE`,
      `RECOVERY_PHASE`)
- [x] HRV (`HRV_USE`, `HRV_TREND`, `HRV_SINGLE_DAY`)
- [x] RHR (`RHR_USE`, `RHR_PATTERN`, `RHR_SENSOR`, `RHR_ILLNESS`,
      `RHR_PROTOCOL`)
- [x] sono (`SLEEP_USE`, `SLEEP_ONE_NIGHT`, `SLEEP_DEBT`,
      `SLEEP_SCORE_PREFERENCE`, `SLEEP_SCORE_TRUST`, `SLEEP_SCORE_COMPARE`)
- [x] stress (`STRESS_USE`, `STRESS_TREND`, `STRESS_SCALE`,
      `STRESS_SCALE_NAME`)
- [x] soreness (`SORENESS_USE`, `SORENESS_DOMS`, `SORENESS_DOMS_HOW`,
      `SORENESS_REGION`, `SORENESS_WHEN`, `SORENESS_SCALE`,
      `SORENESS_SCALE_NAME`)
- [x] motivation (`MOTIVATION_USE`, `MOTIVATION_SINGLE`, `MOTIVATION_KIND`)
- [x] fatigue (`FATIGUE_USE`, `FATIGUE_INDEP`)
- [x] notas de prontidão (`READINESS_USE`, `READINESS_ROLE`,
      `READINESS_DISCORD`)
- [x] ramp (`RAMP_USE`, `RAMP_CONCERN`, `RAMP_INDIVIDUAL`,
      `RAMP_INDIVIDUAL_HOW`, `RAMP_IGNORE`, `RETURN_PAUSE`,
      `RETURN_RECOVERY_WEEK`)
- [x] Pw:HR (`PWHR_OBSERVE`, `PWHR_SCOPE`, `PWHR_CAVEATS`, `PWHR_PICK`,
      `PWHR_GOOD_SEGMENT`, `PWHR_LIMIT`, `PWHR_LIMIT_VALUE`,
      `PWHR_LIMIT_SOURCE`)
- [x] conflitos (`CONFLICT_1` a `CONFLICT_4`, `CONFLICT_RECHECK`)
- [x] mudança de treino (`CHANGE_TYPES`, `AUTOMATION_NEVER`, `PROD_APPROVAL`,
      `PROD_APPROVAL_PENDING`)
- [x] automação (`AUTOMATION_LEVEL`, `AUTOMATION_CHANGE`)
- [x] evidência/experiência (`EVIDENCE_SOURCE`)
- [x] carga/periodização (`WEEK_STRUCTURE`, `FORM_USE`, `FORM_HOW`,
      `WEEK_LOAD_HIGH`, `WEEK_MISSED`, `DELOAD_USE`, `DELOAD_HOW`,
      `BLOCK_PROGRESSION`, `ATHLETE_PROFILE_IMPACT`)
- [x] progressão semanal, gate PROG-1/2 (`PROG_Q1`–`PROG_Q4`, SEÇÃO D / §12.2) —
      **aberto**; sem resposta, PROG-2 permanece bloqueado
- [x] produto e piloto (`PROD_*`, `PLAN_SOURCE`, `MULTI_RACE`, `SOLO_*`)

### Cobertura fina (PROMPT 36)

Re-auditoria linha a linha do roteiro canônico contra este arquivo. Cada linha
que não estava representada na precisão certa ganhou campo próprio:

| origem | o que faltava | campo criado |
|---|---|---|
| §1.4 sono | tempo na cama e eficiência, além de horas dormidas | opções novas em `SLEEP_USE` |
| §1.4 sono | nota pronta **ou** dados por trás dela | `SLEEP_SCORE_PREFERENCE` |
| §1.4 readiness | só contexto ou influência na decisão | `READINESS_ROLE` |
| §1.4 (§5.3) | escala usada pelo treinador para stress | `STRESS_SCALE`, `STRESS_SCALE_NAME` |
| §2.2 ramp | o critério de "rápido" muda com o atleta? | `RAMP_INDIVIDUAL`, `RAMP_INDIVIDUAL_HOW` |
| §2.3 Pw:HR | qual é o limite e de onde ele vem | `PWHR_LIMIT_VALUE`, `PWHR_LIMIT_SOURCE` |
| §2.1 relatório | quais blocos entram no resumo e o que seria ruído | `PROD_REPORT_CONTENT` + reenunciar `PROD_REPORT` |
| PORTAL-UI P1 | aprovação que não chega a tempo | `PROD_APPROVAL_PENDING` |
| STATUS | publicação diária atual (verdade operacional) | linha de contexto da página 12 |
| §1.8 (PROMPT 68) | gate operacional de progressão semanal (adesão/incompletos/dimensão/recuperação) — distinto de `WEEK_MISSED`/`BLOCK_PROGRESSION`/`DELOAD_USE` | `PROG_Q1`–`PROG_Q4`, SEÇÃO D (§12.2) |

Status por seção do §1–§4: **0 lacunas de decisão do treinador restantes**;
os itens classificados como internos (§5.1–§5.5, §6) e os avaliados e
recusados (assistente de IA #13/#29, módulo de corrida #18, estrutura de
intervalos de VO2 — roteada pelo EMBASAMENTO §11 ao roteiro canônico, que não
quer mudar aqui) estão listados no relatório desta re-auditoria.

Consolidações (§48), para rastrear de onde veio cada pergunta:

| pergunta do formulário | origens consolidadas |
|---|---|
| `AUTOMATION_LEVEL` | §1.2 ("só avisar ou mudaria o treino") + §1.6 + §35 |
| `PROD_REPORT` | §2.1 (relatório semanal/mensal) + §3.1 (o que o atleta leria) — detalhe de conteúdo em `PROD_REPORT_CONTENT`, §2.1 |
| `EVIDENCE_SOURCE` | §5.1 (classificação de resposta). Origem de §2.3 saiu para `PWHR_LIMIT_SOURCE` (pergunta específica antes do fechamento) |
| `SLEEP_USE` | §1.4 pergunta de quantidade/qualidade + §22 (checkbox de sono) |
| `ZONE_REF` | §1.1 (FTP ou outro) + §13 (lista de referências) |
| `CONFLICT_2` | §1.5 cenário 2 (RHR normal + cansaço) + §33 (dados do relógio + cansaço) |

Repetições mantidas de propósito (ambas as perguntas foram pedidas
explicitamente; nenhuma foi removida por conta própria):

- **Sweet Spot**: `SWEET_SPOT_REVIEW` (adendo revisado — avalia a faixa 84–97%
  da tabela atual, na página 3) e `ZONE_SWEETSAPOT` (§15 — "faixa própria na
  hora de montar os treinos", com follow-up `ZONE_SWEETSAPOT_WHY` em
  "Depende", na página 4). Decidir na importação se o treinador acha
  repetitivo; se consolidar, manter os dois mapeamentos de origem.
- **Sinais de intensidade**: `ZONE_SIGNALS` (adendo — o que confirma a
  intensidade além da potência) encosta em `ZONE_NOFTP` (§1.1, substituição
  quando falta FTP) e `ZONE_RPE` (§1.6/§13, sensação de esforço sem sensores).
  São perguntas diferentes (confirmar no treino vs. escolher a referência de
  zonas), então ficaram separadas.

O que **não** entrou no formulário, por ser material interno do roteiro:
§5.1 (modelo de registro da resposta), §5.2 (mapa técnico), §5.3 (estado
atual), §5.4 (perguntas de demo), §5.5 (material de referência) e §6 (sugestão
de execução em dois encontros). Eles continuam valendo para quem conduz a
entrevista, não para quem responde.

## Checklist pós-importação

- [ ] Importar apenas as seções 1 a 14; **excluir** este guia e o aviso de
      derivação do topo do formulário publicado
- [ ] Revisar headings/páginas (14 páginas na ordem acima)
- [ ] Confirmar que a tabela de faixas da página 3 importou como tabela
      (reconstruir dentro do Tally se o import quebrar a formatação)
- [ ] Conferir os valores da tabela contra `src/coach.py:ZONE_BANDS` antes de
      publicar (sem Z7; Sweet Spot sobreposto a Z3/Z4 de propósito)
- [ ] Transformar opções em campos do Tally, preservando a ordem dos textos
- [ ] Marcar os 11 campos obrigatórios da tabela
- [ ] Configurar `Outro` → texto curto onde a tabela indicar
- [ ] Configurar lógica condicional (bloco acima), incluindo ocultar páginas
      vazias
- [ ] Confirmar que nenhum campo vem pré-marcado (`RECOVERY_SIGNALS`,
      `SLEEP_USE`, `STRESS_USE`, `FATIGUE_USE`)
- [ ] Testar todos os caminhos: com e sem cada sinal da página 5; com e sem
      cada faixa marcada em `ZONES_PER_ZONE_REVIEW` na página 3; com
      `RAMP_USE = Não`, `PWHR_LIMIT = Não` e `PROD_APPROVAL` sem resposta
- [ ] Reconfirmar que a linha de estado da página 12 (publicação automática do
      dia) ainda descreve o comportamento real (`scripts/daily_reconcile.sh`)
- [ ] Testar mobile
- [ ] Responder o formulário de ponta a ponta como se fosse o treinador
- [ ] Confirmar que nenhuma pergunta técnica aparece ao treinador
