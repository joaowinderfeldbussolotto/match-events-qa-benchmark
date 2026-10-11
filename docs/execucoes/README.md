# Registro das execuções

Uma página por rodada do benchmark: configuração exata, custo, o que saiu e o
que se aprendeu, com links para os traces no Langfuse. Os números vêm sempre
do arquivo de resultados da rodada, nunca do Langfuse.

| # | Data | Execução | Modelo | Execuções | Acerto `graph_tools` | Custo real |
|---|---|---|---|---|---|---|
| [01](2026-10-10_01_claude-haiku-5.5.md) | 2026-10-10 | Claude Haiku 5.5, seis braços | claude-haiku-5.5 | 312 | 45/52 | US$ 1.04 |


## Sobre os links dos traces

Cada símbolo nas tabelas (✅ certo, ❌ alucinação, 🟡 abstenção, ⚠️ erro de
formato) abre o trace daquela execução no Langfuse: o prompt enviado, cada
ferramenta chamada com o resultado, e a resposta. **É preciso estar logado no
projeto do Langfuse** para abrir.

Cada linha do arquivo de resultados grava o próprio `trace_url`, e o `ask.py`
imprime o link. Se o campo estiver vazio, `scripts/trace_links.py --write`
encontra os traces pelo nome e pelo horário e o preenche.

## Como registrar uma nova execução

O `scripts/run_benchmark.py` escreve a página sozinho ao terminar: cria
`AAAA-MM-DD_NN_<arquivo>.md` nesta pasta (configuração, commit, comando,
custo real, resultado por grupo e braço, erros, leitura automática, cada erro
com a resposta esperada e os traces) e acrescenta a linha no índice acima.

1. Rode com um arquivo de saída próprio quando não for a execução principal:
   `python scripts/run_benchmark.py --repeats 1 --output data/benchmark/<nome>_results.jsonl --title "<título>"`.
   `--no-report` pula a página.
2. O custo real sai do consumo da chave no OpenRouter antes e depois
   (`https://openrouter.ai/api/v1/key`, campo `usage`); com outro provedor fica
   "não medido". Se parecer fora do esperado, consulte chamada por chamada em
   `https://openrouter.ai/api/v1/generation?id=<id>` (campo `provider_name`).
3. Para refazer a página de um arquivo que já existe:
   `python scripts/report_run.py --results <arquivo>.jsonl [--title ...] [--cost ...]`.
4. Faça commit do arquivo de resultados, do resumo e da página juntos. A
   leitura automática só descreve os números; o que eles querem dizer vai à mão
   numa seção a mais, se for preciso.
