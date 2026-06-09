# Checklist de Melhorias Profissionais

## 1. Remover viés fixo para Paraíba/UFPB

### Problema atual

O bot aceita país e estado, mas internamente ainda parece enviesado para:

```txt
BR/PB
UFPB
editais_pb
Governo da Paraíba
```

Isso é ruim porque o usuário pode pedir outro estado e receber coisa da Paraíba. Profissionalmente, isso quebra confiança.

### Melhorias

* [ ] Criar um catálogo de fontes por país e estado.
* [ ] Separar `sources` por região: `br_pb`, `br_sp`, `br_rj`, `br_pe`, etc.
* [ ] Fazer o bot só consultar fontes compatíveis com o estado solicitado.
* [ ] Se não houver fonte cadastrada para o estado, retornar mensagem clara.
* [ ] Remover fallback automático para Paraíba quando o estado não tiver suporte.
* [ ] Criar um campo `supported_regions`.
* [ ] Criar comando `/regioes` para listar regiões suportadas.
* [ ] Criar comando `/fontes` para listar fontes disponíveis.
* [ ] Adicionar testes garantindo que busca por `BA` não retorna `PB`.

### Plano de implementação

Criar um arquivo:

```txt
scraper/source_registry.py
```

Exemplo de estrutura:

```python
SOURCE_REGISTRY = {
    "BR": {
        "PB": ["ufpb", "editais_pb"],
        "PE": ["ufpe", "editais_pe"],
        "SP": ["usp", "unesp", "unicamp", "editais_sp"],
        "RJ": ["ufrj", "uerj", "editais_rj"],
    }
}
```

O `build_search_request()` deve receber `country/state` e selecionar as fontes com base nesse registro.

### Prompt para Codex

```txt
@bot_manager

Objetivo: remover o viés fixo do bot para Paraíba/UFPB.

Use create-plan antes de implementar.

Escopo:
1. Criar um registro central de fontes por país e estado em `scraper/source_registry.py`.
2. Garantir que buscas para um estado só usem fontes daquele estado.
3. Se o estado não tiver fontes cadastradas, retornar `status=empty` com warning claro.
4. Não usar Paraíba como fallback silencioso.
5. Criar testes garantindo que busca por `BA`, `SP` ou `RJ` não retorna fontes `PB`.
6. Atualizar documentação.

Não alterar contratos JSON sem aprovação.
```

---

## 2. Melhorar a experiência de conversa no Telegram

### Problema atual

O fluxo é funcional, mas seco demais:

```txt
País da busca? Envie BR.
Estado? Envie a sigla. Ex.: PB
```

Funciona, mas não orienta bem o usuário.

### Melhorias

* [ ] Criar `/start` com explicação curta.
* [ ] Criar `/ajuda`.
* [ ] Criar `/buscar`.
* [ ] Criar `/regioes`.
* [ ] Criar `/fontes`.
* [ ] Criar `/sobre`.
* [ ] Validar país inválido.
* [ ] Validar estado inválido.
* [ ] Permitir usuário digitar “Paraíba” além de `PB`.
* [ ] Permitir usuário digitar “São Paulo” além de `SP`.
* [ ] Adicionar botões inline para escolher país e estado.
* [ ] Adicionar botão “Nova busca”.
* [ ] Adicionar botão “Abrir edital”.
* [ ] Adicionar botão “Ver próxima página”.

### Plano de implementação

Usar `InlineKeyboardMarkup` do `python-telegram-bot`.

Fluxo ideal:

```txt
/start
↓
Bot explica o que faz
↓
Botão: Buscar oportunidades
↓
Selecionar país
↓
Selecionar estado
↓
Selecionar tipo: Mestrado, Doutorado, Concurso, Todos
↓
Resultado paginado
```

### Prompt para Codex

