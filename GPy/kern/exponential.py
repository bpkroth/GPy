# Copyright (c) 2012, GPy authors (see AUTHORS.txt).
# Licensed under the BSD 3-clause license (see LICENSE.txt)


from kernpart import kernpart
import numpy as np
import hashlib
from scipy import integrate

class exponential(kernpart):
    """
    Exponential kernel (aka Ornstein-Uhlenbeck or Matern 1/2)

    .. math::

       k(r) = \sigma^2 \exp(- r) \qquad \qquad \\text{ where  } r = \sqrt{\sum_{i=1}^D \\frac{(x_i-y_i)^2}{\ell_i^2} }

    :param D: the number of input dimensions
    :type D: int
    :param variance: the variance :math:`\sigma^2`
    :type variance: float
    :param lengthscale: the vector of lengthscale :math:`\ell_i`
    :type lengthscale: np.ndarray of size (1,) or (D,) depending on ARD
    :param ARD: Auto Relevance Determination. If equal to "False", the kernel is isotropic (ie. one single lengthscale parameter \ell), otherwise there is one lengthscale parameter per dimension.
    :type ARD: Boolean
    :rtype: kernel object

    """
    def __init__(self,D,variance=1.,lengthscale=None,ARD=False):
        self.D = D
        self.ARD = ARD
        if ARD == False:
            self.Nparam = 2
            self.name = 'exp'
            if lengthscale is not None:
                assert lengthscale.shape == (1,)
            else:
                lengthscale = np.ones(1)
        else:
            self.Nparam = self.D + 1
            self.name = 'exp_ARD'
            if lengthscale is not None:
                assert lengthscale.shape == (self.D,)
            else:
                lengthscale = np.ones(self.D)
        self._set_params(np.hstack((variance,lengthscale)))

    def _get_params(self):
        """return the value of the parameters."""
        return np.hstack((self.variance,self.lengthscale))

    def _set_params(self,x):
        """set the value of the parameters."""
        assert x.size == self.Nparam
        self.variance = x[0]
        self.lengthscale = x[1:]

    def _get_param_names(self):
        """return parameter names."""
        if self.Nparam == 2:
            return ['variance','lengthscale']
        else:
            return ['variance']+['lengthscale_%i'%i for i in range(self.lengthscale.size)]

    def K(self,X,X2,target):
        """Compute the covariance matrix between X and X2."""
        if X2 is None: X2 = X
        dist = np.sqrt(np.sum(np.square((X[:,None,:]-X2[None,:,:])/self.lengthscale),-1))
        np.add(self.variance*np.exp(-dist), target,target)

    def Kdiag(self,X,target):
        """Compute the diagonal of the covariance matrix associated to X."""
        np.add(target,self.variance,target)

    def dK_dtheta(self,partial,X,X2,target):
        """derivative of the covariance matrix with respect to the parameters."""
        if X2 is None: X2 = X
        dist = np.sqrt(np.sum(np.square((X[:,None,:]-X2[None,:,:])/self.lengthscale),-1))
        invdist = 1./np.where(dist!=0.,dist,np.inf)
        dist2M = np.square(X[:,None,:]-X2[None,:,:])/self.lengthscale**3
        dvar = np.exp(-dist)
        target[0] += np.sum(dvar*partial)
        if self.ARD == True:
            dl = self.variance*dvar[:,:,None]*dist2M*invdist[:,:,None]
            target[1:] += (dl*partial[:,:,None]).sum(0).sum(0)
        else:
            dl = self.variance*dvar*dist2M.sum(-1)*invdist
            target[1] += np.sum(dl*partial)

    def dKdiag_dtheta(self,partial,X,target): 
        """derivative of the diagonal of the covariance matrix with respect to the parameters."""
        #NB: derivative of diagonal elements wrt lengthscale is 0
        target[0] += np.sum(partial)

    def dK_dX(self,partial,X,X2,target):
        """derivative of the covariance matrix with respect to X."""
        if X2 is None: X2 = X
        dist = np.sqrt(np.sum(np.square((X[:,None,:]-X2[None,:,:])/self.lengthscale),-1))[:,:,None]
        ddist_dX = (X[:,None,:]-X2[None,:,:])/self.lengthscale**2/np.where(dist!=0.,dist,np.inf)
        dK_dX = - np.transpose(self.variance*np.exp(-dist)*ddist_dX,(1,0,2))
        target += np.sum(dK_dX*partial.T[:,:,None],0)

    def dKdiag_dX(self,X,target):
        pass

    def Gram_matrix(self,F,F1,lower,upper):
        """
        Return the Gram matrix of the vector of functions F with respect to the RKHS norm. The use of this function is limited to D=1.

        :param F: vector of functions
        :type F: np.array
        :param F1: vector of derivatives of F
        :type F1: np.array  
        :param lower,upper: boundaries of the input domain
        :type lower,upper: floats  
        """
        assert self.D == 1
        def L(x,i):
            return(1./self.lengthscale*F[i](x) + F1[i](x))
        n = F.shape[0]
        G = np.zeros((n,n))
        for i in range(n):
            for j in range(i,n):
                G[i,j] = G[j,i] = integrate.quad(lambda x : L(x,i)*L(x,j),lower,upper)[0]
        Flower = np.array([f(lower) for f in F])[:,None]
        return(self.lengthscale/2./self.variance * G + 1./self.variance * np.dot(Flower,Flower.T))



        
