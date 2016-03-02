#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from pyfora.algorithms.logistic.FullRankMajorizationSolver import \
    FullRankMajorizationSolver
from pyfora.algorithms.logistic.TrustRegionConjugateGradientSolver import \
    TrustRegionConjugateGradientSolver
from pyfora.algorithms.logistic.BinaryLogisticRegressionModel import \
    BinaryLogisticRegressionModel
import pyfora.pure_modules.pure_pandas as PurePandas


class BinaryLogisticRegressionFitter(object):
    """
    BinaryLogisticRegressionFitter

    A :class:`~BinaryLogisticRegressionFitter`, or "fitter", holds fitting parameters
    which are used to fit logit models.

    Args:
        regularizer (float): The "lambda" parameter in the referenced paper, the
            regularization strength.
        hasIntercept (bool): If True, include an intercept (aka bias) term in
            the fitted models.
        method (string): one of 'newton-cg' (default) or 'majorization'
        interceptScale (float): When :py:obj:`hasIntercept` is true, feature vectors
            become `[x, interceptScale]`, i.e. we add a "synthetic" feature
            with constant value :py:obj:`interceptScale` to all of the feature vectors.
            This synthetic feature is subject to regularization as all other
            features. To lessen the effect of regularization, users should
            increase this value.
        tol (float): Tolerance for stopping criteria. Fitting stops when
            the l2-norm of the parameters to update do not change more than `tol`.
        maxIter (int): A hard limit on the number of update cycles allowed.
    """
    def __init__(
            self,
            regularizer,
            hasIntercept=True,
            method='majorization',
            interceptScale=1.0,
            tol=1e-4,
            maxIter=1e5,
            splitLimit=1000000):
        assert tol > 0
        assert maxIter > 0

        self.regularizer = regularizer
        self.hasIntercept = hasIntercept
        self.method = method
        self.interceptScale = interceptScale
        self.tol = tol
        self.maxIter = maxIter
        self.splitLimit = splitLimit

    def _addScaleColumn(self, df):
        return df.pyfora_addColumn(
            "intercept", [self.interceptScale for _ in xrange(len(df))])

    def fit(self, X, y):
        """
         fit a (regularized) logit model to the predictors `X` and responses `y`.

        Args:
            X: a dataframe of feature vectors.
            y: a dataframe (with one column) which contains the "target" values,
                corresponding to the feature vectors in `X`.

        Returns:
            A :class:`~pyfora.algorithms.logistic.BinaryLogisticRegressionModel.BinaryLogisticRegressionModel`
            which represents the fit model.

        Examples::

            # fit a logit model without intercept using regularizer 1.0

            from pyfora.algorithms import BinaryLogisticRegressionFitter

            fitter = BinaryLogisticRegressionFitter(1.0, False)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})

            model = fitter.fit(x, y)

        """
        assert len(X) == len(y)

        if isinstance(y, PurePandas.PurePythonDataFrame):
            assert y.shape[1] == 1
            y = y.iloc[:,0]

        # we need to be careful here:
        # sorted is going to copy the
        # maybe we can avoid the copy, but at the very least
        # we should build implement  __pyfora_generator__  on Series
        classes = y.unique()

        assert len(classes) == 2

        classZeroLabel = classes[0]
        classOneLabel = classes[1]

        # TODO: we don't need to hold onto an entire column of ones,
        # but it simplifies the code for now.
        # this logic should move into the subclasses of Solver.Solver
        if self.hasIntercept:
            X = self._addScaleColumn(X)

        if self.method == 'newton-cg':
            solver = TrustRegionConjugateGradientSolver
            regularizer = 1.0 / len(X) / self.regularizer
        elif self.method == 'majorization':
            solver = FullRankMajorizationSolver
            regularizer = self.regularizer
        else:
            raise Exception("bad method argument passed in: " + self.method)

        returnValue = solver(
            X, y,
            classZeroLabel,
            regularizer,
            self.tol,
            self.maxIter,
            self.splitLimit
            ).solve()

        intercept = None
        if self.hasIntercept:
            intercept = returnValue.weights[-1]
            weights = returnValue.weights[:-1]
        else:
            weights = returnValue.weights

        return BinaryLogisticRegressionModel(
            weights,
            classZeroLabel,
            classOneLabel,
            intercept,
            self.interceptScale,
            returnValue.iterations)
