"""Verificações de orientação das classes, empates e denominadores biométricos."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from analysis import eer, choose_threshold, operating_metrics

class MetricsTests(unittest.TestCase):
    def test_perfect_scores(self):
        y=np.array([0,0,1,1]);s=np.array([.1,.2,.8,.9])
        self.assertEqual(eer(y,s),0)
        m=operating_metrics(y,s,choose_threshold(y,s))
        self.assertEqual((m['FAR'],m['FRR'],m['AUC']),(0,0,1))

    def test_constant_scores(self):
        y=np.array([0,0,0,1]);s=np.zeros(4)
        self.assertEqual(eer(y,s),.5)
        m=operating_metrics(y,s,1)
        self.assertEqual((m['FAR'],m['FRR'],m['AUC']),(0,1,.5))
        self.assertTrue(np.isfinite(choose_threshold(y,s)))

    def test_far_frr_denominators_and_inclusive_threshold(self):
        y=np.array([0,0,0,0,1,1]);s=np.array([.1,.2,.3,.8,.4,.5])
        m=operating_metrics(y,s,.5)
        self.assertEqual((m['FAR'],m['FRR']),(.25,.5))
        self.assertEqual((m['TN'],m['FP'],m['FN'],m['TP']),(3,1,1,1))

    def test_saved_predictions_reproduce_all_metrics(self):
        root=Path(__file__).resolve().parents[1]
        predictions=pd.read_csv(root/'results/predictions.csv.gz',float_precision='round_trip')
        metrics=pd.read_csv(root/'results/metrics_by_subject.csv',float_precision='round_trip')
        self.assertEqual(len(predictions),4*51*5100)
        self.assertFalse(predictions.duplicated(['model','account','row_id']).any())
        for (family,account),g in predictions.groupby(['model','account']):
            self.assertEqual(len(g),5100)
            self.assertEqual(g.actual.sum(),100)
            self.assertEqual(g.threshold.nunique(),1)
            observed=operating_metrics(g.actual.to_numpy(),g.score.to_numpy(),g.threshold.iloc[0])
            expected=metrics[(metrics.model==family)&(metrics.subject==account)].iloc[0]
            for key in ['TN','FP','FN','TP','AUC','EER','FAR','FRR']:
                self.assertAlmostEqual(observed[key],expected[key],places=12)

if __name__ == '__main__':
    unittest.main()