```txt
@telegram_specialist

Melhore a UX do bot Telegram sem alterar a pipeline do scraper.

Escopo:
1. Adicionar comandos `/ajuda`, `/regioes`, `/fontes` e `/sobre`.
2. Melhorar mensagens de `/start` e `/buscar`.
3. Adicionar validação amigável para país e estado inválidos.
4. Permitir nomes de estados além de siglas.
5. Adicionar botão de "Nova busca".
6. Manter mensagens curtas usando a skill stop-slop.
7. Não alterar scraper, schemas ou contratos JSON.

Entregar testes ou validação manual documentada.
```

---

## 3. Paginar resultados

### Problema atual

O bot retorna muitos itens em uma mensagem gigante. Isso é ruim no Telegram e ruim para leitura.

### Melhorias

* [ ] Limitar resultados por mensagem.
* [ ] Exibir 3 a 5 oportunidades por página.
* [ ] Criar botões “Próximo” e “Anterior”.
* [ ] Guardar contexto da busca por usuário.
* [ ] Evitar mensagem enorme com 15 resultados de uma vez.
* [ ] Permitir `/buscar` iniciar nova consulta.

### Plano de implementação

Adicionar paginação no `telegram_bot/messages.py`.

Exemplo:

```txt
Resultados: 15 encontrados
Página 1/3

1. Edital...
2. Edital...
3. Edital...

[Anterior] [Próximo]
```

### Prompt para Codex

```txt
@telegram_specialist

Implemente paginação dos resultados no Telegram.

Regras:
1. Mostrar no máximo 5 oportunidades por mensagem.
2. Adicionar botões "Próximo", "Anterior" e "Nova busca".
3. Não alterar a estrutura do JSON retornado pelo scraper.
4. Guardar estado mínimo da busca por usuário.
5. Evitar mensagens longas que dificultem leitura no Telegram.

Use stop-slop para manter os textos objetivos.
```

---

## 4. Melhorar qualidade dos resultados

### Problema atual

O bot retorna algumas oportunidades genéricas demais, como:

```txt
Educação
Ciência, Tecnologia, Inovação e Ensino Superior
```

Isso mostra que o scraper está pegando páginas amplas demais, não necessariamente editais úteis.

### Melhorias

* [ ] Criar filtro de relevância mais rigoroso.
* [ ] Priorizar páginas com edital, inscrição, seleção, resultado, retificação.
* [ ] Reduzir resultados genéricos institucionais.
* [ ] Criar score de oportunidade.
* [ ] Diferenciar edital real de página institucional.
* [ ] Deduplicar resultados semelhantes.
* [ ] Penalizar páginas sem deadline ou link de edital.
* [ ] Penalizar páginas com título genérico.
* [ ] Exibir primeiro oportunidades com prazo aberto.

### Plano de implementação

Criar função:

```txt
scraper/ranking.py
```

Critérios:

```txt
+ contém "edital"
+ contém "inscrição"
+ contém "processo seletivo"
+ contém "mestrado"
+ contém "doutorado"
+ possui deadline
+ possui source_url oficial
- título genérico
- sem data
- página institucional ampla
```

### Prompt para Codex

```txt
@data_specialist

Melhore o ranking e filtragem dos resultados.

Escopo:
1. Criar uma camada de ranking em `scraper/ranking.py`.
2. Priorizar editais reais com prazo, inscrição e link oficial.
3. Penalizar páginas institucionais genéricas.
4. Deduplicar oportunidades semelhantes.
5. Manter o contrato Scraper -> Bot.
6. Criar testes com fixtures simulando resultados bons, genéricos e duplicados.

Não alterar Telegram.
```

---

## 5. Melhorar uso do Hugging Face

### Problema atual

O Hugging Face está opcional, mas não está claro para o usuário se o bot está usando IA ou fallback por palavras-chave.

### Melhorias

* [ ] Adicionar log seguro informando se `HF_API_KEY` está ativa.
* [ ] Não exibir token em logs.
* [ ] Criar fallback robusto quando a API falhar.
* [ ] Criar timeout curto.
* [ ] Criar retry controlado.
* [ ] Criar cache local de classificações.
* [ ] Não chamar Hugging Face para textos obviamente irrelevantes.
* [ ] Usar IA apenas para enriquecer resultados candidatos.
* [ ] Adicionar campo `enriched_by: "hf" | "heuristic"`.

