import numpy as np
from ..base import BaseEstimator, clone
from ..utils import check_random_state
from scipy.sparse import issparse


class ClassifierChain(BaseEstimator):
    """Classifier Chain
    A multi-label model that arranges binary classifiers into a chain. Each
    model makes a prediction in the order specified by the chain using all
    of the available features provided to the model plus the predictions of
    models that are earlier in the chain.

    By default the order of the chain is random although it can be specified
    at the time of fitting with the chain_order parameter. Since the optimal
    chain_order is not known a priori it is common to use the mean prediction
    of an ensemble randomly ordered classifier chains.

    Parameters
    ----------
    base_estimator : object
        The base estimator used for fitting the model for each label.
    random_state : integer or numpy.RandomState, optional
        The generator used to generate random chain orders. If an
        integer is given, it fixes the seed. Defaults to the global numpy
        random number generator.

    Attributes
    ----------
    classifiers_ : array
        List of classifiers, which will be used to chain prediction.
    chain_order_ : list of ints
        A list of integers specifying the order of the classes in the chain.
        For example, for a chain of length 5
            chain_order = [1, 3, 2, 4, 0]
        means that the first model in the chain will make predictions for
        column 1 in the Y matrix, the second model will make predictions
        for column 3, etc. If chain_order is not None it must have a length
        equal to the number of columns in Y.
        If chain_order is None an ordered list of integers will be used
            chain_order = [0, 1, 2, ..., Y.shape[1]]
        where Y is the label matrix passed to the fit method.

    References
    ----------
    Jesse Read, Bernhard Pfahringer, Geoff Holmes, Eibe Frank, "Classifier
    Chains for Multi-label Classification", 2009.

    """

    def __init__(self, base_estimator, random_state=None,
                 chain_order=None, shuffle=True):
        self.base_estimator = base_estimator
        self.random_state = random_state
        if chain_order is not None:
            if not all([isinstance(i, int) for i in self.chain_order]):
                raise ValueError("chain_order must be a list of integers")
        self.chain_order = chain_order

        self.shuffle = shuffle

    def fit(self, X, Y):
        """
        Parameters
        ----------
        shuffle : bool
            If true chain_order is shuffled
        chain_order: list
            A list of integers specifying the order of the classes in the
            chain.
        """

        random_state = check_random_state(self.random_state)
        self.classifiers_ = [clone(self.base_estimator)
                             for _ in range(Y.shape[1])]

        if self.chain_order is not None:
            if not len(self.chain_order) == Y.shape[1]:
                raise ValueError("chain_order length must equal n_labels")
        else:
            self.chain_order = list(range(Y.shape[1]))
            if self.shuffle:
                random_state.shuffle(self.chain_order)

        for chain_idx, classifier in enumerate(self.classifiers_):
            previous_labels = Y[:, self.chain_order[:chain_idx]]
            if issparse(previous_labels):
                previous_labels = previous_labels.toarray()

            y = Y[:, self.chain_order[chain_idx]]
            if issparse(y):
                y = y.toarray()[:,0]

            X_aug = np.hstack((X, previous_labels))
            classifier.fit(X_aug, y)

    def predict(self, X):
        Y_pred_chain = np.zeros((X.shape[0], len(self.classifiers_)))
        for chain_idx, classifier in enumerate(self.classifiers_):
            previous_predictions = Y_pred_chain[:, :chain_idx]
            X_aug = np.hstack((X, previous_predictions))
            Y_pred_chain[:, chain_idx] = classifier.predict(X_aug)
        chain_key = [self.chain_order.index(i) for i in range(len(
            self.chain_order))]
        Y_pred = Y_pred_chain[:, chain_key]

        return Y_pred
