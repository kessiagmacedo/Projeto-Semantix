# Dicionário dos resultados

Gerei todos os resultados numéricos com `python src/analysis.py`.

| Arquivo | Conteúdo |
|---|---|
| `cv_details.csv` | AUC de cada configuração, fold temporal e conta, usando somente sessões 1–4 |
| `cv_summary.csv` | Média da validação por configuração, com peso igual por conta e fold |
| `selection.json` | Família e parâmetros escolhidos antes de consultar o teste |
| `metrics_by_subject.csv` | Limiar e métricas de cada família/conta nas sessões 7–8 |
| `metrics_summary.csv` | Média, desvio-padrão amostral, mínimo e máximo por família; cabeçalho de duas linhas |
| `predictions.csv.gz` | Previsões comprimidas, uma linha por família, conta e digitação de teste |
| `eda.json` | Principais estatísticas da exploração e verificações |
| `feature_separation.csv` | Razão de variâncias entre/dentro dos participantes, calculada no treino |
| `descriptive_statistics.csv` | Estatísticas descritivas das 31 variáveis na base completa; não usadas na seleção |
| `run_manifest.json` | Versões realmente utilizadas, semente, integridade, protocolo e tempo de execução |

Em `predictions.csv.gz`, `account` é a conta avaliada; `row_id` é o índice da linha do CSV
oficial, começando em zero, sem contar o cabeçalho; `actual=1` significa genuíno;
`score` é a saída do modelo e `threshold` é o limiar validado. A decisão é aceitar quando
`score >= threshold`. Não calibrei o score como probabilidade operacional.

As 5.100 digitações de teste são reutilizadas contra 51 contas e quatro famílias:
1.040.400 linhas de previsões. Essas linhas não representam tentativas independentes.

FAR, FRR e EER são frações entre zero e um nos CSVs. Os relatórios as exibem como
percentuais. Para preservar empates e decisões no limiar, scores e limiares são
salvos com 17 algarismos significativos; leia com:

```python
pd.read_csv('results/predictions.csv.gz', float_precision='round_trip')
```

Usei o teste de auditoria para reconstruir as métricas das 204 combinações de modelo/conta.
Nenhum desvio-padrão apresentado deve ser interpretado como intervalo de confiança.
