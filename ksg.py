import scipy.spatial as ss
from scipy.special import digamma
from math import log
import numpy as np

class Entropy(object):
	"""Estimate the entropy of a distribution based on
	nearest-neighbor methods.

	Parameters
	----------
	X : data (n_samples, n_dim)
		Data matrix
	k : int
		k-nearest-neighbor will be used.
	"""
	def __init__(self, X, k=3, add_noise=False):
		self.k = k
		self.n_samples, self.n_dim = X.shape
		assert k <= self.n_samples - 1
		intens = 1e-10  # small noise to break degeneracy, see doc.
		if add_noise:
			X = X.astype(float) + intens * np.random.randn(*X.shape)
		self.X = X
		self.tree = ss.cKDTree(self.X)


	def entropy(self, k=None, n_jobs=-1):
		""" The classic K-L k-nearest neighbor continuous entropy estimator
			x should be a list of vectors, e.g. x = [[1.3], [3.7], [5.1], [2.4]]
			if x is a one-dimensional scalar and we have four samples
		"""
		if k is None:
			k = self.k
		assert k <= self.n_samples - 1
		nn = self.tree.query(self.X, k + 1, p=float('inf'), n_jobs=n_jobs)[0][:, k]
		const = digamma(self.n_samples) - digamma(k) + self.n_dim *log(2)
		return const + self.n_dim * np.mean(np.log(nn))

class MutualInformation(object):
	"""Estimate the mutual information between two variables based on
	nearest-neighbor methods.

	Parameters
	----------
	X : data (n_samples, n_dim)
		Data matrix
	k : int
		k-nearest-neighbor will be used.
	"""
	def __init__(self, X, Y, k=3, kind=1, add_noise=False):
		X = self.normalize(X)
		Y = self.normalize(Y)
		self.k = k
		self.kind = kind
		assert kind in [1, 2]
		n_Xsamples, self.n_Xdim = X.shape
		n_Ysamples, self.n_Ydim = Y.shape
		assert n_Xsamples == n_Ysamples
		self.n_samples = n_Xsamples
		assert k <= self.n_samples - 1
		intens = 1e-10  # small noise to break degeneracy, see doc.
		if add_noise:
			X = X.astype(float) + intens * np.random.randn(*X.shape)
			Y = Y.astype(float) + intens * np.random.randn(*Y.shape)
		self.X = X
		self.Y = Y
		self.Z = np.concatenate([self.X, self.Y], axis=1)
		self.tree = ss.cKDTree(self.Z)
		self.Xtree = ss.cKDTree(self.X)
		self.Ytree = ss.cKDTree(self.Y)

	@staticmethod
	def normalize(X):
		X = X - X.mean(axis=0, keepdims=True)
		X = X / X.std(axis=0, keepdims=True)
		return X

	def mutual_information(self, k=None, kind=None, n_jobs=-1):
		""" Mutual information of x and y
			x, y should be a list of vectors, e.g. x = [[1.3], [3.7], [5.1], [2.4]]
			if x is a one-dimensional scalar and we have four samples
		"""
		if k is None:
			k = self.k
		assert k <= self.n_samples - 1
		if kind is None:
			kind = self.kind
		assert kind in [1, 2]
		# Find nearest neighbors in joint space, p=inf means max-norm
		if kind == 1:
			dvec = self.tree.query(self.Z, k + 1, p=float('inf'), n_jobs=n_jobs)[0][:,k]
			a = avgdigamma1(self.Xtree, self.X, dvec)
			b = avgdigamma1(self.Ytree, self.Y, dvec)
			mi =  -a - b
		elif kind == 2:
			didxs = self.tree.query(self.Z, k + 1, p=float('inf'), n_jobs=n_jobs)[1] [:,1:]
			Xdvec = [np.linalg.norm(xi[np.newaxis]-self.X[idxs], ord=np.inf, axis=-1).max() for xi, idxs in zip(self.X, didxs)]
			Ydvec = [np.linalg.norm(yi[np.newaxis]-self.Y[idxs], ord=np.inf, axis=-1).max() for yi, idxs in zip(self.Y, didxs)]
			a = avgdigamma2(self.Xtree, self.X, Xdvec)
			b = avgdigamma2(self.Ytree, self.Y, Ydvec)
			mi =  -a - b - 1./k
		else:
			raise ValueError('kind must be either 1 or 2.')
		c, d = digamma(k), digamma(self.n_samples)
		mi += c + d
		return mi

def avgdigamma1(tree, points, dvec):
	# This part finds number of neighbors in some radius in the marginal space
	# returns expectation value of <psi(nx)>
	N = len(points)
	avg = 0.
	for point, dist in zip(points, dvec):
		# subtlety, we don't include the boundary point,
		# but we are implicitly adding 1 to kraskov def bc center point is included
		num_points = len(tree.query_ball_point(point, dist - 1e-15, p=float('inf')))
		avg += digamma(num_points) / N
	return avg

def avgdigamma2(tree, points, dvec):
	# This part finds number of neighbors in some radius in the marginal space
	# returns expectation value of <psi(nx)>
	N = len(points)
	avg = 0.
	for point, dist in zip(points, dvec):
		num_points = len(tree.query_ball_point(point, dist, p=float('inf')))
		avg += digamma(num_points - 1) / N
	return avg