### Plano de implementação

Fluxo ideal:

```txt
BeautifulSoup coleta candidatos
↓
Heurística filtra lixo
↓
Só candidatos relevantes vão para Hugging Face
↓
HF enriquece classificação/resumo
↓
Fallback se HF falhar
```

### Prompt para Codex

```txt
@data_specialist

Otimize o uso do Hugging Face para reduzir custo, latência e falhas.

Regras:
1. Usar Hugging Face apenas em candidatos previamente filtrados por heurística.
2. Criar fallback determinístico quando a API falhar.
3. Criar logs seguros indicando `HF enabled` ou `HF fallback`.
4. Nunca logar token, headers ou payload sensível.
5. Criar timeout e retry controlados.
6. Adicionar campo interno de rastreio `enriched_by`, sem quebrar o contrato público.
7. Criar testes simulando HF indisponível.

Não alterar interface Telegram.
```

---

## 6. Criar busca por área/interesse

### Problema atual

O usuário só informa país e estado. Isso limita a utilidade.

### Melhorias

* [ ] Perguntar tipo de oportunidade.
* [ ] Permitir filtro por:

  * [ ] Mestrado
  * [ ] Doutorado
  * [ ] Bolsa
  * [ ] Concurso
  * [ ] Perito
  * [ ] Pedagógico
  * [ ] Tecnologia
  * [ ] Segurança
  * [ ] Saúde
  * [ ] Direito
* [ ] Permitir busca por texto livre.
* [ ] Permitir `/buscar tecnologia PB`.
* [ ] Permitir `/buscar mestrado ciência da computação PB`.
* [ ] Salvar preferências do usuário futuramente.

### Plano de implementação

Expandir `keywords` no contrato Bot → Scraper.

Exemplo:

```json
{
  "country": "BR",
  "state": "PB",
  "keywords": ["mestrado", "computacao", "tecnologia"]
}
```

### Prompt para Codex

```txt
@bot_manager

Planeje a expansão do fluxo de busca para aceitar área de interesse.

Requisitos:
1. O usuário deve informar país, estado e área/tipo de oportunidade.
2. O contrato Bot -> Scraper deve continuar compatível.
3. Se necessário, adicione campo opcional `query`.
4. Não quebrar buscas atuais por `/buscar`.
5. Criar testes para busca com e sem área.

Use create-plan antes de implementar.
```

---

## 7. Criar suporte real a múltiplos países

### Problema atual

O bot aceita país, mas na prática só `BR` está implementado.

### Melhorias

* [ ] Tratar `country` como parâmetro real.
* [ ] Criar registry por país.
* [ ] Definir países suportados.
* [ ] Retornar mensagem clara para país não suportado.
* [ ] Suportar inicialmente:

  * [ ] Brasil
  * [ ] Portugal
  * [ ] França
  * [ ] Canadá
  * [ ] Reino Unido
* [ ] Documentar fontes por país.
* [ ] Evitar scraping em fontes sem permissão ou muito instáveis.

### Plano de implementação

Criar estrutura:

```txt
scraper/sources/
├── br/
│   ├── pb.py
│   ├── sp.py
│   └── registry.py
├── pt/
│   └── registry.py
├── fr/
│   └── registry.py
```

Não implemente todos de uma vez. Comece com Brasil bem feito.

### Prompt para Codex

```txt
@data_specialist

Prepare a arquitetura para múltiplos países sem implementar todas as fontes agora.

Escopo:
1. Criar estrutura de registry por país.
2. Manter Brasil como país inicial.
3. Retornar `empty` para país sem fonte cadastrada.
4. Não usar fallback para Brasil quando outro país for solicitado.
5. Documentar como adicionar novas fontes.

Não implementar scraping internacional ainda.
```

---

## 8. Melhorar mensagens de erro e avisos

### Problema atual

O bot mostra erro técnico demais:

```txt
HTTPSConnectionPool(...)
ConnectTimeoutError(...)
```

