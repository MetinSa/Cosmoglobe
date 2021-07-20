from pathlib import Path
from sys import exit
import warnings

import astropy.units as u
import numpy as np
import healpy as hp

from cosmoglobe.sky.base import (
    _DiffuseComponent,
    _PointSourceComponent,
)
from cosmoglobe.utils import functions as F


DATA_DIR = Path(__file__).parent.parent.resolve() / 'data'
RADIO_CATALOG = DATA_DIR / 'radio_catalog.dat'
SPDUST2_FILE = DATA_DIR / 'spdust2_cnm.dat'


class Synchrotron(_DiffuseComponent):
    r"""Class representing the synchrotron component.

    Attributes
    ----------
    amp : `astropy.units.Quantity`
        Emission maps of synchrotron at the reference frequencies given
        by `freq_ref` from a commander3 chain.
    freq_ref : `astropy.units.Quantity`
        Reference frequencies :math:`\nu_\mathrm{0,s}` for `amp`.
    spectral_parameters : dict
        Dictionary containing the power law spectral index :math:`\beta`.
    label : str
        Component label.

    Methods
    -------
    __call__

    Notes
    -----
    This is a generic power law given at a reference frequency 
    :math:`\nu_{s,0}` with a power law :math:`\beta` in Rayleigh-Jeans 
    temperature. It is defined using the convention in 
    `BeyondPlanck (2020), Section 3.3.1 
    <https://arxiv.org/pdf/2011.05609.pdf>`_;

    .. math::

        \boldsymbol{s}_\mathrm{RJ}^{\mathrm{s}}(\nu) \propto
        \left( \frac{\nu}{\nu_\mathrm{0,s}} \right)^
        {\beta + C \ln \nu / \nu_{0,s}},

    where :math:`\nu` is the frequency for which we are simulating the 
    sky emission. :math:`C` is set to 0 for all current implementations 
    as of BP9.
    """

    label = 'synch'

    def __init__(self, amp, freq_ref, beta):
        super().__init__(amp, freq_ref, beta=beta)

    def _get_freq_scaling(self, freq, freq_ref, beta):
        r"""See base class.

        Parameters
        ----------
        beta : `numpy.ndarray`, `astropy.units.Quantity`
            The power law spectral index.
        """

        scaling = (freq/freq_ref)**beta

        return scaling


class Dust(_DiffuseComponent):
    r"""Class representing the thermal dust component.
    
    Attributes
    ----------
    amp : `astropy.units.Quantity`
        Emission maps of thermal dust at the reference frequencies given
        by `freq_ref`.
    freq_ref : `astropy.units.Quantity`
        Reference frequencies :math:`\nu_\mathrm{0,d}` for `amp`.
    spectral_parameters : dict
        Dictionary containing the spectral parameters :math:`\beta` and 
        :math:`T`.
    label : str
        Component label.

    Methods
    -------
    __call__

    Notes
    -----
    This is a modified blackbody with a power law spectral index 
    :math:`\beta_\mathrm{d}` in Rayleigh-Jeans temperature, and thermal dust 
    temperature :math:`T_{\mathrm{d}}`. It is defined using the convention 
    in `BeyondPlanck (2020), Section 3.3.3 
    <https://arxiv.org/pdf/2011.05609.pdf>`_;

    .. math::

        \boldsymbol{s}_\mathrm{RJ}^{\mathrm{d}}(\nu) \propto 
        \frac{\nu^{\beta_{\mathrm{d}}+1}}{\mathrm{e}^
        {h\nu/kT_{\mathrm{d}}}-1},
    
    where :math:`\nu` is the frequency for which we are simulating the 
    sky emission, :math:`h` is Planck's constant, and :math:`k` is the 
    Boltzmann constant.
    """

    label = 'dust'

    def __init__(self, amp, freq_ref, beta, T):
        super().__init__(amp, freq_ref, beta=beta, T=T)

    def _get_freq_scaling(self, freq, freq_ref, beta, T):
        r"""See base class.

        Parameters
        ----------
        beta : `numpy.ndarray`, `astropy.units.Quantity`
            The power law spectral index.
        T : `astropy.units.Quantity`
            Temperature of the blackbody.
        """

        blackbody_ratio = (
            F.blackbody_emission(freq, T) / F.blackbody_emission(freq_ref, T)
        )
        scaling = (freq/freq_ref)**(beta-2) * blackbody_ratio

        return scaling


