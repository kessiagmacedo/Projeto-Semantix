"""Reproduz a avaliação temporal e as figuras do projeto EBAC × Semantix."""
from pathlib import Path
import hashlib
import json
import platform
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score, roc_curve, confusion_matrix, adjusted_rand_score
import sklearn
from xgboost import XGBClassifier
import xgboost

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
COLORS = ['#7b8b9c', '#2578b8', '#d58c29', '#008577']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                    'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#f7f9fc',
                    'axes.facecolor':'#f7f9fc','savefig.facecolor':'#f7f9fc'})

def roc_values(y, score):
    far, tpr, thresholds = roc_curve(y, score, drop_intermediate=False)
    return far, 1-tpr, thresholds

def eer(y, score):
    """Interseção linear das taxas na curva ROC; descritiva, sem selecionar limiar de uso."""
    far, frr, _ = roc_values(y, score)
    diff = far-frr
    k = np.flatnonzero(diff >= 0)[0]
    if k == 0:
        return float((far[0]+frr[0])/2)
    w = -diff[k-1]/(diff[k]-diff[k-1])
    return float(far[k-1]+w*(far[k]-far[k-1]))

def choose_threshold(y, score):
    """Limiar determinístico da validação: menor diferença FAR/FRR, depois menor FAR."""
    far, frr, thresholds = roc_values(y, score)
    thresholds[~np.isfinite(thresholds)] = np.nextafter(np.max(score), np.inf)
    ix = np.lexsort((far, np.abs(far-frr)))[0]
    return float(thresholds[ix])

def operating_metrics(y, score, threshold):
    tn, fp, fn, tp = confusion_matrix(y, score >= threshold, labels=[0, 1]).ravel()
    return dict(FAR=fp/(fp+tn), FRR=fn/(fn+tp), TN=int(tn), FP=int(fp),
                FN=int(fn), TP=int(tp), AUC=roc_auc_score(y, score), EER=eer(y, score))

def make_model(family, params):
    if family == 'Regressão logística':
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight='balanced',
                             max_iter=2000, random_state=SEED))
    if family == 'Árvore de decisão':
        return DecisionTreeClassifier(class_weight='balanced', random_state=SEED, **params)
    if family == 'XGBoost':
        return XGBClassifier(objective='binary:logistic', eval_metric='logloss', tree_method='hist',
                             scale_pos_weight=50, learning_rate=0.08, subsample=1,
                             colsample_bytree=1, n_jobs=2, random_state=SEED, **params)
    raise ValueError(family)

def savefig(fig, name):
    fig.savefig(ROOT/'figures'/name, dpi=160, bbox_inches='tight')
    plt.close(fig)

