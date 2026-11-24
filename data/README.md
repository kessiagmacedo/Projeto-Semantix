# Origem dos dados

Base pública de pesquisa disponibilizada pela Carnegie Mellon University:
[Keystroke Dynamics Benchmark](https://www.cs.cmu.edu/~keystroke/).

Arquivo: [DSL-StrongPasswordData.csv](https://www.cs.cmu.edu/~keystroke/DSL-StrongPasswordData.csv).
Consulta e conferência em 24/11/2026.

Incluí uma cópia byte a byte do CSV oficial. MD5 publicado pela fonte:
`470235f96568f28f9ea0da62234ec857`.
Minha cópia inicial do CSV tinha serialização diferente, mas os mesmos valores,
colunas e linhas; a igualdade tabular foi conferida com Pandas.

São registros de pesquisa com participantes codificados e uma senha experimental comum.
Não coletei credenciais reais. Dados comportamentais não devem ser tratados
como inofensivos apenas por usarem identificadores codificados.

A fonte disponibiliza os recursos para uso público em pesquisa e solicita a citação do artigo.
Não atribuí ao conjunto uma licença MIT/CC que não esteja declarada pela fonte.

**Referência:** Killourhy, K. S.; Maxion, R. A. Comparing Anomaly Detectors for Keystroke
Dynamics. Proceedings of DSN 2009, p. 125–134, 2009.

Para baixar novamente, execute `python src/download_data.py` na raiz do projeto.