class FreeFree(_DiffuseComponent):
    r"""Class representing the free-free component.

    Attributes
    ----------
    amp : `astropy.units.Quantity`
        Emission maps of free-free at the reference frequencies given
        by `freq_ref`.
    freq_ref : `astropy.units.Quantity`
        Reference frequencies :math:`\nu_\mathrm{0,\mathrm{ff}}` for `amp`.
    spectral_parameters : dict
        Dictionary containing the spectral parameter :math:`T_e`.
    label : str
        Component label.

    Methods
    -------
    __call__

    Notes
    -----
    The free-free emission is defined using the convention in 
    `BeyondPlanck (2020), Section 3.3.2 
    <https://arxiv.org/pdf/2011.05609.pdf>`_;

    .. math::

        \boldsymbol{s}_\mathrm{RJ}^{\mathrm{ff}}(\nu) \propto
        \frac{g_{\mathrm{ff}}(T_\mathrm{e})}{\nu^2},

    where :math:`\nu` is the frequency for which we are simulating the 
    sky emission, :math:`g_\mathrm{ff}` is the Gaunt factor, and 
    :math:`T_\mathrm{e}` is the electron temperature.
    """

    label = 'ff'

    def __init__(self, amp, freq_ref, Te):
        super().__init__(amp, freq_ref, Te=Te)

    def _get_freq_scaling(self, freq, freq_ref, Te):
        r"""See base class.
        
        Parameters
        ----------
        Te : `astropy.units.Quantity`
            Electron temperature.
        """

        gaunt_factor_ratio = (
            F.gaunt_factor(freq, Te) / F.gaunt_factor(freq_ref, Te)
        )
        scaling = (freq_ref/freq)**2 * gaunt_factor_ratio

        return scaling


class AME(_DiffuseComponent):
    r"""Class representing the spinning dust component.

    Attributes
    ----------
    amp : `astropy.units.Quantity`
        Emission maps of spinning dust at the reference frequencies given
        by `freq_ref`.
    freq_ref : `astropy.units.Quantity`
        Reference frequencies :math:`\nu_\mathrm{0,sd}` for `amps`.
    spectral_parameters : dict
        Dictionary containing the spectral parameter :math:`\nu_p`.
    label : str
        Component label.
    spdust2 : `astropy.units.Quantity`
        spdust2 template.

    Methods
    -------
    __call__

    Notes
    -----
    The spinning dust emission is defined using the convention in 
    `BeyondPlanck (2020), Section 3.3.4 
    <https://arxiv.org/pdf/2011.05609.pdf>`_;

    .. math::

        \boldsymbol{s}_{\mathrm{RJ}}^{\mathrm{sd}}(\nu) \propto 
        \nu^{-2} \boldsymbol{s}_{0}^{\mathrm{sd}}\left(\nu \cdot 
        \frac{30.0\; \mathrm{GHz}}{\nu_{p}}\right)

    where :math:`\nu` is the frequency for which we are simulating the 
    sky emission, :math:`\boldsymbol{s}_0^{\mathrm{sd}}` is the `spdust2` 
    template, and :math:`\nu_p` the peak frequency.
    """

    label = 'ame'

    def __init__(self, amp, freq_ref, nu_p):
        super().__init__(amp, freq_ref, nu_p=nu_p)

        spdust2_freq, spdust2_amp = np.loadtxt(SPDUST2_FILE, unpack=True)
        spdust2_freq = u.Quantity(spdust2_freq, unit=u.GHz)
        spdust2_amp = u.Quantity(spdust2_amp, unit=(u.Jy/u.sr))
        spdust2_amp = spdust2_amp.to(
            u.K, equivalencies=u.brightness_temperature(spdust2_freq)
        )        
        self.spdust2 = np.array([spdust2_freq.si.value, spdust2_amp.si.value])

    def _get_freq_scaling(self, freq, freq_ref, nu_p):
        r"""See base class.
        
        Parameters
        ----------
        nu_p : `astropy.units.Quantity`
            Peak frequency.
        """

        spdust2 = self.spdust2
        peak_scale = 30*u.GHz / nu_p

        # AME is undefined at outside of this frequency range
        if not np.logical_and(
            (freq*peak_scale).si.value > np.min(spdust2[0]),
            (freq*peak_scale).si.value < np.max(spdust2[0])
        ).all():
            return u.Quantity(0, unit=u.dimensionless_unscaled)

        interp = np.interp((freq * peak_scale).si.value, spdust2[0], spdust2[1])
        interp_ref = (
            np.interp((freq_ref * peak_scale).si.value, spdust2[0], spdust2[1])
        )
        scaling = interp / interp_ref

        return scaling