Isso é útil para dev, mas horrível para usuário final.

### Melhorias

* [ ] Separar erro técnico de mensagem para usuário.
* [ ] Mostrar aviso simples:

  * “Uma fonte não respondeu.”
  * “Resultados parciais exibidos.”
* [ ] Enviar erro técnico apenas para log.
* [ ] Criar modo debug via `LOG_LEVEL=DEBUG`.
* [ ] Remover stack trace da resposta do Telegram.
* [ ] Criar mensagens amigáveis para timeout, 403, 404, 503.

### Plano de implementação

No `messages.py`, renderizar warnings assim:

```txt
Avisos:
- Algumas fontes não responderam. Os resultados exibidos podem estar incompletos.
```

E deixar erro técnico só no log.

### Prompt para Codex

```txt
@telegram_specialist

Melhore a renderização de erros e warnings.

Regras:
1. Não exibir exceções técnicas completas ao usuário.
2. Converter timeouts e HTTP errors em mensagens amigáveis.
3. Manter detalhes técnicos apenas nos logs.
4. Se houver resultados, usar `partial_success`.
5. Se nenhuma fonte responder, orientar o usuário a tentar novamente.

Não alterar scraper.
```

---

## 9. Criar cache para reduzir scraping repetido

### Problema atual

Cada busca pode bater nos mesmos sites de novo. Isso aumenta latência e risco de bloqueio.

### Melhorias

* [ ] Cache por país/estado/keyword.
* [ ] TTL de 30 minutos ou 1 hora.
* [ ] Cache em memória no MVP.
* [ ] Cache em SQLite no próximo estágio.
* [ ] Comando `/atualizar` para forçar nova busca.
* [ ] Mostrar quando o resultado veio do cache.
* [ ] Reduzir chamadas ao Hugging Face.

### Plano de implementação

Criar:

```txt
scraper/cache.py
```

Estratégia simples:

```python
cache_key = f"{country}:{state}:{','.join(keywords)}"
```

### Prompt para Codex

```txt
@data_specialist

Implemente cache simples para reduzir scraping repetido.

Escopo:
1. Criar cache em memória com TTL configurável.
2. Cachear respostas por country/state/keywords.
3. Permitir bypass futuro via parâmetro `force_refresh`.
4. Não usar banco de dados agora.
5. Criar testes para cache hit e cache miss.

Não alterar Telegram, exceto se for necessário exibir `from_cache`.
```

---

## 10. Criar persistência de preferências do usuário

### Problema atual

O bot não lembra preferências.

### Melhorias

* [ ] Salvar último país/estado pesquisado.
* [ ] Salvar áreas favoritas.
* [ ] Criar `/minhas_preferencias`.
* [ ] Criar `/limpar_preferencias`.
* [ ] Futuramente enviar alertas automáticos.
* [ ] Usar SQLite inicialmente.
* [ ] Migrar para PostgreSQL se crescer.

### Plano de implementação

Criar:

```txt
storage/users.py
storage/db.py
```

Tabela:

```sql
users (
  telegram_id,
  country,
  state,
  keywords,
  created_at,
  updated_at
)
```

### Prompt para Codex

```txt
@bot_manager

Planeje persistência simples de preferências do usuário.

Regras:
1. Usar SQLite no MVP.
2. Não exigir banco externo.
3. Salvar última busca do usuário.
4. Criar comandos `/minhas_preferencias` e `/limpar_preferencias`.
5. Não criar alertas automáticos ainda.

Use create-plan antes da implementação.
```

---

## 11. Criar alerta automático de novas oportunidades

### Problema atual

O bot só responde quando o usuário pergunta. Um produto profissional deveria monitorar e avisar.

### Melhorias

* [ ] Criar `/assinar`.
* [ ] Criar `/cancelar`.
* [ ] Criar rotina periódica.
* [ ] Verificar novas oportunidades a cada X horas.
* [ ] Notificar somente novos editais.
* [ ] Não repetir edital já enviado.
* [ ] Criar hash por `source_url`.
* [ ] Permitir escolher área e estado.
* [ ] Respeitar limite de mensagens do Telegram.

