"""Exporta minha síntese documental a partir das métricas verificadas."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

def main():
    metrics = pd.read_csv(ROOT/'results/metrics_by_subject.csv', float_precision='round_trip')
    result = metrics[metrics.model == 'XGBoost'][['AUC','EER','FAR','FRR']].mean()
    def number(x, digits=2):
        return f'{x:.{digits}f}'.replace('.', ',')
    plt.rcParams['font.family'] = 'DejaVu Sans'
    fig = plt.figure(figsize=(14,9), facecolor='#f7f9fc')
    fig.text(.055,.92,'Meu projeto de autenticação por digitação',fontsize=25,weight='bold',color='#15364b')
    fig.text(.055,.875,'KESSIA MACEDO  •  TRABALHO INDIVIDUAL  •  EBAC × SEMANTIX',fontsize=12,color='#008577')
    blocks = [
        ('01','COLETA DE DADOS',
         'Investiguei se o ritmo de digitação ajuda a reconhecer o titular da conta.\n'
         'Usei a base pública CMU: 20.400 registros, 51 participantes e 31 tempos.\n'
         'Conferi a integridade dos dados e não encontrei nulos ou duplicatas.'),
        ('02','MODELAGEM',
         'Separei treino (sessões 1–4), validação de limiar (5–6) e teste (7–8).\n'
         'Comparei os modelos com dois folds temporais dentro do treino.\n'
         f'Com o XGBoost, obtive AUC {number(result.AUC,4)} e EER {number(result.EER*100)}% no teste.'),
        ('03','CONCLUSÕES',
         f'Observei FAR de {number(result.FAR*100)}% e FRR de {number(result.FRR*100)}%, em média por conta.\n'
         'Encontrei sinal útil, mas não concluo que o modelo esteja pronto para uso.\n'
         'Ainda preciso avaliar novos impostores, dispositivos e ataques dirigidos.')]
    for y,(num,title,body) in zip([.75,.52,.29],blocks):
        fig.text(.055,y,num,fontsize=30,weight='bold',color='#008577')
        fig.text(.13,y+.012,title,fontsize=15,weight='bold',color='#15364b')
        fig.text(.13,y-.035,body,fontsize=14,color='#15364b',va='top',linespacing=1.6)
    fig.text(.055,.065,'Meu relatório completo: docs/RELATORIO.md  •  Código, notebook, dados e resultados no repositório.',fontsize=11,color='#62778a')
    fig.text(.055,.035,'github.com/kessiagmacedo/Projeto-Semantix  •  Síntese documental dos meus resultados.',fontsize=10,color='#62778a')
    fig.savefig(ROOT/'figures/06_documentacao.png',dpi=160,bbox_inches='tight',facecolor=fig.get_facecolor())
    plt.close(fig)

if __name__ == '__main__':
    main()
