import astropy.constants as const
import numpy as np

from .skycomponent import SkyComponent

h = const.h
k_B = const.k_B


class FreeFree(SkyComponent):
    """
    Parent class for all Free-Free models.
    
    """
    comp_label = 'ff'

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)
        self.kwargs = kwargs



class LinearOpticallyThin(FreeFree):
    """
    Linearized model only valid in the optically thin case (tau << 1).
    
    """
    model_label= 'freefree'
    _other_quantities = ('Te_map',)

    def __init__(self, data, nside=None, fwhm=None):
        super().__init__(data, nside=nside, fwhm=fwhm)
        self._spectral_params = (self.Te_map.value,)


    def _get_freq_scaling(self, nu, T_e):
        """
        Computes the frequency scaling from the reference frequency nu_ref to 
        an arbitrary frequency nu, which depends on the spectral parameters
        T_e.

        Parameters
        ----------
        nu : int, float, numpy.ndarray
            Frequencies at which to evaluate the model. 
        nu_ref : int, float, numpy.ndarray
            Reference frequency.        
        T_e : numpy.ndarray
            Electron temperature map.

        Returns
        -------
        scaling : numpy.ndarray
            Frequency scaling factor.

        """
        # scaling = np.exp(-h * ((nu-nu_ref) / (k_B*T_e)))
        nu_ref = self.params['nu_ref'].si.value

        # Commander outputs generally in type float32 which results in overflow 
        # in the calculation of the gaunt factor
        T_e = T_e.astype(np.float64)

        scaling = gaunt_factor(nu, T_e) / gaunt_factor(nu_ref, T_e)
        scaling *= (nu_ref/nu)**2

        return scaling


def gaunt_factor(nu, T_e):
    """
    Returns the gaunt factor for a given frequency and electron temperature.

    Parameters
    ----------
    nu : int, float, numpy.ndarray
        Frequency at which to evaluate the Gaunt factor.   
    T_e : numpy.ndarray
        Electron temperature at which to evaluate the Gaunt factor.

    Returns
    -------
    numpy.ndarray
        Gaunt Factor.

    """
    return np.log(np.exp(5.96 - (np.sqrt(3)/np.pi) * np.log(nu
                  * (T_e*1e-4)**-1.5)) + np.e)