class CMB(_DiffuseComponent):
    r"""Class representing the CMB component.

    Attributes
    ----------
    amp : `astropy.units.Quantity`
        Emission map of CMB in units of :math:`\mathrm{\mu K_{CMB}}`
    freq_ref : `astropy.units.Quantity`
        Reference frequency is None due to the amplitude maps being 
        stored in units of :math:`\mathrm{\mu K_{CMB}}`.
    spectral_parameters : dict
        Empty dictionary.
    label : str
        Component label.

    Methods
    -------
    __call__
    remove_dipole
    get_dipole

    Notes
    -----
    The CMB emission is defined using the convention in 
    `BeyondPlanck (2020), Section 3.2 
    <https://arxiv.org/pdf/2011.05609.pdf>`_;

    .. math::

        \boldsymbol{s}_{\mathrm{RJ}}^{\mathrm{CMB}}(\nu) \propto 
        \frac{x^{2} \mathrm{e}^{x}}{\left(\mathrm{e}^{x}-1\right)
        ^{2}} \boldsymbol{s}^{\mathrm{CMB}},

    where :math:`\nu` is the frequency for which we are simulating the 
    sky emission, :math:`x=h \nu / k T_{0}` and 
    :math:`T_0 = 2.7255 \mathrm{K}` as of BP9.
    """

    label = 'cmb'

    def __init__(self, amp, freq_ref=None):
        super().__init__(amp, freq_ref=freq_ref)

    @u.quantity_input(gal_cut=u.deg)
    def get_dipole(self, gal_cut=10 * u.deg):
        """Returns the solar dipole from the reference amplitude map.

        Parameters
        ----------
        gal_cut : float, optional
            Masks pixles :math:`\pm` `gal_cut` in latitude before estimating 
            dipole (:math:`10^\circ` by default).

        Returns
        -------
        `astropy.units.Quantity`
            Map of the solar dipole.
        """

        if hasattr(self, 'dipole'):
            warnings.warn(
                'Returning previously removed dipole signal '
                '(overriding gal_cut).'
            )
            return self.dipole

        amp_without_dipole = u.Quantity(
                hp.remove_dipole(self.amp[0], gal_cut=gal_cut.value),
                unit=self.amp.unit
        )
        
        return self.amp[0] - amp_without_dipole

    @u.quantity_input(gal_cut=u.deg)
    def remove_dipole(self, gal_cut=10 * u.deg):
        """Removes the solar dipole from the reference amplitude map.

        Parameters
        ----------
        gal_cut : float, optional
            Masks pixles :math:`\pm` `gal_cut` in latitude before 
            estimating dipole (:math:`10^\circ` by default).
        """

        amp_without_dipole = u.Quantity(
                hp.remove_dipole(self.amp[0], gal_cut=gal_cut.value),
                unit=self.amp.unit
        )
        
        self.dipole = self.amp[0] - amp_without_dipole
        self.amp[0] = amp_without_dipole

    def _get_freq_scaling(self, freq, freq_ref=None):
        r"""See base class."""

        # We explicitly expand the dims to support broadcasting
        return np.expand_dims(
            F.thermodynamical_to_brightness(freq), axis=0
        )


class Radio(_PointSourceComponent):
    r"""Class representing the radio component.

    Attributes
    ----------
    amp : `astropy.units.Quantity`
        Point source amplitudes at the reference frequencies given
        by `freq_ref`. Note that this quantity is not a healpix map.
    freq_ref : `astropy.units.Quantity`
        Reference frequencies :math:`\nu_\mathrm{0,\mathrm{src}}` for 
        `amp`.
    spectral_parameters : dict
        Dictionary containing the spectral parameter :math:`\alpha`.
    nside : int
        Point source components need to be explicitly passed an NSIDE.
    label : str
        Component label.

    Methods
    -------
    __call__

    Notes
    -----
    This is a generic power law given at a reference frequency 
    :math:`\nu_{\mathrm{0, src}}` with a power law spectral index 
    :math:`\alpha`. It is defined using the convention in 
    `BeyondPlanck (2020), Section 3.4.1 
    <https://arxiv.org/pdf/2011.05609.pdf>`_;

    .. math::

        \boldsymbol{s}_{\mathrm{RJ}}^{\mathrm{src}}(\nu) \propto
        \left(\frac{\nu}{\nu_{\mathrm{0, src}}}\right)^{\alpha-2}

    where :math:`\nu` is the frequency for which we are simulating the 
    sky emission.
    """

    label = 'radio'

    def __init__(self, amp, freq_ref, nside, specind):
        super().__init__(amp, freq_ref, nside, specind=specind)

        self.amp = u.Quantity(self.amp.value, unit='mJy')
        self.angular_coords = self._read_coords_from_catalog(RADIO_CATALOG)

    def _get_freq_scaling(self, freq, freq_ref, specind):
        r"""See base class.

        Parameters
        ----------
        specind : `astropy.units.Quantity`
            Power law spectral index.
        """

        scaling = (freq/freq_ref)**(specind-2)

        return scaling