### Plano de implementação

Criar job interno ou processo separado.

No Railway, cuidado: processo contínuo já roda. Dá para usar `asyncio`/job queue leve, mas não faça gambiarra com loop infinito paralelo sem controle.

### Prompt para Codex

```txt
@bot_manager

Planeje funcionalidade de alertas automáticos.

Requisitos:
1. Usuário pode assinar alertas por país, estado e keywords.
2. Sistema verifica novas oportunidades periodicamente.
3. Não reenviar oportunidades já notificadas.
4. Usar SQLite para armazenar assinaturas e itens enviados.
5. Não quebrar polling do Telegram.
6. Não implementar antes de apresentar plano.

Use create-plan e proponha arquitetura antes do código.
```

---

## 12. Melhorar contrato de dados

### Problema atual

O contrato atual é bom, mas ainda falta informação importante para editais acadêmicos.

### Melhorias

* [ ] Adicionar `application_url`.
* [ ] Adicionar `program_name`.
* [ ] Adicionar `degree_level`.
* [ ] Adicionar `vacancies`.
* [ ] Adicionar `research_lines`.
* [ ] Adicionar `important_dates`.
* [ ] Adicionar `selection_type`.
* [ ] Adicionar `is_remote`.
* [ ] Adicionar `fees`.
* [ ] Adicionar `eligibility`.
* [ ] Adicionar `last_checked_at`.

### Plano de implementação

Evoluir contrato mantendo compatibilidade:

```json
{
  "program_name": "PPGI",
  "degree_level": ["mestrado", "doutorado"],
  "vacancies": null,
  "research_lines": [],
  "important_dates": {
    "application_start": null,
    "application_end": "2026-07-01",
    "exam_date": null,
    "result_date": null
  },
  "application_url": null
}
```

### Prompt para Codex

```txt
@bot_manager

Planeje evolução do contrato Scraper -> Bot para oportunidades acadêmicas.

Regras:
1. Manter compatibilidade com o contrato atual.
2. Adicionar campos opcionais para programa, nível, vagas, linhas de pesquisa, datas importantes e link de inscrição.
3. Atualizar validação.
4. Atualizar renderização do Telegram.
5. Criar fixtures cobrindo campos novos e antigos.

Não implementar sem aprovação.
```

---

## 13. Melhorar parser de PDF

### Problema atual

O bot apenas aponta PDF, mas não extrai dados de dentro dele. Muitos editais escondem vagas, datas e linhas de pesquisa no PDF.

### Melhorias

* [ ] Baixar PDF com limite de tamanho.
* [ ] Extrair texto com `pypdf`.
* [ ] Detectar vagas.
* [ ] Detectar datas.
* [ ] Detectar linhas de pesquisa.
* [ ] Usar Hugging Face só no texto extraído relevante.
* [ ] Evitar baixar PDFs enormes.
* [ ] Criar timeout.
* [ ] Criar fallback quando PDF não puder ser lido.

### Plano de implementação

Adicionar dependência:

```txt
pypdf
```

Criar:

```txt
scraper/pdf_parser.py
```

### Prompt para Codex

```txt
@data_specialist

Adicione parser opcional de PDF para editais.

Escopo:
1. Usar `pypdf`.
2. Baixar PDFs apenas se o tamanho for aceitável.
3. Extrair texto limitado.
4. Procurar vagas, datas, linhas de pesquisa e links de inscrição.
5. Usar Hugging Face apenas quando heurística não for suficiente.
6. Criar fallback quando o PDF falhar.
7. Criar testes com fixture de PDF pequeno.

Não alterar Telegram inicialmente.
```

---

## 14. Melhorar observabilidade no Railway

### Problema atual

O Railway mostra online, mas você precisa logs melhores para saber o que está acontecendo.

### Melhorias

