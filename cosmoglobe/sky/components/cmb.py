from astropy.units import Quantity
import numpy as np

import cosmoglobe.sky._constants as const
from cosmoglobe.sky.base_components import DiffuseComponent
from cosmoglobe.sky.components import SkyComponentLabel


class CMB(DiffuseComponent):
    r"""Class representing the CMB component.

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

    label = SkyComponentLabel.CMB

    def get_freq_scaling(self, freqs: Quantity) -> Quantity:
        """See base class."""

        x = (const.h * freqs) / (const.k_B * const.T_0)
        scaling = ((x ** 2 * np.exp(x)) / (np.expm1(x) ** 2)).si

        return np.expand_dims(scaling, axis=0)