def main():
    start = time.time()
    for folder in ['results','figures']:
        (ROOT/folder).mkdir(exist_ok=True)
    raw = ROOT/'data/DSL-StrongPasswordData.csv'
    if not raw.exists():
        raise FileNotFoundError('Execute python src/download_data.py antes da análise.')
    assert hashlib.md5(raw.read_bytes()).hexdigest() == '470235f96568f28f9ea0da62234ec857'
    df = pd.read_csv(raw)
    features = list(df.columns[3:])
    assert df.shape == (20400,34) and len(features) == 31
    assert df.isna().sum().sum() == 0 and df.duplicated().sum() == 0
    assert not df.duplicated(['subject','sessionIndex','rep']).any()
    assert (df.groupby(['subject','sessionIndex']).size() == 50).all()
    subjects = sorted(df.subject.unique())
    assert len(subjects) == 51 and set(df.sessionIndex) == set(range(1,9))
    df['tempo_total'] = df.filter(regex=r'^DD\.').sum(axis=1)+df['H.Return']
    train = df.sessionIndex <= 4
    valid = df.sessionIndex.between(5,6)
    test = df.sessionIndex >= 7
    assert not (train & valid | train & test | valid & test).any()
    X = df[features].to_numpy()
    identities = df.subject.to_numpy()
    candidates = {
        'Regressão logística':[{}],
        'Árvore de decisão':[{'max_depth':d,'min_samples_leaf':m} for d in [4,8] for m in [5,20]],
        'XGBoost':[{'max_depth':d,'n_estimators':120} for d in [2,3]]}
    folds = [(df.sessionIndex <= 2, df.sessionIndex == 3),
             (df.sessionIndex <= 3, df.sessionIndex == 4)]
    # Hiperparâmetros globais: cada participante contribui com o mesmo peso.
    cvrows = []
    for family, configs in candidates.items():
        for config_id, params in enumerate(configs):
            for fold_id,(fit_mask, eval_mask) in enumerate(folds,1):
                assert df.loc[fit_mask,'sessionIndex'].max() < df.loc[eval_mask,'sessionIndex'].min()
                for subject in subjects:
                    y = (identities == subject).astype(int)
                    model = make_model(family, params)
                    model.fit(X[fit_mask], y[fit_mask])
                    score = model.predict_proba(X[eval_mask])[:,1]
                    cvrows.append(dict(model=family,config=config_id,params=json.dumps(params),fold=fold_id,
                                       subject=subject,AUC=roc_auc_score(y[eval_mask],score)))
            print('CV concluída:',family,params,flush=True)
    cv = pd.DataFrame(cvrows)
    cv.to_csv(ROOT/'results/cv_details.csv',index=False)
    cv_summary = cv.groupby(['model','config','params'],as_index=False).AUC.mean()
    cv_summary.to_csv(ROOT/'results/cv_summary.csv',index=False)
    chosen = {}
    for family in candidates:
        row = cv_summary[cv_summary.model == family].sort_values(['AUC','config'],ascending=[False,True]).iloc[0]
        chosen[family] = json.loads(row.params)
    winner = cv_summary.loc[cv_summary.AUC.idxmax(),'model']
    (ROOT/'results/selection.json').write_text(json.dumps({'criterion':'AUC macro nos dois folds temporais',
        'selected_family':winner,'hyperparameters':chosen},ensure_ascii=False,indent=2))
    # Teste só é consultado depois de fixar configurações e regra de seleção de limiar.
    rows, prediction_frames, rocs = [], [], {}
    families = ['Sempre rejeitar']+list(candidates)
    for family in families:
        curves=[]
        for subject in subjects:
            y = (identities == subject).astype(int)
            if family == 'Sempre rejeitar':
                vscore=np.zeros(valid.sum()); tscore=np.zeros(test.sum()); threshold=1.0
            else:
                model=make_model(family,chosen[family]);model.fit(X[train],y[train])
                vscore=model.predict_proba(X[valid])[:,1].astype(np.float64)
                threshold=choose_threshold(y[valid],vscore)
                tscore=model.predict_proba(X[test])[:,1].astype(np.float64)
            rows.append(dict(model=family,subject=subject,threshold=threshold,
                             **operating_metrics(y[test],tscore,threshold)))
            prediction_frames.append(pd.DataFrame({'model':family,'account':subject,
                'row_id':df.index[test], 'actual':y[test],'score':tscore,'threshold':threshold}))
            fpr,tpr,_=roc_curve(y[test],tscore)
            curves.append(np.interp(np.linspace(0,1,501), fpr,tpr))
        rocs[family]=np.mean(curves,axis=0)
        print('Teste concluído:',family,flush=True)
    metrics=pd.DataFrame(rows);metrics.to_csv(ROOT/'results/metrics_by_subject.csv',index=False,float_format='%.17g')
    summary=metrics.groupby('model')[['AUC','EER','FAR','FRR']].agg(['mean','std','min','max'])
    summary.to_csv(ROOT/'results/metrics_summary.csv')
    pd.concat(prediction_frames,ignore_index=True).to_csv(ROOT/'results/predictions.csv.gz',index=False,float_format='%.17g',
                                                        compression={'method':'gzip','mtime':0})
    # EDA para decisões e visualizações: somente sessões de treino.
    tr=df[train].copy()
    session=tr.groupby(['subject','sessionIndex']).tempo_total.median().unstack()
    ratios = (session[4]/session[1]-1)*100
    medians=tr.groupby('subject').tempo_total.median().sort_values()
    between=tr.groupby('subject')[features].mean().var()
    within=tr.groupby('subject')[features].var().mean()
    signal=(between/within).sort_values(ascending=False)
    signal.to_csv(ROOT/'results/feature_separation.csv',header=['between_within_ratio'])
    scaler=StandardScaler().fit(X[train]); standardized=scaler.transform(X[train])
    pca=PCA().fit(standardized);coords=pca.transform(standardized)
    k95=int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_),0.95)+1)
    clusters=KMeans(n_clusters=51,n_init=10,random_state=SEED).fit_predict(coords[:,:k95])
    ari=adjusted_rand_score(identities[train],clusters)
    stats={'rows':len(df),'subjects':len(subjects),'features':len(features),'nulls':0,'duplicates':0,
           'train_rows':int(train.sum()),'validation_rows':int(valid.sum()),'test_rows':int(test.sum()),
           'train_median_min':float(medians.min()),'train_median_max':float(medians.max()),
           'subjects_faster_session4':int((ratios<0).sum()),'median_change_session1_4_pct':float(ratios.median()),
           'pca_2_variance':float(pca.explained_variance_ratio_[:2].sum()),'pca_95_components':k95,
           'kmeans_ari_training':ari,'top_feature':signal.index[0],
           'ud_negative_count':int((tr.filter(regex=r'^UD\.')<0).sum().sum()),
           'selected_model':winner}
    (ROOT/'results/eda.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
    df[features].describe().T.to_csv(ROOT/'results/descriptive_statistics.csv')
    fig,axs=plt.subplots(1,2,figsize=(14,6),gridspec_kw={'width_ratios':[1.7,1]})
    axs[0].boxplot([tr.loc[tr.subject==s,'tempo_total'] for s in medians.index],showfliers=False,
                   patch_artist=True,boxprops={'facecolor':'#88c9c1'},medianprops={'color':'#103d50'})
    axs[0].set_xticks(range(1,52),medians.index,rotation=90,fontsize=7)
    axs[0].set(title='Ritmos distintos, com sobreposição',xlabel='Participante • ordenado pela mediana',ylabel='Tempo total (s)')
    for _,row in session.iterrows(): axs[1].plot(range(1,5),row,color='#b5c4d5',alpha=.5,lw=.8)
    axs[1].plot(range(1,5),session.median(),color='#008577',lw=3,marker='o',label='Mediana entre participantes')
    axs[1].set(title=f'{stats["subjects_faster_session4"]}/51 ficaram mais rápidos',xlabel='Sessão de treino',ylabel='Mediana individual (s)',xticks=range(1,5))
    axs[1].legend(fontsize=8)
    fig.suptitle('01  |  O ritmo contém informação, mas muda com a prática',fontsize=18,x=.04,ha='left')
    fig.text(.04,.01,'CMU • sessões 1–4 • extremos ocultos no boxplot, preservados na análise e nos modelos.',fontsize=10)
    fig.tight_layout(rect=(0,.05,1,.93));savefig(fig,'01_ritmo_e_sessoes.png')
    fig,axs=plt.subplots(1,2,figsize=(14,6))
    shown=subjects[:5]
    for s in shown:
        mask=identities[train]==s
        axs[0].scatter(coords[mask,0],coords[mask,1],s=10,alpha=.4,label=s)
    axs[0].set(xlabel=f'PC1 ({pca.explained_variance_ratio_[0]:.1%})',ylabel=f'PC2 ({pca.explained_variance_ratio_[1]:.1%})',title='PCA: cinco primeiros participantes')
    axs[0].legend(fontsize=8,ncol=3)
    top=signal.head(8).sort_values();axs[1].barh(top.index,top.values,color='#008577')
    axs[1].set(title='Quais tempos diferenciam os participantes?',xlabel='Variância entre médias / variância média interna')
    fig.suptitle('02  |  Combinar medidas é mais informativo que usar só a velocidade',fontsize=17,x=.04,ha='left')
    fig.text(.04,.01,f'Treino apenas • PCA ajustado com 51 participantes • 2 PCs: {stats["pca_2_variance"]:.1%} da variância. Separação visual não comprova autenticação.',fontsize=10)
    fig.tight_layout(rect=(0,.05,1,.93));savefig(fig,'02_pca_e_variaveis.png')
    means=metrics.groupby('model')[['AUC','EER','FAR','FRR']].mean().loc[families]
    fig,axs=plt.subplots(1,2,figsize=(14,6))
    yy=np.arange(len(families))
    for j,c in enumerate(['FAR','FRR']):
        vals=means[c]*100
        bars=axs[0].barh(yy+(j-.5)*.32,vals,height=.3,label=c,color=['#d58c29','#2578b8'][j])
        axs[0].bar_label(bars,fmt='%.1f%%',padding=4,fontsize=10)
    axs[0].set(yticks=yy,yticklabels=families,xlabel='Taxa média por participante (%)',xlim=(0,115),title='Segurança × experiência no limiar validado')
    axs[0].invert_yaxis();axs[0].legend()
    for i,family in enumerate(families):
        axs[1].plot(np.linspace(0,1,501),rocs[family],color=COLORS[i],label=f'{family} • AUC {means.loc[family,"AUC"]:.3f}')
    axs[1].plot([0,1],[0,1],'--',color='#abb7c5',lw=1)
    axs[1].set(xlabel='FAR',ylabel='Aceitação de genuínos (1 − FRR)',title='Curva ROC média por participante')
    axs[1].legend(fontsize=8,loc='lower right')
    fig.suptitle('03  |  Acurácia sozinha esconderia o bloqueio de usuários legítimos',fontsize=17,x=.04,ha='left')
    fig.text(.04,.01,'Teste: sessões 7–8 • 51 contas • limiares individuais fixados nas sessões 5–6 • sempre rejeitar: 98,04% de acurácia.',fontsize=10)
    fig.tight_layout(rect=(0,.05,1,.93));savefig(fig,'03_comparacao_modelos.png')
    win=metrics[metrics.model==winner].sort_values('FRR')
    fig,axs=plt.subplots(1,2,figsize=(14,6),gridspec_kw={'width_ratios':[1.7,1]})
    axs[0].plot(range(51),win.FAR*100,marker='o',ms=3,label='FAR',color='#d58c29')
    axs[0].plot(range(51),win.FRR*100,marker='o',ms=3,label='FRR',color='#2578b8')
    axs[0].set_xticks(range(51),win.subject,rotation=90,fontsize=7)
    axs[0].set(ylabel='Taxa de erro (%)',xlabel='Contas ordenadas por FRR',title='A média esconde diferenças individuais');axs[0].legend()
    cm=np.array([[win.TN.sum(),win.FP.sum()],[win.FN.sum(),win.TP.sum()]])
    norm=cm/cm.sum(axis=1,keepdims=True)
    axs[1].imshow(norm,cmap='Blues',vmin=0,vmax=1)
    for i in range(2):
        for j in range(2):
            axs[1].text(j,i,f'{cm[i,j]:,}\n({norm[i,j]:.1%})'.replace(',', '.'),ha='center',va='center',fontsize=14,color='white' if norm[i,j]>.5 else '#17334a')
    axs[1].set(xticks=[0,1],xticklabels=['Rejeitado','Aceito'],yticks=[0,1],yticklabels=['Impostor','Genuíno'],title='Decisões agregadas no teste')
    fig.suptitle(f'04  |  {winner}: avaliar cada conta é essencial',fontsize=17,x=.04,ha='left')
    fig.text(.04,.01,'260.100 avaliações conta × tentativa; as mesmas 5.100 digitações são reutilizadas entre contas. Não são eventos independentes.',fontsize=10)
    fig.tight_layout(rect=(0,.05,1,.93));savefig(fig,'04_erros_por_conta.png')
    fig=plt.figure(figsize=(14,8));fig.text(.06,.9,'O ritmo de digitação ajuda a reconhecer o usuário?',fontsize=24,weight='bold',color='#15364b')
    fig.text(.06,.84,'PROJETO EBAC × SEMANTIX  /  AUTENTICAÇÃO COMPORTAMENTAL',fontsize=12,color='#008577')
    vals=[('PARTICIPANTES','51'),('DIGITAÇÕES','20.400'),('AUC MÉDIA',f'{means.loc[winner,"AUC"]:.3f}'),('EER MÉDIO',f'{means.loc[winner,"EER"]:.1%}')]
    for x,(label,value) in zip([.06,.30,.54,.78],vals):
        fig.text(x,.71,value,fontsize=35,weight='bold',color='#15364b');fig.text(x,.66,label,fontsize=11,color='#62778a')
    blocks=[('EVIDÊNCIA',f'{winner} foi selecionado pela validação temporal.\nNo teste: FAR {means.loc[winner,"FAR"]:.1%} e FRR {means.loc[winner,"FRR"]:.1%}, em média por conta.'),
            ('COMO FOI AVALIADO','Treino: sessões 1–4  →  limiares: 5–6  →  teste: 7–8.\nComparação de modelos com ajustes escolhidos apenas dentro do treino.'),
            ('DECISÃO', 'Há sinal discriminativo neste cenário controlado.\nO resultado apoia pesquisa adicional; não demonstra segurança em produção.'),
            ('LIMITE CENTRAL','Mesmos participantes, senha fixa e teclado físico.\nNão mede generalização para novos impostores, celulares ou ataques dirigidos.')]
    for y,(label,body) in zip([.55,.42,.29,.16],blocks):
        fig.text(.06,y,label,fontsize=11,weight='bold',color='#008577');fig.text(.24,y,body,fontsize=14,va='top',linespacing=1.45,color='#15364b')
    fig.text(.06,.035,'Fonte: CMU / Killourhy & Maxion (2009) • Protocolo próprio, diferente do benchmark original • Kessia Macedo',fontsize=10,color='#62778a')
    savefig(fig,'05_resumo_executivo.png')
    manifest={'seed':SEED,'data_md5':hashlib.md5(raw.read_bytes()).hexdigest(),
        'data_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'python':platform.python_version(),
        'versions':{'pandas':pd.__version__,'numpy':np.__version__,'scikit-learn':sklearn.__version__,
                    'matplotlib':matplotlib.__version__,'xgboost':xgboost.__version__},
        'elapsed_seconds':round(time.time()-start,2),'protocol':'train 1–4; threshold 5–6; test 7–8',
        'cv':'train 1–2 / validate 3; train 1–3 / validate 4'}
    (ROOT/'results/run_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    print(means.to_string(),flush=True)
    print('Tempo total (s):',manifest['elapsed_seconds'],flush=True)

if __name__ == '__main__':
    main()