* [ ] Logar startup.
* [ ] Logar variáveis configuradas sem expor valores.
* [ ] Logar país/estado pesquisado.
* [ ] Logar fontes consultadas.
* [ ] Logar quantidade de itens por fonte.
* [ ] Logar fallback Hugging Face.
* [ ] Logar cache hit/miss.
* [ ] Nunca logar tokens.
* [ ] Criar `LOG_LEVEL=DEBUG`.

### Plano de implementação

Criar logs seguros:

```txt
HF_API_KEY configured: yes
TELEGRAM_BOT_TOKEN configured: yes
Searching: BR/PB
Sources: ufpb, editais_pb
Results: 15
```

### Prompt para Codex

```txt
@data_specialist @telegram_specialist

Melhorem observabilidade do projeto no Railway.

Regras:
1. Adicionar logs estruturados e seguros.
2. Nunca imprimir tokens ou headers sensíveis.
3. Logar startup, fontes, país/estado, quantidade de resultados e status da HF.
4. Usar `LOG_LEVEL`.
5. Não alterar contratos.

Executar testes ao final.
```

---

## 15. Melhorar segurança

### Melhorias

* [ ] Revogar token já exposto em logs/prints.
* [ ] Criar `.env.example`.
* [ ] Garantir `.env` no `.gitignore`.
* [ ] Não mostrar token em stack trace.
* [ ] Não logar URLs com token Telegram.
* [ ] Validar input do usuário.
* [ ] Limitar tamanho de mensagens.
* [ ] Limitar frequência por usuário.
* [ ] Criar allowlist de comandos.
* [ ] Sanitizar texto antes de Markdown/HTML.

### Plano de implementação

Prioridade imediata:

```txt
Revogar token do BotFather
Atualizar Railway
Redeploy
```

Depois melhorar logs do `httpx`, porque seus logs anteriores expuseram URL com token. Isso é perigoso.

### Prompt para Codex

```txt
@bot_manager

Faça hardening de segurança do bot.

Escopo:
1. Garantir que tokens não apareçam em logs.
2. Reduzir verbosidade de logs HTTP do Telegram/httpx.
3. Criar `.env.example`.
4. Confirmar `.env` no `.gitignore`.
5. Validar input do usuário.
6. Evitar injeção em Markdown/HTML.
7. Criar documentação de rotação de tokens.

Não alterar lógica de busca.
```

---

## 16. Criar testes mais sérios

### Melhorias

* [ ] Teste para país suportado.
* [ ] Teste para estado suportado.
* [ ] Teste para estado não suportado.
* [ ] Teste para não retornar PB em busca de BA.
* [ ] Teste para timeout de fonte.
* [ ] Teste para HF indisponível.
* [ ] Teste para contrato novo e antigo.
* [ ] Teste para paginação.
* [ ] Teste para mensagem amigável de erro.
* [ ] Teste para deduplicação.

### Plano de implementação

Criar fixtures por região:

```txt
tests/fixtures/br_pb.html
tests/fixtures/br_ba.html
tests/fixtures/br_sp.html
```

### Prompt para Codex

```txt
@data_specialist @telegram_specialist

Expanda a suíte de testes.

Prioridades:
1. Garantir que cada estado retorna apenas fontes compatíveis.
2. Testar região sem fontes.
3. Testar timeout.
4. Testar fallback sem Hugging Face.
5. Testar renderização paginada.
6. Testar contrato Scraper -> Bot.

Não adicionar dependências pesadas.
```

---

## 17. Melhorar README e documentação técnica

### Melhorias

* [ ] Adicionar roadmap.
* [ ] Adicionar arquitetura com diagrama.
* [ ] Adicionar lista de regiões suportadas.
* [ ] Adicionar como adicionar nova fonte.
* [ ] Adicionar como configurar Railway.
* [ ] Adicionar como configurar Hugging Face.
* [ ] Adicionar como rodar testes.
* [ ] Adicionar troubleshooting.
* [ ] Adicionar segurança/rotação de tokens.
* [ ] Adicionar prints atualizados.
* [ ] Adicionar limitações reais.
* [ ] Adicionar decisões arquiteturais.

### Plano de implementação

Criar:

```txt
docs/ARCHITECTURE.md
docs/ADDING_SOURCES.md
docs/SECURITY.md
docs/DEPLOY_RAILWAY.md
```

### Prompt para Codex

```txt
@documentation_specialist

Atualize a documentação profissional do projeto.

Criar:
1. `docs/ARCHITECTURE.md`
2. `docs/ADDING_SOURCES.md`
3. `docs/SECURITY.md`
4. `docs/DEPLOY_RAILWAY.md`

Atualizar:
1. README.md
2. README_EN.md
3. README_FR.md

Incluir prints em `docs/images`.

Aplicar stop-slop e doc_translator.
```

---

# Ordem recomendada de implementação

Não faça tudo de uma vez. Isso seria o jeito mais eficiente de criar um monstro.

## Sprint 1 — Corrigir confiança do bot

* [ ] Remover viés para Paraíba.
* [ ] Criar registry por país/estado.
* [ ] Impedir fallback silencioso para PB.
* [ ] Melhorar warnings para usuário.
* [ ] Remover logs técnicos do Telegram.
* [ ] Revogar token exposto.

## Sprint 2 — Melhorar UX

* [ ] Paginação.
* [ ] Comandos `/ajuda`, `/regioes`, `/fontes`.
* [ ] Botões inline.
* [ ] Busca por tipo/área.

## Sprint 3 — Melhorar qualidade dos dados

* [ ] Ranking.
* [ ] Deduplicação.
* [ ] Cache.
* [ ] Hugging Face otimizado.
* [ ] Parser PDF opcional.

## Sprint 4 — Produto real

* [ ] Preferências do usuário.
* [ ] Alertas automáticos.
* [ ] Histórico de oportunidades.
* [ ] Painel administrativo futuro.
* [ ] Documentação técnica completa.

---

# Prompt mestre para implementar a Sprint 1

Use este primeiro. Ele ataca o problema mais grave: o viés regional.

```txt
@bot_manager

Inicie a Sprint 1 de profissionalização do projeto.

Objetivo principal:
Remover o viés fixo do bot para Paraíba/UFPB e garantir que o país/estado informado pelo usuário controle realmente as fontes consultadas.

Use create-plan antes de qualquer implementação.

Regras:
1. Não alterar o funcionamento básico do Telegram.
2. Não alterar o contrato JSON sem aprovação.
3. Não implementar novas features cosméticas.
4. Priorizar confiabilidade e previsibilidade.

Escopo da Sprint 1:
1. Criar registry central de fontes por país/estado.
2. Fazer o scraper usar apenas fontes compatíveis com `country` e `state`.
3. Remover fallback silencioso para PB.
4. Quando uma região não for suportada, retornar `status=empty` com mensagem clara.
5. Criar testes garantindo que busca por BA/SP/RJ não retorna fontes PB.
6. Melhorar warnings para não expor stack trace técnico ao usuário.
7. Garantir que logs técnicos fiquem apenas no Railway.
8. Atualizar README com regiões suportadas e limitações.

Execução:
- Delegue `data_specialist` para registry, seleção de fontes e testes.
- Delegue `telegram_specialist` para mensagens de warning amigáveis.
- Delegue `documentation_specialist` para documentação.
- Rode validação final integrando Bot -> Scraper -> Renderização.

Entrega:
1. Arquivos alterados.
2. Testes executados.
3. Exemplo de busca suportada.
4. Exemplo de busca não suportada.
5. Próximas melhorias recomendadas.

Não faça refatorações fora do escopo.
```

---

# Por que seguir essas melhorias na ordem ?

A melhoria central não é “colocar mais IA”. Esse é o clichê preguiçoso. O problema principal é **confiabilidade contextual**: se o usuário pede Bahia e recebe Paraíba, o bot perde valor imediatamente.

A lista foi organizada em camadas:

```txt
Confiabilidade
↓
UX
↓
Qualidade dos dados
↓
Automação
↓
Produto
```

Essa ordem evita que seja gasto tempo criando alertas, botões e IA enquanto o mecanismo principal ainda retorna resultado da região errada. 
